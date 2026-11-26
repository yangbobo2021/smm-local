"""Real creator uploads survive duplicate kicks and the empty-queue handoff."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
from threading import Event, Timer, get_ident
import time
from uuid import uuid4

import pytest
from document_helpers import observe
from test_document_formats_management import Creator, native_input
from test_document_formats_retry import keep
from test_hub_documents_contracts import w
from smm_local import managed_document_uploads
from smm_local.document_snapshots import Snapshots
from smm_local.managed_documents import ManagedDocuments


@pytest.mark.parametrize('owner', ['local', 'hub'])
@pytest.mark.parametrize('boundary', ['processing', 'empty_handoff'])
def test_creator_duplicate_queue_kicks_do_not_disconnect_or_lose_work(w, owner, boundary, monkeypatch):
    # TC-008-upload-queue-coalescing. Actual processing, no synthetic result.
    creator = Creator(w, owner)
    items = []
    for index, (project, format) in enumerate(zip(creator.projects, ('docx', 'xlsx'))):
        key = 'queue' + owner + boundary.replace('_', '') + str(index)
        raw, truth = native_input(format, key)
        item = {'project': project, 'format': format, 'name': key + '.' + format,
                'raw': raw, 'truth': truth, 'status': 'ready'}
        keep('queue/inputs/' + item['name'], raw)
        keep('queue/truth/' + item['name'] + '.json', json.dumps(truth, ensure_ascii=False).encode())
        body = {**creator.project(project), 'name': item['name'], 'sha256': hashlib.sha256(raw).hexdigest(),
                'bytes': len(raw), 'submission_id': uuid4().hex}
        begin = creator.request('POST', '/documents/uploads', body).json()
        for part, start in enumerate(range(0, len(raw), begin['block_bytes'])):
            block = raw[start:start + begin['block_bytes']]
            creator.request('PUT', '/documents/uploads/' + begin['upload_id'] + '/parts/' + str(part),
                            raw=block, headers={'X-Chunk-SHA256': hashlib.sha256(block).hexdigest()})
        item['upload_id'] = begin['upload_id']
        items.append(item)
    entered, release, committed = Event(), Event(), Event()
    original_process = Snapshots.process
    original_lock = managed_document_uploads.control_lock
    original_commit = managed_document_uploads.ManagedDocumentUploads.commit
    owner_thread = []
    gate_checks = []

    def process(self, token, format):
        if boundary == 'processing' and token['raw_sha256'] == hashlib.sha256(items[0]['raw']).hexdigest():
            gate_checks.append({'boundary': boundary, 'raw_sha256': token['raw_sha256']})
            entered.set()
            assert release.wait(20), 'test controller did not release real processing'
        return original_process(self, token, format)

    @contextmanager
    def lock(path, *args, **kwargs):
        with original_lock(path, *args, **kwargs):
            first = path.name == 'upload-queue.lock' and not owner_thread
            if first:
                owner_thread.append(get_ident())
            try:
                yield
            finally:
                if first and boundary == 'empty_handoff':
                    with creator.db.connect() as connection:
                        pending = connection.execute("SELECT COUNT(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0]
                    assert pending == 0
                    gate_checks.append({'boundary': boundary, 'pending_before_second_commit': pending})
                    entered.set()
                    assert release.wait(20), 'test controller did not release queue ownership'

    def captured(self, upload_id, body):
        receipt = original_commit(self, upload_id, body)
        if upload_id == items[1]['upload_id']:
            with creator.db.connect() as connection:
                job = connection.execute('SELECT state,payload FROM document_upload_jobs WHERE document_id=?',
                                         (receipt['document_id'],)).fetchone()
            assert job['state'] == 'pending'
            payload = json.loads(job['payload'])
            assert payload['token']['raw_sha256'] == hashlib.sha256(items[1]['raw']).hexdigest()
            assert payload['token']['capture_id'] == receipt['capture_id']
            committed.set()
        return receipt

    def commit(item):
        return creator.request('POST', '/documents/uploads/' + item['upload_id'] + '/commit', creator.context).json()

    monkeypatch.setattr(Snapshots, 'process', process)
    monkeypatch.setattr(managed_document_uploads, 'control_lock', lock)
    monkeypatch.setattr(managed_document_uploads.ManagedDocumentUploads, 'commit', captured)
    first_error = second_error = None
    timer = None
    with ThreadPoolExecutor(max_workers=2) as threads:
        first = threads.submit(commit, items[0])
        try:
            assert entered.wait(15), 'first real task did not reach the controlled boundary'
            second = threads.submit(commit, items[1])
            assert committed.wait(10), 'second upload did not commit its durable job'
            # Release independently of TestClient's background-task completion.
            # A correct coordinator may wait; this is not a response-time SLA.
            # Existing five-second lock failure can still occur naturally.
            timer = Timer(6.5, release.set)
            timer.start()
            try:
                items[1]['receipt'] = second.result(timeout=15)
            except Exception as error:
                second_error = error
        finally:
            release.set()
            if timer is not None:
                timer.cancel()
                timer.join()
            try:
                items[0]['receipt'] = first.result(timeout=20)
            except Exception as error:
                first_error = error
    observe('queue-handoff', {'owner': owner, 'boundary': boundary, 'gate_checks': gate_checks,
                              'first_error': repr(first_error), 'second_error': repr(second_error)})
    assert first_error is None, repr(first_error)
    assert second_error is None, repr(second_error)
    # No extra kick, upload, service restart or retry can rescue missed work.
    deadline = time.monotonic() + 20
    while True:
        entries = creator.entries()
        if len(entries) == 2 and all(e['latest_attempt']['status'] == 'ready' and not e['publication_pending'] for e in entries.values()):
            break
        assert time.monotonic() < deadline, entries
        time.sleep(.03)
    assert len({item['receipt']['document_id'] for item in items}) == 2
    for item in items:
        item['id'] = item['receipt']['document_id']
        entry = entries[item['id']]
        assert entry['version'] == entry['processing_version'] == 1
        assert entry['sha256'] == hashlib.sha256(item['raw']).hexdigest()
        assert entry['latest_attempt']['capture_id'] == item['receipt']['capture_id']
        assert entry['latest_attempt']['attempt_id'] == item['receipt']['attempt_id']
        assert entry['published_snapshot']['capture_id'] == item['receipt']['capture_id']
        creator.read(item)  # Independent source words/full table cells/original bytes.
    with creator.db.connect() as connection:
        rows = [dict(row) for row in connection.execute('SELECT document_id,state,error FROM document_upload_jobs')]
    assert len(rows) == 2 and {row['document_id'] for row in rows} == set(entries)
    assert all(row['state'] == 'done' and row['error'] is None for row in rows)
    observe('queue-complete', {'owner': owner, 'boundary': boundary, 'jobs': rows})
    # A real coordinator fault after acquiring ownership must remain visible.
    coordinator = managed_document_uploads.ManagedDocumentUploads(ManagedDocuments(creator.db))
    def broken_connect():
        raise RuntimeError('controlled coordinator database failure')
    monkeypatch.setattr(creator.db, 'connect', broken_connect)
    with pytest.raises(RuntimeError, match='controlled coordinator database failure'):
        coordinator.run_pending()

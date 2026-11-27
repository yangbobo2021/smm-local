"""Two independent databases in one directory must both drain committed jobs."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import json
from threading import Event, Timer, get_ident
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from document_helpers import Fixture, observe
from smm_local.core import Archive
from smm_local import managed_document_uploads
from smm_local.document_snapshots import Snapshots
from smm_local.references import material
from test_document_formats_management import Creator, native_input
from test_document_formats_installed_minimum import assert_complete_source_text


@pytest.mark.parametrize('holder', [0, 1])
@pytest.mark.parametrize('boundary', ['processing', 'empty_handoff'])
def test_independent_archives_keep_their_only_queue_kick(tmp_path, monkeypatch, holder, boundary):
    # TC-008-upload-queue-archive-isolation
    creators, fixtures, items = [], [], []
    for archive in range(2):
        db = Archive(tmp_path / ('archive-' + str(archive) + '.sqlite3'))
        fixture = Fixture(tmp_path / ('client-' + str(archive)), db)
        fixtures.append(fixture)
        creator = Creator(SimpleNamespace(pair=SimpleNamespace(local=db), local=fixture,
                                         device=material(db)[0]), 'local')
        creators.append(creator)
        for index, (project, format) in enumerate(zip(creator.projects, ('docx', 'xlsx'))):
            key = 'isolation' + str(archive) + str(index) + boundary.replace('_', '') + str(holder)
            raw, truth = native_input(format, key)
            item = {'archive': archive, 'project': project, 'format': format,
                    'name': key + '.' + format, 'raw': raw, 'truth': truth, 'status': 'ready'}
            body = {**creator.project(project), 'name': item['name'], 'submission_id': uuid4().hex,
                    'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            begin = creator.request('POST', '/documents/uploads', body).json()
            for part, start in enumerate(range(0, len(raw), begin['block_bytes'])):
                block = raw[start:start + begin['block_bytes']]
                creator.request('PUT', '/documents/uploads/' + begin['upload_id'] + '/parts/' + str(part),
                                raw=block, headers={'X-Chunk-SHA256': hashlib.sha256(block).hexdigest()})
            item['upload_id'] = begin['upload_id']
            items.append(item)
    assert creators[0].db.db_path.parent == creators[1].db.db_path.parent
    first = next(i for i in items if i['archive'] == holder)
    entered, release, committed = Event(), Event(), Event()
    original_process = Snapshots.process
    original_lock = managed_document_uploads.control_lock
    original_commit = managed_document_uploads.ManagedDocumentUploads.commit
    first_thread = []
    commits = []

    def process(self, token, format):
        if boundary == 'processing' and token['raw_sha256'] == hashlib.sha256(first['raw']).hexdigest():
            entered.set()
            assert release.wait(20)
        return original_process(self, token, format)

    @contextmanager
    def lock(path, *args, **kwargs):
        with original_lock(path, *args, **kwargs):
            held = path.name == 'upload-queue.lock' and not first_thread
            if held:
                first_thread.append(get_ident())
            try:
                yield
            finally:
                if held and boundary == 'empty_handoff':
                    with creators[holder].db.connect() as con:
                        assert con.execute("SELECT COUNT(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0] == 0
                    entered.set()
                    assert release.wait(20)

    def commit(self, uid, body):
        receipt = original_commit(self, uid, body)
        with self.db.connect() as con:
            row = con.execute('SELECT state,payload FROM document_upload_jobs WHERE document_id=?',
                              (receipt['document_id'],)).fetchone()
        payload = json.loads(row['payload'])
        item = next(i for i in items if i['upload_id'] == uid)
        assert self.db.db_path == creators[item['archive']].db.db_path
        assert row['state'] == 'pending'
        assert payload['token']['capture_id'] == receipt['capture_id']
        assert payload['token']['attempt_id'] == receipt['attempt_id']
        assert payload['token']['raw_sha256'] == hashlib.sha256(item['raw']).hexdigest()
        commits.append(uid)
        if len(commits) == len(items):
            committed.set()
        return receipt

    def submit(item):
        value = creators[item['archive']].request('POST', '/documents/uploads/' + item['upload_id'] + '/commit', {}).json()
        item.update(receipt=value, id=value['document_id'])

    monkeypatch.setattr(Snapshots, 'process', process)
    monkeypatch.setattr(managed_document_uploads, 'control_lock', lock)
    monkeypatch.setattr(managed_document_uploads.ManagedDocumentUploads, 'commit', commit)
    timer = None
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(submit, first)]
            try:
                assert entered.wait(15)
                futures.extend(pool.submit(submit, item) for item in items if item is not first)
                assert committed.wait(10)
                timer = Timer(.2, release.set)
                timer.start()
                for future in futures:
                    future.result(timeout=30)
            finally:
                release.set()
                if timer:
                    timer.cancel()
                    timer.join()
        deadline = time.monotonic() + 10
        while True:
            states = [c.entries() for c in creators]
            if all(len(rows) == 2 and all(r['latest_attempt']['status'] == 'ready' and not r['publication_pending'] for r in rows.values()) for rows in states):
                break
            if time.monotonic() >= deadline:
                observe('cross-archive-queue-lost-kick', {'holder': holder, 'boundary': boundary, 'states': states})
                pytest.fail('committed jobs remained pending without another user action: ' + str(states))
            time.sleep(.03)
        for archive, creator in enumerate(creators):
            expected = [i for i in items if i['archive'] == archive]
            assert set(states[archive]) == {i['id'] for i in expected}
            for item in expected:
                entry = states[archive][item['id']]
                assert entry['latest_attempt']['capture_id'] == item['receipt']['capture_id']
                assert entry['latest_attempt']['attempt_id'] == item['receipt']['attempt_id']
                assert entry['version'] == entry['processing_version'] == 1
                hits = creator.request('POST', '/documents/search', {**creator.context,
                    'query': item['truth']['words'][0], 'scope': 'project',
                    'project_id': item['project']['id'], 'limit': 50, 'local': True}).json()['results']
                assert [hit['id'] for hit in hits] == [item['id']]
                actual = creator.read(item)
                assert_complete_source_text(actual['read']['text'], item['truth'])
            with creator.db.connect() as con:
                assert con.execute("SELECT COUNT(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0] == 0
        observe('cross-archive-queue-completed', {'holder': holder, 'boundary': boundary, 'states': states})
    finally:
        release.set()
        for fixture in fixtures:
            fixture.client.close()

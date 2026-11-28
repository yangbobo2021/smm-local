"""Creator shutdown cancels work, preserves captures and permits explicit retry."""
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from uuid import uuid4

import psutil
import pytest

from document_helpers import Fixture, observe, deny_source_reads
from document_formats_fixtures import docx_fixture
from test_document_formats_parsers import assert_text_result, assert_table_result
from document_formats_platform import process_tree, matching_process
from document_formats_exit_observer import waiting_for_owned_exit
from test_hub_documents_contracts import w


def test_pre_stopped_creator_starts_no_worker_and_keeps_exact_retry(tmp_path, monkeypatch):
    from smm_local import document_supervisor as supervisor
    f = Fixture(tmp_path)
    project = f.project('shutdown component')
    stable_raw, stable_truth = docx_fixture('shutdownstable')
    stable = f.file('control.docx', raw=stable_raw)
    stable_source = f.add(stable, [project])
    f.refresh(stable_source)
    hit, = f.search(stable_truth['words'][0], local=True)['results']
    baseline = f.read(hit, start=0, end=hit['text_length'])
    tables = [f.read(hit, view='table', table_id=t['table_id']) for t in baseline['tables']]

    raw, truth = docx_fixture('shutdowncandidate')
    path = f.file('candidate.docx', raw=raw)
    source = f.add(path, [project])
    event = threading.Event()
    f.db._document_shutdown_event = event
    commands = []
    original = supervisor.module_command
    def command(*args):
        commands.append(args)
        return original(*args)
    monkeypatch.setattr(supervisor, 'module_command', command)
    event.set()
    f.refresh(source)
    entry, = f.files(source)
    assert entry['latest_attempt']['status'] == 'failed' and entry['published_snapshot'] is None
    assert '汇总服务正在停止' in entry['latest_attempt']['error']
    assert commands == []
    target = dict(entry['retry_target'])
    assert target['capture_id'] == entry['latest_attempt']['capture_id']
    assert target['sha256'] == hashlib.sha256(raw).hexdigest()
    root = f.db.db_path.parent / '.document-snapshots'
    assert (root / 'raw' / target['sha256']).read_bytes() == raw
    task = root / 'tasks' / target['expected_attempt_id']
    supervision = json.loads((task / 'supervision.json').read_text())
    assert supervision['status'] == 'failed' and supervision['worker'] is None
    assert supervision['gate_open'] is False and not (root / 'tasks/active.json').exists()
    assert json.loads((task / 'cleanup.json').read_text())['stopped'] is True
    assert f.read(hit, start=0, end=hit['text_length']) == baseline
    assert [f.read(hit, view='table', table_id=t['table_id']) for t in baseline['tables']] == tables

    path.unlink()
    denied = deny_source_reads(monkeypatch, path, stable)
    event.clear()
    f.cli('documents', 'reprocess', '--document-id', entry['id'],
          '--capture-id', target['capture_id'], '--expected-attempt-id', target['expected_attempt_id'],
          '--expected-version', target['expected_version'],
          '--expected-processing-version', target['expected_processing_version'])
    current, = f.files(source)
    assert current['latest_attempt']['status'] == 'ready'
    assert current['latest_attempt']['capture_id'] == target['capture_id']
    assert current['latest_attempt']['attempt_id'] != target['expected_attempt_id']
    retry_task = root / 'tasks' / current['latest_attempt']['attempt_id']
    retry_supervision = json.loads((retry_task / 'supervision.json').read_text())
    assert retry_supervision['status'] == 'completed' and retry_supervision['worker']['pid'] > 0
    assert retry_supervision['controller']['pid'] != supervision['controller']['pid']
    found, = [h for h in f.search(truth['words'][0], local=True, limit=50)['results']
              if h['id'] == entry['id']]
    assert found['sha256'] == target['sha256']
    value = f.read(found, start=0, end=found['text_length'])
    assert_text_result(value, truth)
    for location, cells in zip(truth['table_paths'], truth['tables']):
        table, = [t for t in value['tables'] if t['location']['path'] == location]
        assert_table_result(f.read(found, view='table', table_id=table['table_id']), location, cells)
    assert denied == []
    assert f.read(hit, start=0, end=hit['text_length']) == baseline
    assert [f.read(hit, view='table', table_id=t['table_id']) for t in baseline['tables']] == tables
    response = f.client.post('/api/documents/original', json={'reference': hit['reference']})
    assert response.status_code == 200 and response.content == stable_raw
    observe('shutdown-pre-stopped-retry', {'failed': entry, 'supervision': supervision,
        'ready': current, 'pre_stopped_commands': commands, 'retry_supervision': retry_supervision,
        'parent_query_source_reads': denied,
        'old_complete_bundle_preserved': True})


def test_inflight_creator_shutdown_reclaims_owned_tree_and_saved_capture(tmp_path, monkeypatch):
    f = Fixture(tmp_path)
    project = f.project('inflight shutdown component')
    stable_raw, stable_truth = docx_fixture('inflightstable')
    stable = f.file('control.docx', raw=stable_raw)
    stable_source = f.add(stable, [project])
    f.refresh(stable_source)
    hit, = f.search(stable_truth['words'][0], local=True)['results']
    baseline = f.read(hit, start=0, end=hit['text_length'])
    tables = [f.read(hit, view='table', table_id=t['table_id']) for t in baseline['tables']]
    raw, truth = docx_fixture('inflightcandidate')
    path = f.file('candidate.docx', raw=raw)
    source = f.add(path, [project])
    event = threading.Event()
    f.db._document_shutdown_event = event
    root = f.db.db_path.parent / '.document-snapshots'
    gate = tmp_path / 'raw-gate';gate.mkdir()
    hooks = tmp_path / 'hooks';hooks.mkdir()
    (hooks / 'sitecustomize.py').write_text(
        'from document_formats_lifecycle_hook import install\ninstall()\n', encoding='utf-8')
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv('PYTHONPATH', os.pathsep.join(map(str, (hooks, project_root / 'tests', project_root / 'src'))))
    monkeypatch.setenv('SMM_008_ACTIVE_GATE', str(gate))
    monkeypatch.setenv('SMM_008_ACTIVE_RAW', json.dumps([str(root / 'raw' / hashlib.sha256(raw).hexdigest())]))
    monkeypatch.setenv('SMM_008_ACTIVE_SOURCES', '[]')
    (gate / 'armed').write_text(hashlib.sha256(raw).hexdigest(), encoding='utf-8')
    answers = [];errors = [];members = []
    def refresh():
        try:answers.append(f.refresh(source))
        except BaseException as error:errors.append(repr(error))
    worker = threading.Thread(target=refresh)
    worker.start()
    try:
        until = time.monotonic() + 10
        while True:
            records = list(gate.glob('*.json'))
            if records:
                assert len(records) == 1
                receipt = json.loads(records[0].read_text(encoding='utf-8'))
                active = json.loads((root / 'tasks/active.json').read_text())
                if any(s['pid'] == receipt['pid'] and s['created'] == receipt['created'] for s in active['children']):
                    break
            assert time.monotonic() < until and not errors, errors
            time.sleep(.01)
        assert worker.is_alive() and receipt['token'] == active['token']
        members = process_tree(active['worker'])
        assert any(s['pid'] == receipt['pid'] and s['created'] == receipt['created'] for s in members)
        assert active['controller']['pid'] == os.getpid()
        assert active['gate_open'] and (os.name != 'nt' or active['windows_job']['atomic'])
        assert f.read(hit, start=0, end=hit['text_length']) == baseline
        started = time.monotonic()
        event.set()
        while worker.is_alive() or any(waiting_for_owned_exit(s) for s in members) or (root / 'tasks/active.json').exists():
            assert time.monotonic() - started <= 5
            time.sleep(.01)
        worker.join(timeout=1)
        elapsed = time.monotonic() - started
        assert elapsed <= 5 and not errors and len(answers) == 1
        failed, = f.files(source)
        assert failed['latest_attempt']['attempt_id'] == receipt['token']
        assert failed['latest_attempt']['status'] == 'failed' and failed['published_snapshot'] is None
        assert '汇总服务正在停止' in failed['latest_attempt']['error']
        assert failed['retry_target']['sha256'] == hashlib.sha256(raw).hexdigest()
        assert (root / 'raw' / failed['retry_target']['sha256']).read_bytes() == raw
        assert json.loads((root / 'tasks' / receipt['token'] / 'cleanup.json').read_text())['stopped'] is True
        assert f.read(hit, start=0, end=hit['text_length']) == baseline
        assert [f.read(hit, view='table', table_id=t['table_id']) for t in baseline['tables']] == tables
        response = f.client.post('/api/documents/original', json={'reference': hit['reference']})
        assert response.status_code == 200 and response.content == stable_raw
        observe('shutdown-inflight-owned-tree', {'gate': receipt, 'supervision': active,
            'owned_members': members, 'seconds': elapsed, 'failed': failed,
            'old_complete_bundle_preserved': True})
    finally:
        event.set()
        (gate / 'armed').unlink(missing_ok=True)
        (gate / 'abort').touch()
        worker.join(timeout=10)
        assert not worker.is_alive(), 'owned refresh did not finish during component cleanup'
        assert all(matching_process(s) is None for s in members)


def test_shutdown_preserves_both_unstarted_uploads_for_fresh_archive_startup(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from smm_local.api import create_app
    from smm_local.core import Archive
    from smm_local import document_supervisor as supervisor
    f = Fixture(tmp_path)
    project = f.request('POST', '/api/projects', {'name': 'queued shutdown'})
    event = threading.Event();event.set()
    f.db._document_shutdown_event = event
    commands = []
    native_command = supervisor.module_command
    def command(*args):
        commands.append(args)
        return native_command(*args)
    monkeypatch.setattr(supervisor, 'module_command', command)
    targets = []
    for key in ('queuedalpha', 'queuedbeta'):
        raw, truth = docx_fixture(key)
        body = {'project_id': project['id'], 'project_key': project['stable_key'],
                'submission_id': uuid4().hex, 'name': key + '.docx',
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        upload = f.request('POST', '/api/documents/uploads', body)
        for number, start in enumerate(range(0, len(raw), upload['block_bytes'])):
            chunk = raw[start:start + upload['block_bytes']]
            response = f.client.put('/api/documents/uploads/' + upload['upload_id'] + '/parts/' + str(number),
                content=chunk, headers={'X-Chunk-SHA256': hashlib.sha256(chunk).hexdigest()})
            assert response.status_code == 200
        receipt = f.request('POST', '/api/documents/uploads/' + upload['upload_id'] + '/commit', {})
        row, = [r for r in f.files() if r['id'] == receipt['document_id']]
        assert row['latest_attempt']['status'] == 'pending' and row['published_snapshot'] is None
        assert row['version'] == row['processing_version'] == 0
        targets.append({'receipt': receipt, 'row': row, 'raw': raw, 'truth': truth})
    assert commands == [] and len({v['row']['id'] for v in targets}) == 2
    with f.db.connect() as c:
        jobs = [dict(r) for r in c.execute('SELECT * FROM document_upload_jobs')]
    assert len(jobs) == 2 and all(j['state'] == 'pending' for j in jobs)
    for item in targets:
        Path(item['row']['path']).unlink()
    denied = deny_source_reads(monkeypatch, *[Path(v['row']['path']) for v in targets])
    # A new Archive/app starts its real lifespan consumer. This is a source
    # component, not evidence of an operating-system service restart.
    fresh = Archive(f.db.db_path)
    assert not hasattr(fresh, '_document_shutdown_event')
    with TestClient(create_app(fresh, auto_sync=False, sync_on_start=False)) as client:
        until = time.monotonic() + 10
        while True:
            response = client.get('/api/documents/files');assert response.status_code == 200
            rows = response.json()
            if len(rows) == 2 and all(r['published_snapshot'] is not None for r in rows):break
            assert time.monotonic() < until, rows
            time.sleep(.01)
        assert {r['id'] for r in rows} == {v['row']['id'] for v in targets}
        for item in targets:
            row, = [r for r in rows if r['id'] == item['row']['id']]
            assert row['latest_attempt']['attempt_id'] == item['receipt']['attempt_id']
            assert row['latest_attempt']['capture_id'] == item['receipt']['capture_id']
            assert row['latest_attempt']['status'] == 'ready' and row['version'] == row['processing_version'] == 1
            found = client.post('/api/documents/search', json={'query': item['truth']['words'][0], 'local': True, 'limit': 50})
            assert found.status_code == 200
            hit, = [h for h in found.json()['results'] if h['id'] == row['id']]
            value = client.post('/api/documents/read', json={'reference': hit['reference'], 'start': 0, 'end': hit['text_length']})
            assert value.status_code == 200
            value = value.json();assert_text_result(value, item['truth'])
            for location, cells in zip(item['truth']['table_paths'], item['truth']['tables']):
                table, = [t for t in value['tables'] if t['location']['path'] == location]
                view = client.post('/api/documents/read', json={'reference': hit['reference'], 'view': 'table', 'table_id': table['table_id']})
                assert view.status_code == 200;assert_table_result(view.json(), location, cells)
            original = client.post('/api/documents/original', json={'reference': hit['reference']})
            assert original.status_code == 200 and original.content == item['raw']
        assert denied == [] and commands
    observe('shutdown-two-durable-uploads', {'pending_jobs': jobs,
        'before': [v['row'] for v in targets], 'after': rows,
        'creator_commands': commands, 'source_reads': denied})


def test_processing_lease_stays_owned_until_stopped_application_finishes(tmp_path):
    from smm_local.core import Archive
    from smm_hub.documents import HubDocuments
    from smm_hub.document_execution import ProcessingService
    db = Archive(tmp_path / 'smm-hub.sqlite3')
    shutdown = threading.Event()
    db._document_shutdown_event = shutdown
    hub = HubDocuments(db)
    owner = ProcessingService(hub)
    client = ProcessingService(hub)
    drained = threading.Event()
    native = owner._run
    def observed_run():
        try:native()
        finally:drained.set()
    owner._run = observed_run
    with owner.serve():
        assert client._active() is True
        shutdown.set()
        assert drained.wait(2), 'processor did not stop consuming on the shutdown request'
        assert owner.stop.is_set() is False
        assert client._active() is True, 'CLI must not fall back while the application is still draining'
        during = json.loads(owner.status_file.read_text())
        assert during['status'] == 'running'
    assert client._active() is False
    after = json.loads(owner.status_file.read_text())
    assert after['status'] == 'stopped'
    observe('shutdown-processing-lease-lifetime', {'during_drain': during,
        'after_application_exit': after, 'shutdown_event_separate_from_lifespan_stop': True})


def test_failed_attempt_with_unfinished_queue_receipt_is_not_implicitly_retried(tmp_path, monkeypatch):
    from smm_local.core import Archive
    from smm_local.managed_documents import ManagedDocuments
    from smm_local.managed_document_uploads import ManagedDocumentUploads
    from smm_local import document_supervisor as supervisor
    f = Fixture(tmp_path)
    project = f.request('POST', '/api/projects', {'name': 'failed ticket'})
    shutdown = threading.Event();shutdown.set();f.db._document_shutdown_event = shutdown
    raw, truth = docx_fixture('failedticket')
    body = {'project_id': project['id'], 'project_key': project['stable_key'],
        'submission_id': uuid4().hex, 'name': 'failed-ticket.docx',
        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    begun = f.request('POST', '/api/documents/uploads', body)
    for number, start in enumerate(range(0, len(raw), begun['block_bytes'])):
        chunk = raw[start:start + begun['block_bytes']]
        response = f.client.put('/api/documents/uploads/' + begun['upload_id'] + '/parts/' + str(number),
            content=chunk, headers={'X-Chunk-SHA256': hashlib.sha256(chunk).hexdigest()})
        assert response.status_code == 200
    receipt = f.request('POST', '/api/documents/uploads/' + begun['upload_id'] + '/commit', {})
    uploads = ManagedDocumentUploads(ManagedDocuments(f.db))
    with f.db.connect() as c:
        queued = dict(c.execute('SELECT * FROM document_upload_jobs').fetchone())
    token = json.loads(queued['payload'])['token']
    assert queued['state'] == 'pending' and token['attempt_id'] == receipt['attempt_id']
    # Exercise the real cancellation transition, then leave its operational
    # receipt unfinished as it would be after a crash before queue finalization.
    with pytest.raises(ValueError, match='汇总服务正在停止'):
        uploads.snapshots.process(token, 'docx')
    before, = f.files()
    assert before['latest_attempt']['status'] == 'failed'
    calls = []
    native = supervisor.module_command
    def command(*args):
        calls.append(args)
        return native(*args)
    monkeypatch.setattr(supervisor, 'module_command', command)
    fresh = Archive(f.db.db_path)
    ManagedDocumentUploads(ManagedDocuments(fresh)).run_pending()
    after, = f.files()
    assert calls == [], 'a terminal failed attempt needs a new explicit attempt, not a pending receipt replay'
    assert after['latest_attempt'] == before['latest_attempt'] and after['retry_target'] == before['retry_target']
    assert after['published_snapshot'] is None
    with fresh.connect() as c:
        finished = dict(c.execute('SELECT * FROM document_upload_jobs').fetchone())
    assert finished['state'] == 'failed' and finished['payload'] == queued['payload']
    target = after['retry_target']
    f.cli('documents', 'reprocess', '--document-id', after['id'], '--capture-id', target['capture_id'],
        '--expected-attempt-id', target['expected_attempt_id'], '--expected-version', 0, '--expected-processing-version', 0)
    current, = f.files()
    assert current['latest_attempt']['status'] == 'ready'
    assert current['latest_attempt']['attempt_id'] != target['expected_attempt_id']
    hit, = [h for h in f.search(truth['words'][0], local=True)['results'] if h['id'] == current['id']]
    assert_text_result(f.read(hit, start=0, end=hit['text_length']), truth)
    observe('shutdown-failed-ticket-replay', {'cancelled': before, 'after_replay': after,
        'operational_before': queued, 'operational_after': finished, 'explicit_retry': current})


def test_hub_failed_handoff_ticket_never_restarts_its_terminal_attempt(w):
    from smm_hub.documents import HubDocuments
    from smm_hub.document_execution import ProcessingService
    project = w.hub_project('failed Hub handoff')
    context = w.context()
    shutdown = threading.Event();shutdown.set();w.pair.remote._document_shutdown_event = shutdown
    raw, truth = docx_fixture('hubfailedticket')
    body = {**context, 'project_id': project['id'], 'project_key': project['source_key'],
        'submission_id': uuid4().hex, 'name': 'hub-failed-ticket.docx',
        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    begun = w.remote('POST', '/documents/uploads', body)
    for number, start in enumerate(range(0, len(raw), begun['block_bytes'])):
        chunk = raw[start:start + begun['block_bytes']]
        response = w.hub.put('/v1/documents/uploads/' + begun['upload_id'] + '/parts/' + str(number),
            content=chunk, headers={'X-Chunk-SHA256': hashlib.sha256(chunk).hexdigest()})
        assert response.status_code == 200
    receipt = w.remote('POST', '/documents/uploads/' + begun['upload_id'] + '/commit', context)
    hub = HubDocuments(w.pair.remote)
    processor = ProcessingService(hub)
    with w.pair.remote.connect() as c:
        token = json.loads(c.execute('SELECT payload FROM document_upload_jobs WHERE document_id=?',
                                    (receipt['document_id'],)).fetchone()[0])['token']
    with pytest.raises(ValueError, match='汇总服务正在停止'):
        processor.snapshots.process(token, 'docx')
    before, = w.remote('GET', '/documents/files')
    assert before['latest_attempt']['status'] == 'failed'
    payload = json.dumps({'context': context, 'token': token, 'format': 'docx'}, sort_keys=True)
    with w.pair.remote.connect() as c:
        c.execute("INSERT INTO hub_document_processing_jobs VALUES(?,?,'pending',NULL,NULL)",
                  (token['attempt_id'], payload))
    native = processor.native;calls = []
    def process(*args):
        calls.append(args[0]['attempt_id'])
        return native(*args)
    processor.native = process
    shutdown.clear()
    processor._one()
    after, = w.remote('GET', '/documents/files')
    assert calls == [] and after['latest_attempt'] == before['latest_attempt']
    assert after['published_snapshot'] is None and after['retry_target'] == before['retry_target']
    with w.pair.remote.connect() as c:
        ticket = dict(c.execute('SELECT * FROM hub_document_processing_jobs WHERE attempt_id=?',
                                (token['attempt_id'],)).fetchone())
    assert ticket['state'] == 'failed' and ticket['payload'] == payload
    assert ticket['result_sha256'] is None
    observe('shutdown-hub-failed-ticket', {'before': before, 'after': after,
        'retired_ticket': ticket, 'unexpected_native_attempts': calls,
        'source_truth_words': truth['words']})


def test_shutdown_after_processing_before_publication_preserves_old_bundle(tmp_path, monkeypatch):
    from smm_local.document_snapshots import Snapshots
    f = Fixture(tmp_path)
    project = f.request('POST', '/api/projects', {'name': 'publication shutdown'})
    def upload(raw, previous=None):
        body = {'project_id': project['id'], 'project_key': project['stable_key'],
                'submission_id': uuid4().hex, 'name': 'replace.docx',
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if previous:
            body.update(document_id=previous['id'], expected_version=previous['version'],
                        expected_processing_version=previous['processing_version'],
                        expected_revision=previous['source_revision'])
        begun = f.request('POST', '/api/documents/uploads', body)
        for number, start in enumerate(range(0, len(raw), begun['block_bytes'])):
            chunk = raw[start:start + begun['block_bytes']]
            response = f.client.put('/api/documents/uploads/' + begun['upload_id'] + '/parts/' + str(number),
                content=chunk, headers={'X-Chunk-SHA256': hashlib.sha256(chunk).hexdigest()})
            assert response.status_code == 200
        return f.request('POST', '/api/documents/uploads/' + begun['upload_id'] + '/commit', {})
    old_raw, old_truth = docx_fixture('publicationold')
    upload(old_raw)
    original, = f.request('GET', '/api/documents/library')
    old_hit, = f.search(old_truth['words'][0], local=True)['results']
    old_read = f.read(old_hit, start=0, end=old_hit['text_length'])
    old_tables = [f.read(old_hit, view='table', table_id=t['table_id']) for t in old_read['tables']]
    raw, truth = docx_fixture('publicationnew')
    event = threading.Event();f.db._document_shutdown_event = event
    native = Snapshots.publish;ready = []
    def before_publish(snapshots, c, pk, token, result):
        assert snapshots.db is f.db
        attempt = dict(c.execute('SELECT * FROM document_processing_attempts WHERE id=?',
                                (token['attempt_id'],)).fetchone())
        assert attempt['state'] == 'ready' and attempt['result_sha256'] == token['result_sha256']
        assert snapshots.load_result(token['result_sha256']) == result
        assert (snapshots.root / 'raw' / token['raw_sha256']).read_bytes() == raw
        ready.append({'token': dict(token), 'attempt': attempt})
        event.set()  # Real result complete; the publication entry has not run.
        return native(snapshots, c, pk, token, result)
    with monkeypatch.context() as m:
        m.setattr(Snapshots, 'publish', before_publish)
        upload(raw, original)
    assert len(ready) == 1
    failed, = f.files()
    assert failed['latest_attempt']['status'] == 'failed'
    assert failed['latest_attempt']['attempt_id'] == ready[0]['token']['attempt_id']
    assert '汇总服务正在停止' in failed['latest_attempt']['error']
    assert failed['version'] == old_hit['version'] and failed['processing_version'] == old_hit['processing_version']
    assert failed['published_snapshot']['sha256'] == old_hit['sha256']
    assert f.read(old_hit, start=0, end=old_hit['text_length']) == old_read
    assert [f.read(old_hit, view='table', table_id=t['table_id']) for t in old_read['tables']] == old_tables
    response = f.client.post('/api/documents/original', json={'reference': old_hit['reference']})
    assert response.status_code == 200 and response.content == old_raw
    Path(failed['path']).unlink();event.clear()
    target = failed['retry_target']
    f.cli('documents', 'reprocess', '--document-id', failed['id'], '--capture-id', target['capture_id'],
          '--expected-attempt-id', target['expected_attempt_id'], '--expected-version', target['expected_version'],
          '--expected-processing-version', target['expected_processing_version'])
    current, = f.files()
    assert current['latest_attempt']['capture_id'] == target['capture_id']
    assert current['latest_attempt']['attempt_id'] != target['expected_attempt_id']
    hit, = [h for h in f.search(truth['words'][0], local=True)['results'] if h['id'] == failed['id']]
    assert_text_result(f.read(hit, start=0, end=hit['text_length']), truth)
    assert hit['sha256'] == hashlib.sha256(raw).hexdigest()
    observe('shutdown-result-ready-before-publication', {'completed': ready,
        'failed': failed, 'explicit_retry': current, 'old_bundle_preserved': True})

"""Last-use reclamation covers shared archives and actual abandoned pins."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from document_formats_exit_observer import waiting_for_owned_exit
from document_formats_fixture_io import read_fixture_json
from document_helpers import Fixture, ROOT, observe
from smm_local.core import Archive
from smm_local.documents import Documents
from smm_local.references import material
from document_formats_platform import matching_process, terminate_verified, spawn_identity, verify_server, process_tree
import document_formats_health_hook  # Dynamic child sitecustomize dependency, frozen by the runner.
import document_formats_windows_recovery
from test_document_formats_installed_minimum import assert_complete_source_text
from test_document_formats_management import Creator
from test_document_formats_retry import FONT, scan_pdf
from test_hub_documents_contracts import w


@pytest.mark.skipif(not FONT, reason='requires prepared real PDF fixture font')
@pytest.mark.parametrize('variant', ['local', 'hub', 'two-archives'])
@pytest.mark.parametrize('first_index', [0, 1])
def test_shared_candidate_reclaims_only_after_the_last_authorized_use(w, tmp_path, variant, first_index):
    # TC-008-candidate-last-use-recovery / canonical-shared-last-use
    first = Creator(w, 'hub' if variant == 'hub' else 'local')
    fixture = None
    if variant == 'two-archives':
        db = Archive(first.db.db_path.parent / 'independent.sqlite3')
        fixture = Fixture(tmp_path / 'independent-client', db)
        second = Creator(SimpleNamespace(root=fixture.root, pair=SimpleNamespace(local=db), local=fixture, device=material(db)[0]), 'local')
    else:
        second = first
    control = first.add('docx', 'retainedpublication' + variant.replace('-', ''), first.projects[0])
    before = first.read(control)
    assert_complete_source_text(before['read']['text'], control['truth'])
    raw = scan_pdf('sharedcandidate' + variant.replace('-', ''))
    sha = hashlib.sha256(raw).hexdigest()
    items = []
    try:
        for index, creator in enumerate((first, second)):
            item = {'project': creator.projects[index], 'name': 'shared' + str(index) + '.pdf',
                    'format': 'pdf', 'raw': raw, 'truth': {'words': [], 'tables': [], 'excluded': []}, 'status': 'failed'}
            uid, receipt, entry = creator.upload(item, raw)
            assert entry['latest_attempt']['status'] == 'failed' and entry['published_snapshot'] is None
            assert entry['retry_target']['sha256'] == sha and entry['retry_target']['capture_id'] == receipt['capture_id']
            item.update(id=receipt['document_id'], receipt=receipt, uid=uid)
            items.append((creator, item))
        snapshots = Documents(first.db).snapshots
        path = snapshots.blob('raw', sha)
        assert path.read_bytes() == raw
        ordered = items if first_index == 0 else list(reversed(items))
        for index, (creator, item) in enumerate(ordered):
            entry = creator.entries()[item['id']]
            creator.request('DELETE', '/documents/library/' + item['id'],
                            {**creator.project(item['project']), **creator.comparison(entry)})
            snapshots.put('raw', scan_pdf('sweep' + str(index) + variant.replace('-', '')))
            if index == 0:
                assert path.read_bytes() == raw
                other, kept = ordered[1]
                live = other.entries()[kept['id']]
                assert live['retry_target']['capture_id'] == kept['receipt']['capture_id']
                assert live['retry_target']['expected_attempt_id'] == kept['receipt']['attempt_id']
            else:
                observe('last-use-physical-result', {'variant': variant, 'raw_sha256': sha, 'exists': path.exists()})
                assert not path.exists(), 'last unused shared candidate still occupies staging bytes'
            current = first.read(control)
            assert_complete_source_text(current['read']['text'], control['truth'])
            assert current == before
        for creator, item in items:
            baseline = creator.frozen()
            creator.retry_removed(item, {'capture_id': item['receipt']['capture_id'],
                'expected_attempt_id': item['receipt']['attempt_id'], 'expected_version': 0, 'expected_processing_version': 0})
            assert creator.frozen() == baseline
        assert not path.exists()
    finally:
        if fixture:
            fixture.client.close()


@pytest.mark.parametrize('database', ['local.sqlite3', 'smm-hub.sqlite3'])
def test_real_pin_owner_exit_releases_only_abandoned_pending_bytes(tmp_path, database):
    # TC-008-candidate-last-use-recovery / canonical-crash-pin
    db = Archive(tmp_path / database)
    snapshots = Documents(db).snapshots
    old = b'owned uncommitted pending bytes'
    digest = snapshots.put('raw', old)
    code = '''import sys,os
from pathlib import Path
from smm_local.core import Archive
from smm_local.documents import Documents
s=Documents(Archive(Path(sys.argv[1]))).snapshots
with s.pin([('raw',sys.argv[2])]):
 print('pin-held',flush=True)
 sys.stdin.buffer.read(1)
 os._exit(0)
'''
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
    child = subprocess.Popen([sys.executable, '-B', '-c', code, str(db.db_path), digest],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        assert child.stdout.readline() == ('pin-held'+os.linesep).encode('utf-8')
        pins = list((snapshots.root / 'reclamation').glob('pin-*.json'))
        assert len(pins) == 1
        snapshots.put('raw', b'another explicit admission while the owner is live')
        assert snapshots.blob('raw', digest).read_bytes() == old
        child.stdin.write(b'x');child.stdin.flush();child.stdin.close()
        assert child.wait(timeout=5) == 0
        snapshots.put('raw', b'another explicit admission after confirmed owner exit')
        observe('pin-recovery-physical-result', {'database': database,
            'owner_exit': child.returncode, 'blob_exists': snapshots.blob('raw', digest).exists(),
            'pins_left': [p.name for p in (snapshots.root / 'reclamation').glob('pin-*.json')]})
        assert not snapshots.blob('raw', digest).exists()
        assert not any(p.exists() for p in pins)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)
        if child.stdin and not child.stdin.closed:child.stdin.close()
        child.stdout.close();child.stderr.close()


def test_unregistered_bytes_and_legacy_pin_remain_protected(tmp_path):
    # Historical ownership cannot be inferred from the current DB alone.
    snapshots = Documents(Archive(tmp_path / 'archive.sqlite3')).snapshots
    raw = b'unknown historical bytes'
    sha = hashlib.sha256(raw).hexdigest()
    snapshots._directory('raw')
    snapshots.blob('raw', sha).write_bytes(raw)
    tracked = snapshots.put('raw', b'legacy pinned content')
    pin = snapshots._gc_path('pin-' + 'a' * 32 + '.json')
    pin.write_text(json.dumps({'blobs': [['raw', tracked]]}))
    snapshots.put('raw', b'explicit admission')
    assert snapshots.blob('raw', sha).read_bytes() == raw
    assert snapshots.blob('raw', tracked).read_bytes() == b'legacy pinned content'
    assert pin.exists()


def test_reused_database_path_does_not_transfer_old_archive_ownership(tmp_path):
    database = tmp_path / 'reused.sqlite3'
    snapshots = Documents(Archive(database)).snapshots
    old_identity = material(snapshots.db)[0]
    raw = b'old archive pending bytes at a later reused database path'
    sha = snapshots.put('raw', raw)
    database.rename(tmp_path / 'moved.sqlite3')
    replacement = Documents(Archive(database)).snapshots
    assert material(replacement.db)[0] != old_identity
    replacement.put('raw', b'different archive explicit admission')
    assert snapshots.blob('raw', sha).read_bytes() == raw


def test_denied_physical_deletion_keeps_bytes_charged_until_it_succeeds(tmp_path, monkeypatch):
    snapshots = Documents(Archive(tmp_path / 'archive.sqlite3')).snapshots
    raw = b'denied old pending bytes'
    sha = snapshots.put('raw', raw)
    path = snapshots.blob('raw', sha)
    original = Path.unlink
    denied = []
    def unlink(self, *args, **kwargs):
        if self == path:
            denied.append(str(self))
            raise PermissionError('owned deletion-denial control')
        return original(self, *args, **kwargs)
    new = b'new pending bytes'
    with monkeypatch.context() as patch:
        patch.setattr(Path, 'unlink', unlink)
        snapshots.put('raw', new)
        assert denied and path.read_bytes() == raw
        actual = sum(p.stat().st_size for kind in ('raw', 'results') for p in (snapshots.root / kind).glob('*'))
        assert actual == len(raw) + len(new) == snapshots._unpublished_bytes()
    final = b'final valid admission after release'
    snapshots.put('raw', final)
    assert not path.exists()
    assert snapshots._unpublished_bytes() == len(final)
    observe('gc-delete-denial-accounting', {'denial_observed': denied, 'retained_bytes': len(raw) + len(new),
            'after_release_bytes': snapshots._unpublished_bytes(), 'kind': 'fault injection, not an OS ACL claim'})


@pytest.mark.skipif(os.name == 'nt' or not FONT, reason='real POSIX independent-watchdog crash recovery')
def test_processing_pin_waits_for_real_owned_task_tree_cleanup(tmp_path):
    # The original API supplies the task association; no fake task/pin state.
    control = tmp_path / 'control';control.mkdir()
    (control / 'arm.json').write_text(json.dumps({'nonce': uuid4().hex}))
    hooks = tmp_path / 'hooks';hooks.mkdir()
    (hooks / 'sitecustomize.py').write_text('from document_formats_health_hook import install\ninstall()\n')
    path = tmp_path / 'owned.pdf';raw = scan_pdf('ownedcrashcandidate');path.write_bytes(raw)
    database = tmp_path / 'archive.sqlite3'
    code = '''from pathlib import Path
import sys
from smm_local.core import Archive
from smm_local.documents import Documents
d=Documents(Archive(Path(sys.argv[1])))
s=d.add(sys.argv[2])
d.refresh(s['id'])
'''
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(hooks), str(ROOT / 'tests'), str(ROOT / 'src')]),
               PYTHONUTF8='1', SMM_008_HEALTH_CONTROL=str(control))
    child = subprocess.Popen([sys.executable, '-B', '-c', code, str(database), str(path)],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    records = []
    try:
        deadline = time.monotonic() + 10
        while not list(control.glob('worker-ready-*.json')):
            assert child.poll() is None and time.monotonic() < deadline
            time.sleep(.01)
        ready = json.loads(next(control.glob('worker-ready-*.json')).read_text())
        token = ready['token']
        while not (control / ('watch-live-' + token + '.json')).exists():
            assert child.poll() is None and time.monotonic() < deadline
            time.sleep(.01)
        live = json.loads((control / ('watch-live-' + token + '.json')).read_text())
        full_records = [ready['worker'], ready['descendant'], live['watcher']]
        assert all(Path(record['cwd']).resolve() == Path(ready['directory']).resolve() for record in full_records)
        records = [{k: record[k] for k in ('pid', 'created', 'argv', 'exe')} for record in full_records]
        assert all(matching_process(record) is not None for record in records)
        documents = Documents(Archive(database));snapshots = documents.snapshots
        sha = hashlib.sha256(raw).hexdigest()
        snapshots.put('raw', b'admission while real content worker is alive')
        assert snapshots.blob('raw', sha).read_bytes() == raw
        # Suspend only our verified independent watcher. After controller
        # death, worker/helper remain genuinely live: GC must retain the task
        # pin until the watcher resumes and proves whole-tree/payload cleanup.
        import signal,psutil
        watcher=matching_process(records[-1]);watcher.send_signal(signal.SIGSTOP)
        deadline=time.monotonic()+2
        while watcher.status()!=psutil.STATUS_STOPPED:
            assert time.monotonic()<deadline
            time.sleep(.005)
        child.kill();child.wait(timeout=5)
        source = next(s for s in documents.sources() if s['path'] == str(path))
        documents.remove(source['id'])
        snapshots.put('raw',b'admission after controller exit with live parser tree')
        assert all(matching_process(record) is not None for record in records[:2])
        assert snapshots.blob('raw',sha).read_bytes()==raw
        assert Path(ready['payload']).exists()
        observe('live-orphan-task-pin-protected',{'token':token,'registered_tree':records,'raw_sha256':sha})
        matching_process(records[-1]).send_signal(signal.SIGCONT)
        deadline = time.monotonic() + 8
        while any(waiting_for_owned_exit(record) for record in records):
            assert time.monotonic() < deadline, records
            time.sleep(.01)
        task = Path(ready['directory'])
        assert not Path(ready['payload']).exists(), 'terminated task retained parser temporary payload'
        assert not (task.parent / 'active.json').exists(), 'terminated controller retained the active lease'
        terminal = json.loads((task / 'supervision.json').read_text())
        assert terminal['token'] == token and terminal['status'] == 'failed'
        snapshots.put('raw', b'admission after independently observed whole task exit')
        observe('real-content-pin-recovery', {'token': token, 'registered_tree': records,
            'controller_exit': child.returncode, 'remaining_blob': snapshots.blob('raw', sha).exists()})
        assert not snapshots.blob('raw', sha).exists()
        assert not list((snapshots.root / 'reclamation').glob('pin-*.json'))
    finally:
        (control / 'release-all').touch()
        if child.poll() is None:child.kill()
        child.wait(timeout=5)
        terminate_verified(records)
        child.stdout.close();child.stderr.close()


@pytest.mark.skipif(os.name!='nt',reason='actual Windows Job Object membership and owner death')
def test_windows_job_owner_crash_recovers_pin(tmp_path):
    import psutil
    from test_document_formats_management import native_input
    control=tmp_path/'control';control.mkdir()
    nonce=uuid4().hex;(control/'control.json').write_text(json.dumps({'nonce':nonce}))
    hooks=tmp_path/'hooks';hooks.mkdir()
    (hooks/'sitecustomize.py').write_text('from document_formats_windows_recovery import install\ninstall()\n')
    path=tmp_path/'Windows 原件.docx';raw,_=native_input('docx','windowsjobpending');path.write_bytes(raw)
    database=tmp_path/'archive.sqlite3'
    code='''from pathlib import Path
import sys
from smm_local.core import Archive
from smm_local.documents import Documents
d=Documents(Archive(Path(sys.argv[1])))
s=d.add(sys.argv[2]);d.refresh(s['id'])
'''
    env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(hooks),str(ROOT/'tests'),str(ROOT/'src')]),
             PYTHONUTF8='1',PYTHONIOENCODING='utf-8',SMM_008_WINDOWS_RECOVERY=str(control))
    argv=[sys.executable,'-B','-c',code,str(database),str(path)]
    child=subprocess.Popen(argv,cwd=tmp_path,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    bootstrap=spawn_identity(psutil.Process(child.pid));records=[]
    try:
        deadline=time.monotonic()+15
        while not (control/'worker.json').exists() or not (control/'job.json').exists():
            assert child.poll() is None and time.monotonic()<deadline
            time.sleep(.01)
        job=read_fixture_json(control/'job.json',deadline=deadline)
        ready=read_fixture_json(control/'worker.json',deadline=deadline)
        assert job['nonce']==ready['nonce']==nonce
        controller=job['controller']
        stamp=verify_server(bootstrap,{'pid':controller['pid'],'archive':str(database),'owner':'local','nonce':nonce},
            argv=argv,archive=database,owner='local',nonce=nonce,cwd=tmp_path,
            executables=[sys.executable,sys._base_executable])
        members=[ready['worker'],ready['descendant']]
        records=[stamp]+[{k:value[k] for k in ('pid','created','argv','exe')} for value in members]
        assert all(matching_process(record) is not None for record in records)
        assert ready['raw_sha256']==hashlib.sha256(raw).hexdigest()
        assert all(document_formats_windows_recovery.specific_job_contains(stamp['pid'],job['handle'],value['pid']) for value in members), 'parser or descendant escaped the exact creator Job Object'
        # Every query duplicate was closed before owner death, preserving the
        # real KILL_ON_JOB_CLOSE semantics of the product's sole job handle.
        observe('windows-actual-job-membership',{'controller':stamp,'members':records[1:],'nonce':nonce,
            'exact_job_membership_verified':True,'query_handles_closed':True})
        matching_process(stamp).kill();child.wait(timeout=8)
        # Exercise product recovery immediately, before the test waits for
        # any Job member. Unconfirmed termination must keep the raw/pin; a
        # later admission may reclaim it only after the real whole tree exits.
        documents=Documents(Archive(database));snapshots=documents.snapshots
        source=next(s for s in documents.sources() if s['path']==str(path.resolve()))
        documents.remove(source['id'])
        task=Path(ready['directory']);sha=hashlib.sha256(raw).hexdigest()
        deadline=time.monotonic()+8;attempts=[]
        while True:
            snapshots.put('raw',b'admission after real Windows job owner death')
            unconfirmed=[record for record in records if waiting_for_owned_exit(record)]
            reclaimed=not snapshots.blob('raw',sha).exists()
            attempts.append({'reclaimed':reclaimed,'unconfirmed':unconfirmed})
            if reclaimed:
                assert not unconfirmed,'product reclaimed before exact Job members exited'
                break
            assert time.monotonic()<deadline,attempts
            time.sleep(.01)
        observe('windows-immediate-recovery-order',{'attempts':attempts,'deadline_seconds':8,
            'test_waited_before_first_admission':False})
        assert not list((snapshots.root/'reclamation').glob('pin-*.json'))
        assert not Path(ready['payload']).exists()
        assert not (task.parent/'active.json').exists()
        assert json.loads((task/'supervision.json').read_text(encoding='utf-8'))['status']=='failed'
        assert path.read_bytes()==raw
        observe('windows-actual-job-pin-recovery',{'token':ready['token'],'controller_exit':child.returncode,
            'raw_sha256':sha,'tree_exited':True,'staging_reclaimed':True})
    finally:
        (control/'release').touch()
        for record in process_tree(bootstrap):
            if record not in records:records.append(record)
        terminate_verified(records,owner=child)
        if child.poll() is None:child.kill()
        child.wait(timeout=5)
        stdout=child.stdout.read();stderr=child.stderr.read()
        observe('windows-job-controller-output',{'exit':child.returncode,
            'stdout':stdout.decode('utf-8',errors='replace'),'stderr':stderr.decode('utf-8',errors='replace')})
        child.stdout.close();child.stderr.close()


@pytest.mark.skipif(not FONT, reason='requires prepared real PDF fixture font')
@pytest.mark.parametrize('registered_copy', [False, True])
def test_copied_archive_identity_never_retires_the_other_database_candidate(tmp_path, registered_copy):
    # A copied SQLite identity is ambiguous; no GC ownership is inferred.
    import sqlite3
    first = Documents(Archive(tmp_path / 'original.sqlite3'))
    path = tmp_path / 'copied-owner.pdf'
    raw = scan_pdf('copiedarchivecandidate')
    path.write_bytes(raw)
    source = first.add(str(path))
    first.refresh(source['id'])
    rows = first.files(source['id'])
    assert len(rows) == 1
    item = rows[0]
    retry = item['retry_target']
    assert item['latest_attempt']['status'] == 'failed' and item['published_snapshot'] is None
    assert retry and retry['sha256'] == hashlib.sha256(raw).hexdigest()
    with first.db.connect() as con, sqlite3.connect(tmp_path / 'copied.sqlite3') as clone:
        con.backup(clone)
    second = Documents(Archive(tmp_path / 'copied.sqlite3'))
    assert material(first.db)[0] == material(second.db)[0]
    if registered_copy:
        second.snapshots.put('raw', raw)
    second.remove(source['id'])
    third = Documents(Archive(tmp_path / 'third.sqlite3'))
    third.snapshots.put('raw', b'independent third archive admission after copied removal')
    assert first.files(source['id'])[0]['retry_target'] == retry
    second.snapshots.put('raw', b'admission after removing only the copied source')
    assert first.files(source['id'])[0]['retry_target'] == retry
    first.snapshots.put('raw', b'original archive admission after copied removal')
    assert first.snapshots.blob('raw', retry['sha256']).read_bytes() == raw
    assert not first.snapshots.retired('captures', retry['capture_id'])
    assert not first.snapshots.retired('attempts', retry['expected_attempt_id'])
    assert first.snapshots._unpublished_bytes() >= len(raw)
    token = first.snapshots.retry(item['id'], retry['capture_id'], retry['expected_attempt_id'],
                                  retry['expected_version'], retry['expected_processing_version'])
    assert token['capture_id'] == retry['capture_id']
    assert token['attempt_id'] != retry['expected_attempt_id']
    with first.db.connect() as con:
        state = con.execute('SELECT current_capture,latest_attempt FROM document_snapshot_state WHERE document_pk=?', (token['document_pk'],)).fetchone()
        attempt = con.execute('SELECT capture_id,state FROM document_processing_attempts WHERE id=?', (token['attempt_id'],)).fetchone()
        assert tuple(state) == (retry['capture_id'], token['attempt_id'])
        assert tuple(attempt) == (retry['capture_id'], 'pending')
    first.snapshots.fail_current(token, 'test ends after confirming the saved original can be retried')
    assert path.read_bytes() == raw
    observe('copied-archive-candidate-protection', {'registered_copy': registered_copy,
        'capture_id': retry['capture_id'], 'raw_sha256': retry['sha256'],
        'raw_bytes': len(raw), 'retained_bytes': first.snapshots._unpublished_bytes()})

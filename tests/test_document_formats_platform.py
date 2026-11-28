"""Real platform controls for shared test facilities, not full E/H/X acceptance."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import psutil
import pytest
from document_helpers import observe
from document_formats_platform import (
    path_key, windows_target_key, utf8_environment, process_identity,spawn_identity,
    matching_process, process_tree, verify_server, terminate_verified,
    diagnostics_on_failure,
)
from test_document_formats_upload_restart import Server
from test_document_formats_retry import keep


def test_platform_path_keys_preserve_distinct_and_special_targets(tmp_path):
    first=tmp_path/'First源';second=tmp_path/'Second源'
    first.write_bytes(b'first');second.write_bytes(b'second')
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (first,second)}
    assert path_key(first)!=path_key(second)
    if os.name=='nt':assert path_key(first)==path_key(str(first).upper())
    else:assert path_key(first)!=path_key(str(first).upper())
    pairs=[(r'\\?\C:\Folder\File',r'C:\Folder\File'),
           (r'\\?\UNC\Server\Share\Folder\File',r'\\Server\Share\Folder\File')]
    for left,right in pairs:assert windows_target_key(left)==windows_target_key(right)
    assert windows_target_key(r'\\?\C:\Folder\File.')!=windows_target_key(r'C:\Folder\File.')
    assert windows_target_key(r'\\?\C:\Folder\..\File')!=windows_target_key(r'C:\Folder\..\File')
    assert windows_target_key(r'C:\A\File')!=windows_target_key(r'C:\B\File')
    assert first.read_bytes()==b'first' and second.read_bytes()==b'second'
    assert {p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (first,second)}==before
    observe('platform-path-controls',{'native_case_insensitive':os.name=='nt','ordinary_namespace_pairs':pairs,'special_extended_paths_preserved':True,'distinct_targets_preserved':True})


def test_child_logs_preserve_utf8_and_actual_nonzero_exit():
    stdout='已收到文档 α 😺\n';stderr='真实失败原因 β 😺\n'
    script='import sys;sys.stdout.write('+repr(stdout)+');sys.stderr.write('+repr(stderr)+');raise SystemExit(23)'
    r=subprocess.run([sys.executable,'-B','-c',script],env=utf8_environment(os.environ),capture_output=True,timeout=10)
    keep('platform-utf8/stdout.bin',r.stdout);keep('platform-utf8/stderr.bin',r.stderr)
    expected_stdout=stdout.replace('\n',os.linesep).encode('utf-8')
    expected_stderr=stderr.replace('\n',os.linesep).encode('utf-8')
    assert r.returncode==23 and r.stdout==expected_stdout and r.stderr==expected_stderr
    observe('platform-utf8-control',{'exit_code':r.returncode,'stdout':r.stdout.decode('utf-8'),'stderr':r.stderr.decode('utf-8')})


def test_failed_operation_keeps_raw_diagnostics_and_original_exception(tmp_path,monkeypatch):
    root=tmp_path/'task';root.mkdir();raw='原始错误：识别失败 😺\n'.encode('utf-8')
    (root/'worker.stderr').write_bytes(raw)
    (root/'credentials.json').write_bytes(b'must never be copied')
    destination=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'proof')))/'diagnostic-self-control'
    monkeypatch.setenv('ACCEPTANCE_EVIDENCE_DIR',str(destination))
    @diagnostics_on_failure
    def fail(self):raise LookupError('original failure remains visible')
    with pytest.raises(LookupError,match='original failure remains visible'):
        fail(SimpleNamespace(root=root,number=1))
    indexes=list((destination/'diagnostics').glob('*.json'));assert len(indexes)==1
    value=json.loads(indexes[0].read_bytes());digest=hashlib.sha256(raw).hexdigest()
    assert value['files']==[{'path':'worker.stderr','sha256':digest,'bytes':len(raw)}]
    assert (destination/'diagnostics/blobs'/digest).read_bytes()==raw
    assert (root/'credentials.json').read_bytes()==b'must never be copied'
    observe('platform-failure-diagnostics',{'index':value,'copied_original_sha256':digest,'original_exception_preserved':True})


def test_real_failed_start_keeps_child_stderr_and_cleans_task_process(tmp_path,monkeypatch):
    import test_document_formats_upload_restart as runtime
    destination=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'proof')))/'failed-start-control'
    monkeypatch.setenv('ACCEPTANCE_EVIDENCE_DIR',str(destination))
    # Actual child imports fail from a task-only missing module location.
    monkeypatch.setattr(runtime,'ROOT',tmp_path/'missing-code')
    server=Server(tmp_path/'failed-service','local')
    try:
        with pytest.raises(AssertionError,match='document_formats_restart_server'):
            server.start()
    finally:
        stopped=server.stop()
    assert stopped['exit']!=0 and all(matching_process(stamp) is None for stamp in stopped['members'])
    raw=server.stderr.read_bytes();assert b'document_formats_restart_server' in raw
    digest=hashlib.sha256(raw).hexdigest()
    assert (destination/'diagnostics/blobs'/digest).read_bytes()==raw
    indexes=[json.loads(p.read_bytes()) for p in (destination/'diagnostics').glob('*.json')]
    assert any(any(row.get('sha256')==digest for row in i['files']) for i in indexes)
    observe('platform-real-failed-start',{'exit':stopped['exit'],'stderr_sha256':digest,'original_failure_preserved':True,'cleanup':stopped})


def test_enrollment_failure_and_cleanup_failure_preserve_original_and_identity(tmp_path,monkeypatch):
    import test_document_formats_upload_restart as runtime
    destination=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'proof')))/'enrollment-failure-control'
    monkeypatch.setenv('ACCEPTANCE_EVIDENCE_DIR',str(destination))
    server=Server(tmp_path/'enrollment-service','local')
    def reject(*args,**kwargs):raise AssertionError('known enrollment rejection')
    def fail_cleanup():raise RuntimeError('known cleanup failure')
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(runtime,'verify_server',reject)
            with pytest.raises(AssertionError,match='known enrollment rejection'):
                try:server.start()
                finally:
                    with monkeypatch.context() as cleanup:
                        cleanup.setattr(server,'_owned_tree',fail_cleanup)
                        incomplete=server.stop()
        assert incomplete['status']=='incomplete' and incomplete['error']=='known cleanup failure'
        packet=json.loads((server.root/'identity-1.json').read_bytes())
        assert packet['http_status']==200 and packet['http_identity']['nonce']==server.nonce
        assert packet['bootstrap']==server.bootstrap_stamp and packet['requested_argv']==server.argv
        assert packet['current_tree'] and packet['expected_archive']==str(server.db)
        assert matching_process(server.bootstrap_stamp) is not None
        stopped=server.stop()
        assert stopped['forced'] is True and all(matching_process(stamp) is None for stamp in stopped['members'])
        indexes=[json.loads(p.read_bytes()) for p in (destination/'diagnostics').glob('*.json')]
        copied={row['sha256'] for index in indexes for row in index['files'] if 'sha256' in row}
        for name in ('identity-1.json','cleanup-incomplete.json'):
            raw=(server.root/name).read_bytes();digest=hashlib.sha256(raw).hexdigest()
            assert digest in copied and (destination/'diagnostics/blobs'/digest).read_bytes()==raw
        observe('platform-enrollment-failure-control',{'identity':packet,'cleanup_failure':incomplete,'actual_cleanup':stopped,'original_enrollment_exception_preserved':True})
    finally:server.stop()


def test_business_failure_and_cleanup_failure_keep_original_and_raw_identity(tmp_path,monkeypatch):
    destination=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'proof')))/'body-failure-control'
    monkeypatch.setenv('ACCEPTANCE_EVIDENCE_DIR',str(destination))
    server=Server(tmp_path/'body-service','local')
    def fail_cleanup():raise RuntimeError('known body cleanup failure')
    try:
        server.start();assert server.start_failed is False
        with pytest.raises(LookupError,match='known original business failure'):
            try:raise LookupError('known original business failure')
            finally:
                with monkeypatch.context() as cleanup:
                    cleanup.setattr(server,'_owned_tree',fail_cleanup)
                    incomplete=server.stop()
        assert incomplete['status']=='incomplete' and incomplete['error']=='known body cleanup failure'
        assert incomplete['original_error']=='known original business failure'
        assert matching_process(server.serving_stamp) is not None
        packet=json.loads((server.root/'identity-1.json').read_bytes())
        assert packet['http_status']==200 and packet['http_identity']['pid']==server.serving_pid
        stopped=server.stop()
        assert stopped['forced'] is False and all(matching_process(stamp) is None for stamp in stopped['members'])
        indexes=[json.loads(p.read_bytes()) for p in (destination/'diagnostics').glob('*.json')]
        copied={row['sha256'] for index in indexes for row in index['files'] if 'sha256' in row}
        for name in ('identity-1.json','cleanup-incomplete.json'):
            raw=(server.root/name).read_bytes();digest=hashlib.sha256(raw).hexdigest()
            assert digest in copied and (destination/'diagnostics/blobs'/digest).read_bytes()==raw
        observe('platform-body-failure-control',{'identity':packet,'cleanup_failure':incomplete,'actual_cleanup':stopped,'original_business_exception_preserved':True})
    finally:server.stop()


@pytest.mark.parametrize('owner',['local','hub'])
def test_actual_serving_identity_rejects_foreign_pid_and_stops_only_own_tree(tmp_path,owner):
    # TC-008-platform-runtime-controls; source/debug identity only, no document claim.
    server=Server(tmp_path/owner,owner)
    foreign=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(90)'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=os.name!='nt')
    foreign_stamp=spawn_identity(psutil.Process(foreign.pid))
    try:
        server.start()
        value=server.client.get('/__test_identity').json()
        expected=dict(argv=server.argv,archive=server.db,owner=owner,nonce=server.nonce,cwd=server.root,executables=server.allowed_executables)
        assert verify_server(server.launcher_stamp,value,**expected)==server.serving_stamp
        assert server.call('GET','/documents/files').json()==[]
        # Bad identity must fail before any signal/stop action on the foreign PID.
        for field,bad in [('pid',foreign.pid),('pid',True),('archive',str(tmp_path/'another.sqlite3')),('owner','another-owner'),('nonce','another-task')]:
            with pytest.raises(AssertionError):verify_server(server.launcher_stamp,{**value,field:bad},**expected)
            assert matching_process(foreign_stamp) is not None
        with pytest.raises(AssertionError):
            verify_server({**server.launcher_stamp,'created':server.launcher_stamp['created']+1},value,**expected)
        with pytest.raises(AssertionError):
            terminate_verified([{**foreign_stamp,'created':foreign_stamp['created']+1}])
        denied=server.client.post('/__test_shutdown',headers={'X-SMM-Test-Nonce':'another-task'})
        assert denied.status_code==403 and matching_process(server.serving_stamp) is not None
        stopped=server.stop()
        assert stopped['forced'] is False and stopped['audit']==[]
        assert all(matching_process(stamp) is None for stamp in stopped['members'])
        assert matching_process(foreign_stamp) is not None
        observe('platform-real-serving-controls',{'owner':owner,'launcher':server.launcher_stamp,'serving':server.serving_stamp,'cleanup':stopped,'foreign_stamp':foreign_stamp,'foreign_alive_after_cleanup':True})
    finally:
        try:server.stop()
        finally:
            terminate_verified(process_tree(foreign_stamp),owner=foreign)
            foreign.wait(timeout=3)


def test_normal_exit_between_creation_check_and_full_identity_is_not_cleanup_failure(tmp_path,monkeypatch):
    import document_formats_platform as runtime
    import time
    ready=tmp_path/'normal-exit-ready'
    code='from pathlib import Path;import sys;Path('+repr(str(ready))+').write_bytes(b"ready");sys.stdin.buffer.readline();sys.stdout.buffer.write(b"normal exit\\n")'
    child=subprocess.Popen([sys.executable,'-B','-c',code],env=utf8_environment(os.environ),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=os.name!='nt')
    seed=spawn_identity(psutil.Process(child.pid));original=runtime.matching_process;triggered=[]
    try:
        until=time.monotonic()+10
        while not ready.exists() and child.poll() is None and time.monotonic()<until:time.sleep(.01)
        assert ready.exists() and child.poll() is None
        stamp=process_identity(psutil.Process(child.pid))
        with pytest.raises(AssertionError):runtime.refresh_owned_records([{**stamp,'created':stamp['created']+1}],{sys.executable})
        assert child.poll() is None
        def exit_after_lookup(candidate):
            process=original(candidate)
            if process is not None and process.pid==child.pid and not triggered:
                out,err=child.communicate(input=b'go\n',timeout=5);triggered.append({'exit':child.returncode,'stdout':out.decode('utf-8'),'stderr':err.decode('utf-8')})
                keep('normal-exit/stdout.bin',out);keep('normal-exit/stderr.bin',err)
            return process
        with monkeypatch.context() as scope:
            scope.setattr(runtime,'matching_process',exit_after_lookup)
            assert runtime.refresh_owned_records([stamp],{sys.executable})==[]
        assert triggered==[{'exit':0,'stdout':'normal exit\n','stderr':''}]
        observe('platform-normal-exit-interleave',{'stamp':stamp,'exit_between_live_check_and_identity':triggered,'stale_creation_rejected_before_release':True})
    finally:
        if child.poll() is None:terminate_verified(process_tree(seed),owner=child)
        child.wait(timeout=3)

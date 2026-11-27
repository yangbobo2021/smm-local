"""Actual owned exit/creation controls for the isolated read-only observer."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import psutil
import pytest
from document_formats_exit_observer import waiting_for_owned_exit
from document_formats_platform import process_tree,spawn_identity,matching_process,utf8_environment,terminate_verified
from document_helpers import ROOT,observe
from document_formats_fixture_io import read_fixture_json


@contextmanager
def owned(tmp_path):
    ready=tmp_path/'ready.json';nonce=uuid4().hex
    code='''import os,json,sys
from pathlib import Path
import psutil
from document_formats_platform import process_identity
p=Path(sys.argv[1]);q=p.with_suffix('.new');q.write_text(json.dumps({'nonce':sys.argv[2],'identity':process_identity(psutil.Process())}),encoding='utf-8');q.replace(p)
sys.stdin.buffer.read(1);os._exit(0)
'''
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'tests'),str(ROOT/'src')]))
    with (tmp_path/'child.stderr').open('wb') as errors:
        child=subprocess.Popen([sys.executable,'-B','-c',code,str(ready),nonce],env=env,cwd=tmp_path,
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
        bootstrap=spawn_identity(psutil.Process(child.pid));records=[]
        try:
            deadline=time.monotonic()+5
            while not ready.exists():
                assert child.poll() is None and time.monotonic()<deadline
                time.sleep(.005)
            value=read_fixture_json(ready,deadline=deadline);assert value['nonce']==nonce
            records=process_tree(bootstrap);stamp=value['identity']
            assert stamp in records and matching_process(stamp) is not None
            yield child,stamp
        finally:
            try:child.stdin.close()
            except BrokenPipeError:pass
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                terminate_verified(records,owner=child)
                child.wait(timeout=3)


def test_owned_live_exit_and_strict_enrollment_remain_distinct(tmp_path):
    with owned(tmp_path) as (child,stamp):
        assert waiting_for_owned_exit(stamp) is True
        with pytest.raises(AssertionError):waiting_for_owned_exit({**stamp,'created':stamp['created']+1})
        with pytest.raises(AssertionError):waiting_for_owned_exit({'pid':stamp['pid'],'created':stamp['created']})
        with pytest.raises(AssertionError):matching_process({**stamp,'argv':stamp['argv']+['wrong-enrollment']})
        child.stdin.write(b'x');child.stdin.flush()
        deadline=time.monotonic()+2
        while waiting_for_owned_exit(stamp):
            assert time.monotonic()<deadline
            time.sleep(.005)
        assert child.wait(timeout=3)==0
        assert waiting_for_owned_exit(stamp) is False
        observe('isolated-exit-live-dead-control',{'stamp':stamp,'exit':child.returncode,'wrong_creation_rejected':True,'strict_enrollment_rejected':True})


@pytest.mark.skipif(os.name=='nt',reason='Windows has no unreaped POSIX zombie state')
def test_unreaped_real_zombie_still_checks_creation_first(tmp_path):
    with owned(tmp_path) as (child,stamp):
        child.stdin.write(b'x');child.stdin.flush()
        deadline=time.monotonic()+2
        while psutil.Process(stamp['pid']).status()!=psutil.STATUS_ZOMBIE:
            assert time.monotonic()<deadline
            time.sleep(.005)
        # Do not call Popen.poll/wait before these checks: the real child is
        # deliberately unreaped, not a mocked zombie response.
        assert waiting_for_owned_exit(stamp) is False
        with pytest.raises(AssertionError):waiting_for_owned_exit({**stamp,'created':stamp['created']+1})
        assert child.wait(timeout=3)==0
        observe('isolated-exit-zombie-control',{'stamp':stamp,'wrong_creation_rejected_before_zombie':True,'exit':child.returncode})


@pytest.mark.parametrize('method',['create_time','is_running','status'])
def test_denied_observation_stays_pending_with_original_deadline(tmp_path,monkeypatch,method):
    with owned(tmp_path) as (child,stamp):
        calls=[]
        def deny(self,*a,**kw):calls.append(self.pid);raise psutil.AccessDenied(self.pid)
        with monkeypatch.context() as patch:
            patch.setattr(psutil.Process,method,deny)
            deadline=time.monotonic()+.03
            while time.monotonic()<deadline:assert waiting_for_owned_exit(stamp) is True
            assert calls
        assert waiting_for_owned_exit(stamp) is True
        observe('isolated-exit-denial-control',{'method':method,'all_denials_pending':True,'calls':len(calls),'deadline_not_reset':True})


def test_exit_polling_never_rereads_argv_or_exe(tmp_path,monkeypatch):
    with owned(tmp_path) as (child,stamp):
        def forbidden(*args,**kwargs):raise AssertionError('exit polling read mutable argv/exe')
        with monkeypatch.context() as patch:
            patch.setattr(psutil.Process,'cmdline',forbidden);patch.setattr(psutil.Process,'exe',forbidden)
            assert waiting_for_owned_exit(stamp) is True
        assert matching_process(stamp) is not None
        observe('isolated-exit-no-argv-control',{'stamp':stamp,'strict_enrollment_retained':True})

"""Real Windows job membership and parser gates for task-owned recovery tests."""
import builtins
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from document_formats_fixture_io import read_fixture_json


DESCENDANT = '''import json,os,sys,time
from pathlib import Path
import psutil
p=psutil.Process();target=Path(sys.argv[1]);control=Path(sys.argv[2])
value={'pid':p.pid,'created':p.create_time(),'argv':p.cmdline(),'exe':os.path.normcase(str(Path(p.exe()).resolve())),
       'nonce':sys.argv[3],'cwd':p.cwd()}
t=target.with_suffix('.new');t.write_text(json.dumps(value),encoding='utf-8');t.replace(target)
deadline=time.monotonic()+60
while not (control/'release').exists():
 assert time.monotonic()<deadline
 time.sleep(.01)
'''


def write(path,value):
    temporary=path.with_suffix('.new')
    temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    temporary.replace(path)


def identity():
    import psutil
    from document_formats_platform import process_identity
    p=psutil.Process()
    return {**process_identity(p),'cwd':p.cwd()}


def install():
    if os.name!='nt' or not os.environ.get('SMM_008_WINDOWS_RECOVERY'):return
    control=Path(os.environ['SMM_008_WINDOWS_RECOVERY'])
    nonce=json.loads((control/'control.json').read_text(encoding='utf-8'))['nonce']
    if '--task-token' not in sys.orig_argv:
        from smm_local.document_supervisor import WindowsJob
        original=WindowsJob.__init__
        def created(job,*args,**kwargs):
            original(job,*args,**kwargs)
            handle=job.handle if isinstance(job.handle,int) else job.handle.value
            write(control/'job.json',{'controller':identity(),'handle':handle,'nonce':nonce})
        WindowsJob.__init__=created
        return
    token=sys.orig_argv[sys.orig_argv.index('--task-token')+1]
    original_import=builtins.__import__
    def importing(name,*args,**kwargs):
        module=original_import(name,*args,**kwargs)
        if name.endswith('document_formats.word') and hasattr(module,'parse') and not getattr(module,'_recovery_gate',False):
            original=module.parse
            module._recovery_gate=True
            def gated(raw,sha,profile,*a,**kw):
                assert hashlib.sha256(raw).hexdigest()==sha
                ready=control/'descendant.json'
                command=[sys.executable,'-B','-c',DESCENDANT,str(ready),str(control),nonce]
                child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try:
                    deadline=time.monotonic()+8
                    while not ready.exists():
                        assert child.poll() is None and time.monotonic()<deadline
                        time.sleep(.01)
                    descendant=read_fixture_json(ready,deadline=deadline)
                    assert descendant['nonce']==nonce
                    payload=Path.cwd()/'owned-windows-payload.bin';payload.write_bytes(b'owned Windows parser payload')
                    write(control/'worker.json',{'worker':identity(),'descendant':descendant,'nonce':nonce,
                        'token':token,'raw_sha256':sha,'directory':str(Path.cwd()),'payload':str(payload)})
                    while not (control/'release').exists():
                        assert time.monotonic()<deadline+45
                        time.sleep(.01)
                finally:
                    (control/'release').touch()
                    child.wait(timeout=3)
                return original(raw,sha,profile,*a,**kw)
            module.parse=gated
        return module
    builtins.__import__=importing


def specific_job_contains(controller_pid,job_handle,member_pid):
    """Query the exact real job, closing the duplicate before owner death."""
    import ctypes as c
    from ctypes import wintypes as w
    k=c.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.GetCurrentProcess.restype=w.HANDLE
    k.DuplicateHandle.argtypes=[w.HANDLE,w.HANDLE,w.HANDLE,c.POINTER(w.HANDLE),w.DWORD,w.BOOL,w.DWORD];k.DuplicateHandle.restype=w.BOOL
    k.IsProcessInJob.argtypes=[w.HANDLE,w.HANDLE,c.POINTER(w.BOOL)];k.IsProcessInJob.restype=w.BOOL
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    owner=k.OpenProcess(0x40,False,controller_pid);member=k.OpenProcess(0x1000,False,member_pid);duplicate=w.HANDLE()
    assert owner and member,c.get_last_error()
    try:
        assert k.DuplicateHandle(owner,w.HANDLE(job_handle),k.GetCurrentProcess(),c.byref(duplicate),0,False,2),c.get_last_error()
        value=w.BOOL()
        assert k.IsProcessInJob(member,duplicate,c.byref(value)),c.get_last_error()
        return bool(value.value)
    finally:
        if duplicate:assert k.CloseHandle(duplicate)
        assert k.CloseHandle(member)
        assert k.CloseHandle(owner)

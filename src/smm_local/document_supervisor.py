"""Archive-wide supervised creator tasks, gated workers and checked process IDs."""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from .archive_protocol import atomic_json,control_lock

RSS_LIMIT=1024*1024*1024
TEMP_LIMIT=256*1024*1024
TIME_LIMIT=300


def temporary_bytes(root):
    """Sample live regular files while workers may remove completed temporaries."""
    root.stat()  # The task directory itself must remain observable.
    def walk_error(exc):
        if not isinstance(exc,FileNotFoundError):raise exc
    used=0
    for directory,_,files in os.walk(root,followlinks=False,onerror=walk_error):
        for name in files:
            try:info=(Path(directory)/name).stat()
            except FileNotFoundError:continue
            if stat.S_ISREG(info.st_mode):used+=info.st_size
    root.stat()
    return used


def identity(process):return {'pid':process.pid,'created':process.create_time()}

def matching(stamp,token=None):
    import psutil
    try:
        process=psutil.Process(stamp['pid'])
        if process.create_time()!=stamp['created']:return None
        if token is not None and token not in process.cmdline():return None
        return process
    except (psutil.NoSuchProcess,psutil.ZombieProcess):return None


def stop_tree(stamp,token,known=()):
    import psutil
    parent=matching(stamp,token)
    children=[]
    if parent:
        try:children=parent.children(recursive=True)
        except psutil.NoSuchProcess:pass
    valid=[p for s in known if (p:=matching(s)) is not None]
    processes={p.pid:p for p in children+valid+([parent] if parent else [])}
    if os.name!='nt':
        # A live, creation-time-verified member proves this is still our group.
        for p in processes.values():
            try:
                if os.getpgid(p.pid)==stamp['pid']:
                    os.killpg(stamp['pid'],signal.SIGKILL);break
            except ProcessLookupError:pass
    for process in processes.values():
        try:process.kill()
        except psutil.NoSuchProcess:pass
    psutil.wait_procs(list(processes.values()),timeout=2)


class WindowsJob:
    def __init__(self,child):
        import ctypes
        from ctypes import wintypes as w
        class BASIC(ctypes.Structure):
            _fields_=[('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),('Flags',w.DWORD),('MinWorkingSet',ctypes.c_size_t),('MaxWorkingSet',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class IO(ctypes.Structure):_fields_=[(name,ctypes.c_ulonglong) for name in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
        class EXTENDED(ctypes.Structure):_fields_=[('Basic',BASIC),('IO',IO),('ProcessMemory',ctypes.c_size_t),('JobMemory',ctypes.c_size_t),('PeakProcessMemory',ctypes.c_size_t),('PeakJobMemory',ctypes.c_size_t)]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];kernel.CreateJobObjectW.restype=w.HANDLE
        kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];kernel.SetInformationJobObject.restype=w.BOOL
        kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];kernel.AssignProcessToJobObject.restype=w.BOOL
        kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
        handle=kernel.CreateJobObjectW(None,None)
        if not handle:raise OSError(ctypes.get_last_error(),'无法创建监督Job Object')
        info=EXTENDED();info.Basic.Flags=0x2000 # KILL_ON_JOB_CLOSE, no breakaway
        if not kernel.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(handle,w.HANDLE(int(child._handle))):
            code=ctypes.get_last_error();kernel.CloseHandle(handle);raise OSError(code,'无法将worker纳入Job Object')
        self.kernel=kernel;self.handle=handle
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None


def watch(path):
    import psutil
    initial=json.loads(Path(path).read_text());known=[]
    while True:
        worker=matching(initial['worker'],initial['token'])
        if worker:
            try:known=[identity(p) for p in worker.children(recursive=True)]
            except psutil.NoSuchProcess:pass
        controller=matching(initial['controller'])
        if controller is None or worker is None:
            stop_tree(initial['worker'],initial['token'],known);return
        time.sleep(.05)


def run(db,request,task_directory):
    import psutil
    root=Path(task_directory);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    lease=root.parent/'active.json';lock=root.parent/'processing.lock'
    with control_lock(lock):
        if lease.exists():
            old=json.loads(lease.read_text())
            if matching(old['worker'],old['token']):
                if matching(old['controller']):raise ValueError('另一内容处理任务仍在运行')
                stop_tree(old['worker'],old['token'],old.get('children',[]))
        token=request['task_token'];log=root/'worker.stderr';stdout=root/'worker.stdout'
        child=None;job=None;watchdog=None;known=[];peak=0;started=time.monotonic()
        with log.open('wb') as errors,stdout.open('wb') as output:
            try:
                child=subprocess.Popen([sys.executable,'-B','-m',__package__+'.document_worker','--task-token',token],stdin=subprocess.PIPE,stdout=output,stderr=errors,cwd=root,start_new_session=os.name!='nt')
                process=psutil.Process(child.pid);stamp=identity(process)
                if os.name=='nt':job=WindowsJob(child)
                state={'token':token,'worker':stamp,'controller':identity(psutil.Process()),'children':[],'status':'processing','rss_limit':RSS_LIMIT,'temp_limit':TEMP_LIMIT,'seconds_limit':TIME_LIMIT}
                atomic_json(lease,state);atomic_json(root/'supervision.json',state)
                if os.name!='nt':
                    watchdog=subprocess.Popen([sys.executable,'-B','-m',__package__+'.document_supervisor','--watch',str(root/'supervision.json')],stdin=subprocess.DEVNULL,stdout=output,stderr=errors,cwd=root,start_new_session=True)
                # Optional parser imports are unreachable before this gate.
                child.stdin.write(json.dumps(request).encode('utf-8')+b'\n');child.stdin.close()
                while child.poll() is None:
                    try:
                        tree=[process]+process.children(recursive=True);known=[identity(p) for p in tree]
                        rss=sum(p.memory_info().rss for p in tree if p.is_running());peak=max(peak,rss)
                        if rss>RSS_LIMIT:raise ValueError('任务进程树RSS超过1GiB')
                    except (psutil.NoSuchProcess,psutil.ZombieProcess):continue
                    except psutil.AccessDenied as exc:raise ValueError('无法建立完整任务树监督') from exc
                    used=temporary_bytes(root)
                    if used>TEMP_LIMIT:raise ValueError('任务临时文件超过256MiB')
                    if time.monotonic()-started>TIME_LIMIT:raise ValueError('任务总处理超过300秒')
                    with db.connect() as c:
                        active=c.execute('SELECT a.capture_id,s.latest_attempt,g.revision AS current_revision,a.config_revision FROM document_processing_attempts a JOIN document_snapshot_state s ON s.document_pk=(SELECT document_pk FROM document_captures WHERE id=a.capture_id) JOIN document_processing_config g ON g.singleton=1 WHERE a.id=?',(token,)).fetchone()
                        authorized=c.execute('SELECT 1 FROM document_capture_authorizations a JOIN document_sources s ON s.id=a.source_id AND s.revision=a.revision WHERE a.capture_id=? AND a.active=1',(active['capture_id'],)).fetchone() if active else None
                    if active is None or active['latest_attempt']!=token or active['config_revision']!=active['current_revision'] or authorized is None:raise ValueError('处理目标、配置或采集授权已失效')
                    state.update(peak_rss=peak,children=known);atomic_json(lease,state)
                    time.sleep(.05)
                if child.returncode:raise ValueError('原生解析失败: '+log.read_text(encoding='utf-8',errors='replace')[-2000:])
                state.update(status='completed',peak_rss=peak,seconds=time.monotonic()-started);atomic_json(root/'supervision.json',state)
                return Path(request['output']).read_bytes()
            except BaseException as exc:
                if child is not None:
                    try:stop_tree(stamp,token,known)
                    except UnboundLocalError:child.kill()
                state=locals().get('state',{});state.update(status='failed',error=str(exc),peak_rss=peak,seconds=time.monotonic()-started);atomic_json(root/'supervision.json',state)
                raise
            finally:
                if job:job.close()
                if child is not None:
                    if child.poll() is None:stop_tree(stamp,token,known)
                    child.wait(timeout=3)
                if watchdog is not None:
                    try:watchdog.wait(timeout=3)
                    except subprocess.TimeoutExpired:watchdog.kill();watchdog.wait(timeout=2)
                lease.unlink(missing_ok=True)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--watch':watch(sys.argv[2])
    else:raise SystemExit('supervisor is an internal task observer')

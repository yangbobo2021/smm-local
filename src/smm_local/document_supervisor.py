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


def module_command(module, *arguments):
    if sys.flags.no_site:
        # SCM registers the base interpreter before adding the protected Hub
        # environment's site directory. A new base interpreter does not inherit
        # that sys.path. Bootstrap only this installed package root explicitly;
        # -I excludes the task cwd, user site and PYTHONPATH from module lookup.
        installed = Path(__file__).resolve().parents[len(__package__.split('.'))]
        bootstrap = ('import runpy,site,sys; '
                     'site.addsitedir(sys.argv.pop(1)); '
                     'module=sys.argv.pop(1); '
                     'runpy.run_module(module,run_name="__main__",alter_sys=True)')
        return [sys.executable, '-I', '-S', '-B', '-c', bootstrap, str(installed), module, *arguments]
    return [sys.executable, '-B', '-m', module, *arguments]


def temporary_bytes(root):
    """Return a complete sample, retrying one transient child-path denial."""
    task = Path(os.path.abspath(root))
    for attempt in range(2):
        root.stat()  # Missing/inaccessible task roots always fail closed.
        try:
            return _temporary_bytes_once(root)
        except PermissionError as exc:
            if attempt or exc.filename is None:
                raise
            failed = Path(os.path.abspath(exc.filename))
            if failed == task:
                raise
            try:
                failed.relative_to(task)
            except ValueError:
                raise exc
            # A Windows delete-pending child can reject a cached traversal.
            # Discard the partial count and start one immediate complete scan.
            # Persistent denial still aborts; no sleep or whole-task retry.


def _temporary_bytes_once(root):
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
        if token is not None:
            try:command=process.cmdline()
            except psutil.AccessDenied:
                # A cmdline denial alone is not evidence of exit. Only an
                # independent, conclusive observation can retire this identity.
                try:
                    if not process.is_running() or process.status()==psutil.STATUS_ZOMBIE:return None
                except (psutil.NoSuchProcess,psutil.ZombieProcess):return None
                raise
            if token not in command:return None
        return process
    except (psutil.NoSuchProcess,psutil.ZombieProcess):return None


def stop_tree(stamp,token,known=(),*,owned=False,parent_exited=False):
    import psutil
    # The controller owns this Popen child and its creation-time identity.
    # Reading argv again during exit adds no ownership proof and can fail on
    # Darwin before the process is classified as a zombie.
    parent=None if parent_exited else matching(stamp,None if owned else token)
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
    _,alive=psutil.wait_procs(list(processes.values()),timeout=2)
    for process in alive:
        try:
            if process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:
                raise ValueError('任务进程树未能完全停止')
        except psutil.NoSuchProcess:pass


def cleanup_task(root,state):
    """Record proof only after the owned tree has stopped and payload is gone."""
    import shutil
    for path in root.iterdir():
        if path.name in {'supervision.json','worker.stdout','worker.stderr','watchdog.stderr','cleanup.json'}:continue
        if path.is_dir() and not path.is_symlink():shutil.rmtree(path)
        else:path.unlink(missing_ok=True)
    atomic_json(root/'cleanup.json',{'token':state['token'],'worker':state['worker'],'stopped':True})


def recover_abandoned_task(path,initial,known):
    root=Path(path).parent
    stop_tree(initial['worker'],initial['token'],known,owned=True)
    state={**initial,'status':'failed','error':'主控制进程已退出，已终止其文档处理任务'}
    atomic_json(root/'supervision.json',state)
    cleanup_task(root,state)
    # A newer task can already own the shared slot. Never remove its lease.
    try:
        with control_lock(root.parent/'processing.lock',timeout=0):
            lease=root.parent/'active.json'
            if lease.exists() and json.loads(lease.read_text()).get('token')==initial['token']:
                lease.unlink()
    except RuntimeError:pass


def recover_windows_task(root,state):
    """Finish an orphan only when the kernel proves its private Job closed."""
    from .document_windows import identity_exited
    proof=state.get('windows_job',{})
    if not proof.get('atomic') or not state.get('worker'):return False
    if not identity_exited(state['controller']['pid'],proof['controller_ticks']):return False
    if not identity_exited(state['worker']['pid'],proof['worker_ticks']):return False
    # No Job handle was inherited. Controller exit closes its sole handle;
    # KILL_ON_JOB_CLOSE terminates all members, including redirector children.
    # In-use deletion failures remain charged and retried by later admission.
    failed={**state,'status':'failed','error':'主控制进程已退出，其Windows Job已终止'}
    atomic_json(root/'supervision.json',failed)
    cleanup_task(root,failed)
    try:
        with control_lock(root.parent/'processing.lock',timeout=0):
            lease=root.parent/'active.json'
            if lease.exists() and json.loads(lease.read_text()).get('token')==state['token']:lease.unlink()
    except RuntimeError:pass
    return True


class WindowsJob:
    def __init__(self,child=None):
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
        if not kernel.SetInformationJobObject(handle,9,ctypes.byref(info),ctypes.sizeof(info)) or (child is not None and not kernel.AssignProcessToJobObject(handle,w.HANDLE(int(child._handle)))):
            code=ctypes.get_last_error();kernel.CloseHandle(handle);raise OSError(code,'无法将worker纳入Job Object')
        self.kernel=kernel;self.handle=handle
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None


class ExitSignal:
    """Positive kernel exit evidence, bound to a checked process identity."""
    def __init__(self,stamp):
        import select
        self.queue=None;self.fd=None;self.poller=None;self.done=False
        if matching(stamp) is None:
            self.done=True;return
        try:
            if sys.platform=='darwin':
                self.queue=select.kqueue()
                event=select.kevent(stamp['pid'],filter=select.KQ_FILTER_PROC,
                    flags=select.KQ_EV_ADD|select.KQ_EV_ONESHOT,fflags=select.KQ_NOTE_EXIT)
                self.queue.control([event],0,0)
            elif hasattr(os,'pidfd_open'):
                self.fd=os.pidfd_open(stamp['pid'])
                self.poller=select.poll();self.poller.register(self.fd,select.POLLIN)
            # Check again after registration: PID reuse cannot bind another
            # process's eventual exit to this worker identity.
            if matching(stamp) is None:self.done=True
        except ProcessLookupError:self.done=True
        except BaseException:
            self.close();raise

    def exited(self,timeout=0):
        if self.done:return True
        if self.queue is not None:
            import select
            events=self.queue.control(None,1,timeout)
            self.done=any(e.fflags & select.KQ_NOTE_EXIT for e in events)
        elif self.poller is not None:
            import select
            self.done=any(flags & select.POLLIN for _,flags in self.poller.poll(int(timeout*1000)))
        return self.done

    def close(self):
        if self.queue is not None:self.queue.close();self.queue=None
        if self.fd is not None:os.close(self.fd);self.fd=None


def watch(path):
    import psutil
    initial=json.loads(Path(path).read_text());known=[]
    exited=ExitSignal(initial['worker'])
    try:
        while True:
            controller=matching(initial['controller'])
            if controller is None:
                recover_abandoned_task(path,initial,known);return
            try:worker=matching(initial['worker'],initial['token'])
            except psutil.AccessDenied:
                # Darwin can reject argv while an owned process is exiting.
                # A denial is never exit proof; only the registered kernel
                # event allows us to skip querying that dying root again.
                if not exited.exited(.1):raise
                stop_tree(initial['worker'],initial['token'],known,parent_exited=True);return
            if worker:
                try:known=[identity(p) for p in worker.children(recursive=True)]
                except psutil.NoSuchProcess:pass
            if worker is None:
                stop_tree(initial['worker'],initial['token'],known,parent_exited=True);return
            time.sleep(.05)
    finally:exited.close()


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
        child=None;stamp=None;job=None;watchdog=None;known=[];peak=0;started=time.monotonic()
        with log.open('wb') as errors,stdout.open('wb') as output,(root/'watchdog.stderr').open('wb') as watch_errors:
            try:
                # Invalidate old proof before any new worker can be spawned
                # for a resumed attempt with the same task token.
                (root/'cleanup.json').unlink(missing_ok=True)
                preparing={'token':token,'worker':None,'controller':identity(psutil.Process()),'children':[],
                    'status':'preparing','gate_open':False}
                atomic_json(root/'supervision.json',preparing)
                command=module_command(__package__+'.document_worker','--task-token',token)
                if os.name=='nt':
                    from .document_windows import spawn,creation_ticks,kernel
                    job=WindowsJob()
                    child=spawn(job,command,stdout=output,stderr=errors,cwd=root)
                else:child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=output,stderr=errors,cwd=root,start_new_session=True)
                process=psutil.Process(child.pid);stamp=identity(process)
                state={'token':token,'worker':stamp,'controller':identity(psutil.Process()),'children':[],'status':'processing','rss_limit':RSS_LIMIT,'temp_limit':TEMP_LIMIT,'seconds_limit':TIME_LIMIT}
                state['gate_open']=False
                if os.name=='nt':
                    state['windows_job']={'atomic':True,'controller_ticks':creation_ticks(kernel().GetCurrentProcess()),
                        'worker_ticks':creation_ticks(child._handle)}
                atomic_json(lease,state);atomic_json(root/'supervision.json',state)
                if os.name!='nt':
                    watchdog=subprocess.Popen(module_command(__package__+'.document_supervisor','--watch',str(root/'supervision.json')),stdin=subprocess.DEVNULL,stdout=output,stderr=watch_errors,cwd=root,start_new_session=True)
                state['gate_open']=True;atomic_json(root/'supervision.json',state)
                # Optional parser imports are unreachable before this gate.
                child.stdin.write(json.dumps(request).encode('utf-8')+b'\n');child.stdin.close()
                while child.poll() is None:
                    if watchdog is not None and watchdog.poll() is not None:
                        # Exit 0 is also unexpected while the worker is live.
                        # The owned Popen handle supplies conclusive exit proof
                        # across one observation interval, without querying a
                        # dying process's argv or interpreting AccessDenied.
                        try:child.wait(timeout=.05)
                        except subprocess.TimeoutExpired:
                            raise ValueError('独立监督程序已退出，文档处理已终止（退出码 '+str(watchdog.returncode)+'）')
                        break
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
                cleanup_error=None
                if child is not None:
                    try:
                        if stamp is not None:stop_tree(stamp,token,known,owned=True)
                        elif child.poll() is None:child.kill()
                    except Exception as cleanup:cleanup_error=str(cleanup)
                state=locals().get('state',locals().get('preparing',{'token':token,'worker':stamp}));state.update(status='failed',error=str(exc),peak_rss=peak,seconds=time.monotonic()-started)
                if cleanup_error:state['cleanup_error']=cleanup_error
                atomic_json(root/'supervision.json',state)
                raise
            finally:
                if job:job.close()
                if child is not None:
                    if child.poll() is None:
                        if stamp is not None:stop_tree(stamp,token,known,owned=True)
                        else:child.kill()
                    child.wait(timeout=3)
                    if os.name=='nt':child.close()
                    if stamp is not None:stop_tree(stamp,token,known,owned=True)
                if watchdog is not None:
                    try:watchdog.wait(timeout=3)
                    except subprocess.TimeoutExpired:watchdog.kill();watchdog.wait(timeout=2)
                lease.unlink(missing_ok=True)
                if stamp is not None or child is None:cleanup_task(root,state)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--watch':watch(sys.argv[2])
    else:raise SystemExit('supervisor is an internal task observer')

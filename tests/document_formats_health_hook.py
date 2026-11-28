"""Task-owned, real-process gates; never replace product results or budgets."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time


DESCENDANT = '''import json,os,sys,time
from pathlib import Path
import psutil
ready=Path(sys.argv[1]);control=Path(sys.argv[2]);token=sys.argv[3];nonce=sys.argv[4]
assert sys.stdin.buffer.read(1)==b''
p=psutil.Process()
value={'token':token,'nonce':nonce,'stdin_eof_observed':True,'pid':p.pid,'created':p.create_time(),
       'argv':p.cmdline(),'exe':p.exe(),'cwd':p.cwd(),'parent_pid':p.ppid()}
temporary=ready.with_suffix('.new');temporary.write_text(json.dumps(value),encoding='utf-8');temporary.replace(ready)
from document_formats_health_hook import preparation_progress
step=-1;deadline=time.monotonic()+60
while not (control/('helper-release-'+token)).exists() and not (control/'release-all').exists():
    step,deadline=preparation_progress(control,token,nonce,step,deadline,60)
    assert time.monotonic()<deadline,'test descendant gate deadline exceeded'
    time.sleep(.005)
'''


def write(path, value):
    temporary=path.with_name(path.name+'.'+str(os.getpid())+'.new')
    temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    temporary.replace(path)


def preparation_progress(control,token,nonce,step,deadline,seconds):
    # Only explicit parent progress between complete preparation checks renews
    # the fixture's idle gate. Production task budgets remain authoritative.
    path=control/('preparing-'+token+'.json')
    try:value=json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:return step,deadline
    assert value['token']==token and value['nonce']==nonce
    current=value['step']
    assert type(current) is int and current>=step
    return (current,time.monotonic()+seconds) if current>step else (step,deadline)


def install():
    value=os.environ.get('SMM_008_HEALTH_CONTROL')
    if not value:return
    import psutil
    control=Path(value);arguments=sys.orig_argv
    def identity(process):
        return {'pid':process.pid,'created':process.create_time(),
                'argv':process.cmdline(),'exe':process.exe(),'cwd':process.cwd()}
    if 'document_formats_restart_server' in arguments:
        original=subprocess.Popen.wait
        def waited(child,*args,**kwargs):
            try:return original(child,*args,**kwargs)
            finally:
                argv=child.args
                if (child.returncode is not None and isinstance(argv,(list,tuple))
                        and '--watch' in argv and any(str(a).endswith('.document_supervisor') for a in argv)):
                    path=Path(argv[argv.index('--watch')+1]);state=json.loads(path.read_text(encoding='utf-8'))
                    write(control/('watch-exit-'+state['token']+'.json'),
                          {'pid':child.pid,'argv':list(argv),'actual_returncode':child.returncode,'at':time.monotonic()})
        subprocess.Popen.wait=waited
        return
    arm=control/'arm.json'
    if not arm.exists():return
    setup=json.loads(arm.read_text(encoding='utf-8'))
    if '--task-token' in arguments:
        token=arguments[arguments.index('--task-token')+1]
        if not any(str(a).endswith('.document_worker') for a in arguments):return
        directory=Path.cwd();child=None
        try:
            ready=control/('descendant-started-'+token+'.json')
            argv=[sys.executable,'-B','-c',DESCENDANT,str(ready),str(control),token,setup['nonce']]
            child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            bootstrap={'pid':child.pid,'created':psutil.Process(child.pid).create_time()}
            deadline=time.monotonic()+5
            while not ready.exists():
                assert child.poll() is None and time.monotonic()<deadline
                time.sleep(.005)
            handshake=json.loads(ready.read_text(encoding='utf-8'))
            assert handshake['pid']==bootstrap['pid'] and handshake['created']==bootstrap['created']
            assert handshake['token']==token and handshake['nonce']==setup['nonce'] and handshake['stdin_eof_observed']
            descendant=psutil.Process(handshake['pid']);final=identity(descendant)
            assert {k:handshake[k] for k in final}==final and final['argv'][1:]==argv[1:]
            payload=directory/'health-temporary-payload.bin';payload.write_bytes(b'owned temporary processing payload 008')
            write(control/('worker-ready-'+token+'.json'),{'token':token,'nonce':setup['nonce'],
                  'worker':identity(psutil.Process()),'descendant':final,'descendant_handshake':handshake,
                  'descendant_requested_argv':argv,'descendant_bootstrap':bootstrap,
                  'directory':str(directory),'payload':str(payload)})
            step=-1;deadline=time.monotonic()+30
            while not (control/('release-'+token)).exists() and not (control/'release-all').exists():
                step,deadline=preparation_progress(control,token,setup['nonce'],step,deadline,30)
                if time.monotonic()>=deadline:
                    write(control/('gate-timeout-'+token+'.json'),{'token':token,'at':time.monotonic()})
                    raise RuntimeError('test preparation gate deadline exceeded')
                time.sleep(.005)
        finally:
            if child is not None:
                (control/('helper-release-'+token)).touch()
                child.wait(timeout=3)
        return
    if '--watch' not in arguments or not any(str(a).endswith('.document_supervisor') for a in arguments):return
    path=Path(arguments[arguments.index('--watch')+1]);state=json.loads(path.read_text(encoding='utf-8'));token=state['token']
    original=psutil.Process.cmdline
    watcher=identity(psutil.Process())
    def observed(process):
        result=original(process)
        if process.pid!=state['worker']['pid']:return result
        created=process.create_time()
        if created!=state['worker']['created'] or token not in result:
            # The real reader can return an empty argv during normal exit.
            # Observation must preserve that result, not invent a fault.
            write(control/('watch-transition-'+token+'.json'),
                  {'pid':process.pid,'created':created,'expected_created':state['worker']['created'],'argv':result})
            return result
        try:
            live={'token':token,'nonce':setup['nonce'],'watcher':watcher,
                  'worker':{'pid':process.pid,'created':created,'argv':result,
                            'exe':process.exe(),'cwd':process.cwd()},'status':process.status()}
        except (psutil.NoSuchProcess,psutil.ZombieProcess,psutil.AccessDenied):
            # Extra metadata is for the test's enrollment only; its absence
            # must not turn a successful cmdline read into a product error.
            return result
        command=control/('fault-'+token+'.json')
        if not command.exists():
            write(control/('watch-live-'+token+'.json'),live)
            return result
        request=json.loads(command.read_text(encoding='utf-8'))
        assert request['token']==token and request['nonce']==setup['nonce']
        assert observed(psutil.Process())==original(psutil.Process())
        live.update(mode=request['mode'],non_target_original_unchanged=True,at=time.monotonic())
        write(control/('fault-observed-'+token+'.json'),live)
        if request['mode']=='denial':raise psutil.AccessDenied(process.pid)
        assert request['mode']=='exit0'
        os._exit(0)
    psutil.Process.cmdline=observed

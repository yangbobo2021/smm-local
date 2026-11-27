"""Isolated CLI-handoff observer; leaves retained restart audits unchanged."""
import json
import os
from pathlib import Path
import sys


def arguments(value):
    if isinstance(value,(list,tuple)):return list(value)
    if not isinstance(value,str):raise TypeError('unsupported process argv')
    if os.name!='nt':raise TypeError('unexpected POSIX process argv string')
    import ctypes as c
    from ctypes import wintypes as w
    shell=c.WinDLL('shell32',use_last_error=True);kernel=c.WinDLL('kernel32',use_last_error=True)
    shell.CommandLineToArgvW.argtypes=[w.LPCWSTR,c.POINTER(c.c_int)];shell.CommandLineToArgvW.restype=c.POINTER(w.LPWSTR)
    kernel.LocalFree.argtypes=[c.c_void_p];kernel.LocalFree.restype=c.c_void_p
    count=c.c_int();pointer=shell.CommandLineToArgvW(value,c.byref(count))
    if not pointer:raise c.WinError(c.get_last_error())
    try:return [pointer[i] for i in range(count.value)]
    finally:kernel.LocalFree(pointer)


def worker_token(argv):
    if len(argv)<6 or argv[1:3]!=['-B','-m'] or argv[3] not in {'smm_local.document_worker','smm_hub._archive.document_worker'} or argv[4]!='--task-token':return None
    token=argv[5]
    return token if len(token)==32 and all(c in '0123456789abcdef' for c in token) else None


def install():
    log=os.environ.get('SMM_008_HANDOFF_AUDIT')
    if not log:return
    import psutil,subprocess
    own=psutil.Process();nonce=os.environ['SMM_008_HANDOFF_NONCE']
    identity={'pid':os.getpid(),'created':own.create_time(),'exe':own.exe(),
        'parent_argv':own.cmdline(),'cwd':own.cwd(),'nonce':nonce}
    def record(value):
        with open(log,'a',encoding='utf-8') as stream:stream.write(json.dumps({**identity,**value},ensure_ascii=False)+'\n')
    observed=[]
    def audit(event,args):
        if event=='smm.handoff.observer_probe':
            assert args[0]==nonce and arguments(args[1])==list(args[2])
            assert worker_token(arguments(args[1]))=='f'*32
            observed.append(True);record({'event':'handoff-observer-control','raw_type':type(args[1]).__name__})
            return
        if event!='subprocess.Popen':return
        argv=arguments(args[1]);token=worker_token(argv)
        if token is None:return
        record({'event':event,'argv':argv,'raw_argv':args[1],'raw_type':type(args[1]).__name__,'task_token':token})
    sys.addaudithook(audit)
    expected=[sys.executable,'-B','-m','smm_local.document_worker','--task-token','f'*32,'带 空格','','C:\\空 格\\tail\\','quote "value"']
    assert arguments(expected)==expected
    value=subprocess.list2cmdline(expected) if os.name=='nt' else expected
    sys.audit('smm.handoff.observer_probe',nonce,value,tuple(expected))
    assert observed==[True]
    record({'event':'handoff-observer-installed','argv':identity['parent_argv'],'probe_passed':True})


def controls(root):
    import subprocess
    import psutil
    from document_helpers import ROOT,observe
    from document_formats_platform import spawn_identity,process_tree,terminate_verified,same_existing_path,utf8_environment
    from uuid import uuid4
    root.mkdir();hooks=root/'带 空格';hooks.mkdir()
    (hooks/'sitecustomize.py').write_text('from document_formats_handoff_observer import install\ninstall()\n',encoding='utf-8')
    log=root/'probe.jsonl'
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_HANDOFF_AUDIT=str(log),SMM_008_HANDOFF_NONCE=uuid4().hex)
    token='a'*32
    tail=['带 空格', '', 'quoted "argument"', 'C:\\space dir\\tail\\']
    positive=[sys.executable,'-B','-m','smm_local.document_worker','--task-token',token,*tail]
    negative=[sys.executable,'-B','-c','pass','literal.document_worker',*tail,'-m','smm_local.document_worker','--task-token',token]
    fake=[sys.executable,'-B','-m','fake.document_worker','--task-token',token]
    nonworker=[sys.executable,'-B','-m','smm_local.document_supervisor']
    code='''import json,sys,subprocess,psutil,os
p=psutil.Process()
print(json.dumps({'pid':os.getpid(),'created':p.create_time(),'exe':p.exe(),'argv':p.cmdline()}),flush=True)
sys.stdin.buffer.read(1)
commands=json.loads(sys.argv[1]);codes=[]
sys.audit('smm.handoff.unrelated',commands)
for command in commands:
 q=subprocess.run(command,input=b'',capture_output=True,timeout=10);codes.append(q.returncode)
print(json.dumps({'codes':codes}),flush=True)
'''
    child=subprocess.Popen([sys.executable,'-B','-c',code,json.dumps([positive,negative,fake,nonworker],ensure_ascii=False)],env=env,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    bootstrap=spawn_identity(psutil.Process(child.pid));members=[]
    try:
        live=json.loads(child.stdout.readline())
        members=process_tree(bootstrap)
        actual=[r for r in members if r['pid']==live['pid'] and r['created']==live['created']]
        assert len(actual)==1 and same_existing_path(actual[0]['exe'],live['exe']) and actual[0]['argv']==live['argv']
        output,error=child.communicate(b'x',timeout=25)
        assert child.returncode==0,error.decode('utf-8',errors='replace')
        assert json.loads(output)['codes']==[2,0,1,1]
        rows=[json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
        installed=[e for e in rows if e['event']=='handoff-observer-installed']
        assert any(e['pid']==live['pid'] and e['created']==live['created'] and e['argv']==live['argv'] for e in installed)
        events=[e for e in rows if e['event']=='subprocess.Popen']
        assert len(events)==1 and events[0]['argv']==positive
        assert events[0]['pid']==live['pid'] and events[0]['created']==live['created']
        assert same_existing_path(events[0]['exe'],live['exe'])
        assert events[0]['raw_type']==('str' if os.name=='nt' else 'list')
        observe('handoff-observer-controls',{'identity':actual[0],'positive':positive,'negative':negative,
            'exit_codes':[2,0,1,1],'fake_module':fake,'nonworker':nonworker,'events':events,'stderr':error.decode('utf-8',errors='replace')})
    finally:
        terminate_verified(members or process_tree(bootstrap),owner=child)
        if child.poll() is None:child.kill()
        child.wait(timeout=5)

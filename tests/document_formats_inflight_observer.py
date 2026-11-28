"""Pause only explicit CLI reprocessing before its real supervised task."""
import json
import os
from pathlib import Path

HOOK = r'''
import json,os,sys,time
import psutil
from pathlib import Path
protected={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_INFLIGHT_SOURCES'])}
def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes)) and os.path.normcase(os.path.abspath(os.fsdecode(args[0]))) in protected:
        with open(os.environ['SMM_008_INFLIGHT_READS'],'a',encoding='utf-8') as out:out.write(json.dumps({'kind':'source-open','path':os.fsdecode(args[0]),'pid':os.getpid()})+chr(10))
        raise AssertionError('inflight source must not reopen')
sys.addaudithook(audit)
from smm_local import document_supervisor
original=document_supervisor.run
def paused(db,request,task_directory):
    signal=Path(os.environ['SMM_008_INFLIGHT_ENTERED'])
    temporary=signal.with_suffix('.pending')
    actor=psutil.Process()
    temporary.write_text(json.dumps({'task_token':request['task_token'],'raw_sha256':request['raw_sha256'],'raw':request['raw'],'format':request['format'],'pid':actor.pid,'created':actor.create_time(),'argv':actor.cmdline(),'exe':actor.exe()}),encoding='utf-8')
    os.replace(temporary,signal)
    release=Path(os.environ['SMM_008_INFLIGHT_RELEASE']);deadline=time.monotonic()+30
    while not release.exists():
        if time.monotonic()>deadline:raise AssertionError('inflight test barrier was not released')
        time.sleep(.01)
    return original(db,request,task_directory)
document_supervisor.run=paused
'''


def install(root, sources):
    root.mkdir(parents=True, exist_ok=False)
    (root/'sitecustomize.py').write_text(HOOK,encoding='utf-8')
    entered=root/'entered.json';release=root/'release';reads=root/'source-reads.jsonl'
    env=dict(os.environ,SMM_008_INFLIGHT_SOURCES=json.dumps(list(map(str,sources))),SMM_008_INFLIGHT_READS=str(reads),SMM_008_INFLIGHT_ENTERED=str(entered),SMM_008_INFLIGHT_RELEASE=str(release),PYTHONPATH=str(root)+os.pathsep+os.environ.get('PYTHONPATH',''))
    return env,entered,release,reads

"""Actual child raw-file read barrier; test observation only, no result/status mocking."""
import json,os
from pathlib import Path

HOOK=r'''import json,os,sys,time
from pathlib import Path
root=Path(os.environ['SMM_008_REFRESH_GATE'])
protected={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_REFRESH_RAW_PATHS'])}
def observe_open(event,args):
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    if '--task-token' not in sys.argv:return
    path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
    if path not in protected:return
    digest=Path(path).name;token=sys.argv[sys.argv.index('--task-token')+1]
    entry=root/(digest+'.json')
    if not entry.exists():
        entry.write_text(json.dumps({'path':path,'sha256':digest,'token':token,'pid':os.getpid(),'ppid':os.getppid(),'argv':sys.argv,'executable':sys.executable,'uid':os.getuid(),'entered_at':time.time()}),encoding='utf-8')
    until=time.monotonic()+90
    while not (root/(digest+'.release')).exists() and not (root/'abort').exists():
        if time.monotonic()>until:raise RuntimeError('test raw gate release deadline exceeded')
        time.sleep(.01)
sys.addaudithook(observe_open)
'''


def prepare_gate(root,paths):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    hooks=root/'hooks';hooks.mkdir();(hooks/'sitecustomize.py').write_text(HOOK,encoding='utf-8')
    env=dict(os.environ,SMM_008_REFRESH_GATE=str(root),SMM_008_REFRESH_RAW_PATHS=json.dumps(list(map(str,paths))))
    env['PYTHONPATH']=str(hooks)+os.pathsep+os.environ.get('PYTHONPATH','')
    return env

"""Task-only raw-read barrier and original-source denial; no parser/result mocks."""
import json,os,sys,time
from pathlib import Path


def install():
    root=Path(os.environ['SMM_008_ACTIVE_GATE'])
    raw={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_ACTIVE_RAW'])}
    sources={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_ACTIVE_SOURCES'])}
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path in sources and (root/'deny-sources').exists():
            with (root/'source-opens.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps({'path':path,'pid':os.getpid()})+'\n')
            raise AssertionError('active source must not reopen')
        if path not in raw or '--task-token' not in sys.argv:return
        armed=root/'armed'
        if not armed.exists() or armed.read_text(encoding='utf-8')!=Path(path).name:return
        token=sys.argv[sys.argv.index('--task-token')+1];entry=root/(token+'.json')
        if not entry.exists():
            import psutil
            process=psutil.Process()
            entry.write_text(json.dumps({'path':path,'sha256':Path(path).name,'token':token,'pid':os.getpid(),'ppid':os.getppid(),'created':process.create_time(),'argv':process.cmdline(),'exe':process.exe(),'entered_at':time.time()},ensure_ascii=False),encoding='utf-8')
        until=time.monotonic()+60
        while not (root/(token+'.release')).exists() and not (root/'abort').exists():
            if time.monotonic()>until:raise RuntimeError('active raw gate release deadline')
            time.sleep(.01)
    sys.addaudithook(audit)

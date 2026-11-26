"""Task-only gate AFTER real processing, before the caller publishes its result."""
import hashlib,json,os,sys,time
from pathlib import Path


def install():
    if '--task-token' in sys.argv or '--watch' in sys.argv:return
    from smm_local.document_snapshots import Snapshots
    original=Snapshots.process
    root=Path(os.environ['SMM_008_PUBLICATION_GATE'])
    def gated(self,token,format):
        result=original(self,token,format)
        armed=root/'armed'
        if not armed.exists() or armed.read_text(encoding='utf-8')!=token['raw_sha256']:return result
        import psutil
        raw=self.blob('results',token['result_sha256']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==token['result_sha256']
        value={'pid':os.getpid(),'created':psutil.Process().create_time(),'argv':psutil.Process().cmdline(),'capture_id':token['capture_id'],'attempt_id':token['attempt_id'],'raw_sha256':token['raw_sha256'],'result_sha256':token['result_sha256'],'result_status':result['status'],'config_revision':token['config']['revision'],'profile':result['profile'],'entered_at':time.time()}
        path=root/(token['attempt_id']+'.json');temporary=path.with_suffix('.pending');temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temporary.replace(path)
        until=time.monotonic()+60
        while not (root/(token['attempt_id']+'.release')).exists() and not (root/'abort').exists():
            if time.monotonic()>until:raise RuntimeError('postprocessing publication gate deadline')
            time.sleep(.01)
        return result
    Snapshots.process=gated

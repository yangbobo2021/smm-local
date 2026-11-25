"""Explicit isolated HTTP factory and child audit for development restart tests."""
import json,os,sys,time
from pathlib import Path


def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        value=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        blocked={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ.get('SMM_008_RESTART_DENY','[]'))}
        if value in blocked:
            with open(os.environ['SMM_008_RESTART_AUDIT'],'a',encoding='utf-8') as out:out.write(json.dumps({'event':event,'path':value,'pid':os.getpid()})+'\n')
            raise RuntimeError('restart source read denied')
    if event=='subprocess.Popen' and (log:=os.environ.get('SMM_008_WEB_READ_ONLY')):
        with open(log,'a',encoding='utf-8') as out:out.write(json.dumps({'event':'subprocess','pid':os.getpid()})+'\n')
        raise AssertionError('read-only browser phase attempted subprocess')
    if event=='subprocess.Popen' and isinstance(args[1],(list,tuple)) and any('.document_worker' in str(x) for x in args[1]):
        with open(os.environ['SMM_008_RESTART_AUDIT'],'a',encoding='utf-8') as out:out.write(json.dumps({'event':event,'pid':os.getpid(),'argv':list(args[1])})+'\n')


def install_audit():sys.addaudithook(audit)


def make_app():
    from smm_local.core import Archive
    path=Path(os.environ['SMM_008_TEST_DB']);assert path.is_absolute()
    db=Archive(path);empty=path.parent/'empty-agent';empty.mkdir(exist_ok=True)
    db.set_settings(codex_root=str(empty),claude_root=str(empty))
    if gate:=os.environ.get('SMM_008_WEB_PROCESSING_GATE'):
        from smm_local.managed_document_uploads import ManagedDocumentUploads
        original=ManagedDocumentUploads.run_pending
        def gated(self,*args,**kwargs):
            def event(kind):
                with open(gate+'.events','a',encoding='utf-8') as out:out.write(json.dumps({'event':kind,'pid':os.getpid()})+'\n')
            event('enter')
            while not Path(gate).exists():time.sleep(.02)
            try:return original(self,*args,**kwargs)
            finally:event('exit')
        ManagedDocumentUploads.run_pending=gated
    if pause:=os.environ.get('SMM_008_RESTART_PAUSE'):
        from smm_local.managed_document_uploads import ManagedDocumentUploads
        original=ManagedDocumentUploads.run_pending
        def blocked(self,*args,**kwargs):
            with self.db.connect() as c:jobs=[dict(r) for r in c.execute('SELECT document_id,state FROM document_upload_jobs ORDER BY document_id')]
            with open(pause,'a',encoding='utf-8') as out:out.write(json.dumps({'pid':os.getpid(),'jobs':jobs})+'\n')
            while True:time.sleep(.05)
            return original(self,*args,**kwargs)
        ManagedDocumentUploads.run_pending=blocked
    if os.environ['SMM_008_TEST_OWNER']=='local':
        from smm_local.api import create_app
        app=create_app(db,auto_sync=False,sync_on_start=False)
    else:
        from smm_hub.hub import create_hub
        app=create_hub(db,os.environ['SMM_008_TEST_TOKEN'])
    if readonly:=os.environ.get('SMM_008_WEB_READ_ONLY'):
        from smm_local.document_snapshots import Snapshots
        from smm_local import document_processing
        def denied(*args,**kwargs):
            with open(readonly,'a',encoding='utf-8') as out:out.write(json.dumps({'event':'processing','pid':os.getpid()})+'\n')
            raise AssertionError('read-only browser phase attempted processing')
        Snapshots.process=denied;document_processing.process=denied
        @app.post('/__test_processing_probe')
        def processing_probe():
            import subprocess
            blocked=[]
            try:Snapshots.process(None,None,'docx')
            except AssertionError:blocked.append('processing')
            try:child=subprocess.Popen([sys.executable,'-c','raise SystemExit(19)']);child.wait(timeout=5)
            except AssertionError:blocked.append('subprocess')
            return {'blocked':blocked,'pid':os.getpid()}
    @app.get('/__test_identity')
    def actual_identity():return {'pid':os.getpid(),'archive':str(db.db_path.resolve()),'owner':os.environ['SMM_008_TEST_OWNER']}
    return app

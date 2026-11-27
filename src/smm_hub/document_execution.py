"""Same-archive CLI handoff to a live Hub's saved-byte processor."""
from contextlib import contextmanager
import json
import threading
import time

from ._archive import atomic_json, control_lock, digest


class ProcessingService:
    def __init__(self,hub):
        self.hub=hub;self.db=hub.db;self.snapshots=hub.documents.snapshots
        self.native=self.snapshots.process
        key=digest(str(self.db.db_path.resolve()))
        directory=self.snapshots._directory('services')
        self.lock=directory/('hub-processing-'+key+'.lock')
        self.status_file=directory/('hub-processing-'+key+'.json')
        self.stop=threading.Event()
        with self.db.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS hub_document_processing_jobs(
                attempt_id TEXT PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL,
                result_sha256 TEXT,error TEXT)''')

    def _active(self):
        acquired=False
        try:
            with control_lock(self.lock,timeout=0):acquired=True
        except RuntimeError:
            if acquired:raise
            state=json.loads(self.status_file.read_text(encoding='utf-8'))
            if state.get('archive')!=str(self.db.db_path.resolve()) or state.get('status')!='running':
                raise ValueError('同档案Hub文档处理服务不可用，请查看服务诊断')
            return True
        return False

    def process(self,token,format):
        # A continuous overlapping source can reuse the already published
        # snapshot. It must not enqueue that old attempt with a new payload.
        if token.get('reused'):return self.snapshots.load_result(token['result_sha256'])
        if not self._active():return self.native(token,format)
        context=self.hub.context()
        payload=json.dumps({'context':context,'token':token,'format':format},sort_keys=True)
        with self.hub.guard.hold(),self.db.connect() as c:
            self.hub._context(context)
            old=c.execute('SELECT payload FROM hub_document_processing_jobs WHERE attempt_id=?',(token['attempt_id'],)).fetchone()
            if old and old['payload']!=payload:raise ValueError('处理尝试的服务交接目标已改变')
            c.execute("INSERT OR IGNORE INTO hub_document_processing_jobs VALUES(?,?,'pending',NULL,NULL)",(token['attempt_id'],payload))
        while True:
            with self.db.connect() as c:
                job=c.execute('SELECT * FROM hub_document_processing_jobs WHERE attempt_id=?',(token['attempt_id'],)).fetchone()
            if job is None:raise ValueError('Hub文档处理交接已失效')
            if job['state']=='failed':raise ValueError(job['error'])
            if job['state']=='done':
                token['result_sha256']=job['result_sha256']
                return self.snapshots.load_result(job['result_sha256'])
            if not self._active():raise ValueError('Hub文档处理服务已停止；已保存原件，请查看当前状态后重试')
            time.sleep(.05)

    def _one(self):
        acquired=False
        try:
            with control_lock(self.snapshots.root/'upload-queue.lock',timeout=0):
                acquired=True
                with self.db.connect() as c:
                    row=c.execute("SELECT * FROM hub_document_processing_jobs WHERE state='pending' ORDER BY rowid LIMIT 1").fetchone()
                if row is None:return
                value=json.loads(row['payload']);token=value['token'];error=None
                try:
                    with self.hub.guard.hold():self.hub._context(value['context'])
                    with self.db.connect() as c:
                        attempt=c.execute('SELECT * FROM document_processing_attempts WHERE id=?',(token['attempt_id'],)).fetchone()
                        current=c.execute('SELECT current_capture,latest_attempt FROM document_snapshot_state WHERE document_pk=?',(token['document_pk'],)).fetchone()
                        if (current is None or current['current_capture']!=token['capture_id']
                                or current['latest_attempt']!=token['attempt_id'] or not self.snapshots.authorized(c,token['capture_id'])):
                            raise ValueError('交接的原件或处理尝试已失效')
                    if attempt and attempt['result_sha256'] and attempt['state'] in {'ready','partial','empty-success'}:
                        token['result_sha256']=attempt['result_sha256']
                    else:self.native(token,value['format'])
                except Exception as exc:
                    error=str(exc)
                    # Pre-processing rejection must finish this exact pending
                    # attempt too. A stale Hub context cannot mutate its heir.
                    with self.hub.guard.hold():
                        try:self.hub._context(value['context'])
                        except (OSError,ValueError,RuntimeError):pass
                        else:self.snapshots.fail_current(token,error)
                try:
                    with self.hub.guard.hold():self.hub._context(value['context'])
                except (OSError,ValueError,RuntimeError) as exc:error=str(exc)
                # Retire only this exact operational ticket after a context
                # change; never publish or rewrite the new context's content.
                with self.db.connect() as c:
                    c.execute('UPDATE hub_document_processing_jobs SET state=?,result_sha256=?,error=? WHERE attempt_id=? AND payload=?',
                        ('failed' if error else 'done',token.get('result_sha256'),error,token['attempt_id'],row['payload']))
        except RuntimeError:
            if acquired:raise

    def _run(self):
        try:
            self.hub.managed_uploads.run_pending()
            while not self.stop.is_set():
                self._one()
                self.stop.wait(.05)
        except BaseException as exc:
            atomic_json(self.status_file,{'archive':str(self.db.db_path.resolve()),'status':'failed','error':str(exc)})

    def _coordinate(self,ready):
        # Multiple HTTP lifespans may share one archive during restart. Each
        # frontend waits for the same kernel lease; exactly one consumes jobs.
        while not self.stop.is_set():
            acquired=False
            try:
                with control_lock(self.lock,timeout=.1):
                    acquired=True
                    if self.stop.is_set():return
                    atomic_json(self.status_file,{'archive':str(self.db.db_path.resolve()),'status':'running'})
                    ready.set()
                    self._run()
                    # A failed processor keeps ownership until this frontend
                    # stops. Never silently move work into an interactive CLI.
                    self.stop.wait()
                    atomic_json(self.status_file,{'archive':str(self.db.db_path.resolve()),'status':'stopped'})
                    return
            except RuntimeError:
                if acquired:raise
                ready.set()  # An existing frontend owns the real processor.
        ready.set()

    @contextmanager
    def serve(self):
        ready=threading.Event()
        worker=threading.Thread(target=self._coordinate,args=(ready,),name='smm-hub-document-processor',daemon=True)
        worker.start()
        if not ready.wait(5):
            self.stop.set();raise ValueError('Hub文档处理服务启动失败，请查看服务诊断')
        try:yield
        finally:
            self.stop.set();worker.join(timeout=2)

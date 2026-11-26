"""Creator-owned resumable raw uploads and saved-byte processing jobs.

The device projection receiver never calls this module. Parsing happens only
from the saved raw snapshot, after the upload response, outside control/DB locks.
"""
from __future__ import annotations
from contextlib import nullcontext
import json
import os
from pathlib import Path
from uuid import uuid4
from .archive_protocol import control_lock,digest
from .core import utcnow
from .document_protocol import integer,identity
from .document_results import sha
from .document_snapshots import RAW_LIMIT
from .document_transfers import BlobTransfers,BLOCK_LIMIT
from .managed_documents import display_name
from .documents import _link


class ManagedDocumentUploads:
    def __init__(self,library,*,guard=None,context_check=None,project_check=None):
        self.library=library;self.db=library.db;self.documents=library.documents
        self.snapshots=self.documents.snapshots;self.guard=guard
        self.context_check=context_check;self.project_check=project_check
        self.transfers=BlobTransfers(self.snapshots,raw_only=True)
        with self.db.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS document_upload_jobs(document_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL,error TEXT)')
    def _hold(self):return self.guard.hold() if self.guard is not None else nullcontext()
    def _check(self,binding):
        if self.context_check:self.context_check(binding)
        if self.project_check:self.project_check(binding['project_id'],binding['project_key'])
        with self.db.connect() as c:
            self.documents._projects(c,[binding['project_id']])
            if self.project_check is None:self.library._project_key(c,binding['project_id'],binding['project_key'])
    def _target(self,c,binding):
        if 'document_id' not in binding:return None
        identity(binding['document_id'],'文档ID')
        for key in ('capture_id','expected_attempt_id'):
            if key in binding:identity(binding[key],key)
        row=self.library._receipt(c,binding['document_id'])
        if binding['project_id'] not in row['project_ids']:raise ValueError('资料不属于所显示项目')
        latest=row.get('latest_attempt') or {};published=row.get('published_snapshot') or {}
        wanted={'expected_version':row['version'],'expected_processing_version':row['processing_version'],'expected_revision':row['source_revision']}
        if any(type(binding.get(k)) is not int or binding[k]!=v for k,v in wanted.items()):raise ValueError('资料内容、处理或来源版本已改变，请重新查看')
        # A failed/unpublished candidate must be compared independently from
        # the still-readable published V/P. A normal published update may also
        # submit CID/AID to protect the exact state it displayed.
        pair={'capture_id':latest.get('capture_id'),'expected_attempt_id':latest.get('attempt_id')}
        if set(pair).intersection(binding) or latest.get('capture_id')!=published.get('capture_id'):
            if any(not v or binding.get(k)!=v for k,v in pair.items()):raise ValueError('捕获或最近处理尝试已改变，请重新查看')
        if not latest.get('capture_id') or not self.snapshots.authorized(c,latest['capture_id']):raise ValueError('当前原件采集授权已失效')
        if Path(binding['name']).suffix.lower()!=Path(row['display_name']).suffix.lower():raise ValueError('新格式更新必须保持同格式，跨格式请新纳入资料')
        # Keep native writes inside ordinary managed entries, as for legacy
        # text updates. A removed regular file may be recreated by an explicit
        # upload, but present links (including broken ancestors) are rejected.
        self.library._root()
        path=Path(row['path'])
        for component in (path,*path.parents):
            try:linked=_link(component)
            except FileNotFoundError:continue
            if linked:raise ValueError('管理副本路径不能经过链接或 junction')
        return row
    def _prior(self,c,binding,fingerprint):
        prior=self.library._retry(c,binding['submission_id'],fingerprint)
        if prior is None:return None
        attempt=c.execute('SELECT * FROM document_processing_attempts WHERE id=? AND capture_id=?',(prior['attempt_id'],prior['capture_id'])).fetchone()
        doc=c.execute('SELECT * FROM documents WHERE id=?',(prior['document_id'],)).fetchone()
        if attempt is None or doc is None or self.snapshots.retired('attempts',prior['attempt_id']):raise ValueError('上传回执对应的资料或尝试已失效')
        state=self.snapshots.detail(c,doc['pk']);current=self.library._receipt(c,prior['document_id']);latest=state.get('latest_attempt') or {}
        if binding['project_id'] not in current['project_ids'] or latest.get('capture_id')!=prior['capture_id'] or latest.get('attempt_id')!=prior['attempt_id'] or not self.snapshots.authorized(c,prior['capture_id']):
            raise ValueError('上传已被新项目、候选或处理尝试取代，请重新查看')
        return {**prior,'status':attempt['state'],'version':doc['version'],'processing_version':state['processing_version']}
    def _check_current_upload(self,c,binding):
        # A committed upload supersedes its own original CAS. Only its exact,
        # still-current receipt may resume; later candidates/removal still fail.
        if self._prior(c,binding,digest(['managed-original',binding])) is None:
            self._target(c,binding)

    def _view(self,status):
        received=status['received']['raw'];state=self.transfers.binding(status['transfer_id'])
        length=state['bytes'];parts=(length+BLOCK_LIMIT-1)//BLOCK_LIMIT
        count=parts if received==length else received//BLOCK_LIMIT
        return {'upload_id':status['transfer_id'],'block_bytes':BLOCK_LIMIT,'received_parts':list(range(count)),'committed':status['committed']}
    def begin(self,body):
        allowed={'project_id','project_key','submission_id','name','sha256','bytes'}
        if self.context_check:allowed|={'hub_id','document_epoch'}
        update={'document_id','expected_version','expected_processing_version','expected_revision'}
        candidate={'capture_id','expected_attempt_id'}
        if not isinstance(body,dict) or set(body) not in (allowed,allowed|update,allowed|update|candidate):raise ValueError('上传需要当前项目身份、提交身份、显示名及原SHA/长度；更新还需文档和当前版本')
        integer(body['project_id'],'项目ID')
        self.library._submission(body['submission_id'])
        if not isinstance(body['project_key'],str) or not body['project_key']:raise ValueError('需要刚查看的稳定项目身份')
        name=display_name(body['name'],native=True)
        if Path(name).suffix.lower() not in {'.docx','.xlsx','.pdf'}:raise ValueError('分块原件入口支持 .docx/.xlsx/.pdf；小文本沿用资料入口')
        if type(body['bytes']) is not int or not 0<body['bytes']<=RAW_LIMIT:raise ValueError('新格式原件须为1字节到20MiB')
        if not isinstance(body['sha256'],str):raise ValueError('原件SHA无效')
        self.snapshots.blob('raw',body['sha256'])
        # A disjoint archive namespace prevents this upload identity from being
        # mistaken for a device projection transfer of an identical body.
        from .references import material
        binding={**body,'purpose':'managed-original','device_id':'managed','archive_id':material(self.db)[0],'generation':0}
        with self._hold():
            self._check(binding)
            with self.db.connect() as c:self._check_current_upload(c,binding)
            return self._view(self.transfers.begin(binding,{'raw':{'bytes':body['bytes'],'sha256':body['sha256']}}))
    def part(self,upload_id,index,raw,expected_sha):
        integer(index,'分块序号',minimum=0)
        binding=self.transfers.binding(upload_id)
        with self._hold():
            self._check(binding)
            with self.db.connect() as c:self._check_current_upload(c,binding)
        # Body I/O is bounded and does not hold the Hub guard or a DB lock.
        return self._view(self.transfers.part(upload_id,'raw',index*BLOCK_LIMIT,raw,expected_sha))
    def commit(self,upload_id,body):
        binding=self.transfers.binding(upload_id)
        with self.snapshots.pin([('raw',binding['sha256'])]):
            return self._commit(upload_id,body)
    def _commit(self,upload_id,body):
        binding=self.transfers.binding(upload_id)
        if not isinstance(body,dict):raise ValueError('提交上下文无效')
        if self.context_check:
            if set(body)!={'hub_id','document_epoch'}:raise ValueError('需要当前Hub身份和文档epoch')
            self.context_check(body)
        elif body:raise ValueError('本机原件提交不接受额外身份')
        fingerprint=digest(['managed-original',binding])
        # Receipt replay precedes the old update CAS. The old expected AID is
        # necessarily superseded by this submission's own new AID, but it may
        # never replay over a later candidate, retry, removal or project move.
        with self._hold(),control_lock(self.library.lock):
            self._check(binding)
            with self.db.connect() as c:
                prior=self._prior(c,binding,fingerprint)
                if prior is not None:return prior
                self._target(c,binding)
        _,raw=self.transfers.commit(upload_id,lambda b,raw,result:raw)
        with self._hold(),control_lock(self.library.lock):
            self._check(binding)
            with self.db.connect() as c:
                prior=self._prior(c,binding,fingerprint)
                if prior is not None:return prior
                existing=self._target(c,binding)
                backup=None
                if existing is not None:
                    capture=c.execute('SELECT raw_sha256 FROM document_captures WHERE id=?',(existing['latest_attempt']['capture_id'],)).fetchone()
                    backup=self.snapshots.blob('raw',capture[0]).read_bytes()
            self.library._root()
            directory=None
            if existing is None:
                directory=self.library.root/uuid4().hex;directory.mkdir(mode=0o700)
                path=directory/('file'+Path(binding['name']).suffix.lower())
            else:path=Path(existing['path'])
            try:
                self.library._replace(path,raw)
                with self.db.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    existing=self._target(c,binding)
                    self.documents._projects(c,[binding['project_id']])
                    seq=c.execute("UPDATE document_meta SET value=value+1 WHERE key='request_seq' RETURNING value").fetchone()[0]
                    if existing is None:
                        sid=uuid4().hex;ident=uuid4().hex
                        c.execute("INSERT INTO document_sources(id,path,kind,recursive,exclude,request_seq) VALUES(?,?,'file',1,'[]',?)",(sid,str(path),seq))
                        c.execute('INSERT INTO document_source_projects VALUES(?,?)',(sid,binding['project_id']))
                        c.execute('INSERT INTO documents(id,path_key,path) VALUES(?,?,?)',(ident,os.path.normcase(str(path)),str(path)))
                        c.execute('INSERT INTO document_library(document_id,source_id,display_name,created_project) VALUES(?,?,?,?)',(ident,sid,binding['name'],binding['project_id']))
                    else:
                        sid=existing['source_id'];ident=existing['id']
                        # Preserve the published qualification/revision while
                        # replacing the separate capture authorization.
                        c.execute('UPDATE document_capture_authorizations SET active=0 WHERE source_id=?',(sid,))
                        c.execute('UPDATE document_sources SET request_seq=?,refresh_id=? WHERE id=?',(seq,uuid4().hex,sid))
                    source=dict(c.execute('SELECT * FROM document_sources WHERE id=?',(sid,)).fetchone())
                    token=self.snapshots.capture_metadata(c,source,path,binding['sha256'],len(raw),Path(path).suffix[1:])
                    if existing is None:c.execute("INSERT INTO document_memberships VALUES(?,?,?,'pending',1,NULL)",(sid,token['document_pk'],path.name))
                    payload={'binding':binding,'source':source,'token':token,'path':str(path)}
                    detail=self.snapshots.detail(c,token['document_pk'])
                    doc=c.execute('SELECT version FROM documents WHERE pk=?',(token['document_pk'],)).fetchone()
                    receipt={'document_id':ident,'capture_id':token['capture_id'],'attempt_id':token['attempt_id'],'status':'pending','version':doc['version'],'processing_version':detail['processing_version']}
                    c.execute("INSERT INTO document_upload_jobs VALUES(?,?,?,'pending',NULL) ON CONFLICT(document_id) DO UPDATE SET source_id=excluded.source_id,payload=excluded.payload,state='pending',error=NULL",(ident,sid,json.dumps(payload)))
                    c.execute('INSERT INTO document_library_submissions VALUES(?,?,?,?)',(binding['submission_id'],fingerprint,ident,json.dumps(receipt)))
                return receipt
            except BaseException:
                if directory is not None:path.unlink(missing_ok=True);directory.rmdir()
                elif backup is not None:self.library._replace(path,backup)
                raise
    def run_pending(self):
        # Kicks coalesce while another coordinator owns this durable queue.
        # Never wait for a whole content task in an HTTP background callback.
        while True:
            acquired = False
            try:
                with control_lock(self.snapshots.root/'upload-queue.lock', timeout=0):
                    acquired = True
                    self._drain_pending()
            except RuntimeError:
                if acquired:
                    raise  # A real coordinator failure must remain visible.
                return
            # Check only AFTER releasing ownership. A producer may have added
            # work after the drain saw empty but before its busy kick returned.
            # If it commits later, its own kick can acquire the now-free lock.
            with self.db.connect() as c:
                if c.execute("SELECT 1 FROM document_upload_jobs WHERE state='pending' LIMIT 1").fetchone() is None:
                    return

    def _drain_pending(self):
        while True:
            with self.db.connect() as c:
                job=c.execute("SELECT * FROM document_upload_jobs WHERE state='pending' ORDER BY rowid LIMIT 1").fetchone()
                if job is None:return
                value=json.loads(job['payload'])
            token=value['token'];source=value['source'];error=None;result=None
            try:
                with self._hold():self._check(value['binding'])
                with self.db.connect() as c:
                    attempt=c.execute('SELECT * FROM document_processing_attempts WHERE id=?',(token['attempt_id'],)).fetchone()
                if attempt and attempt['result_sha256'] and attempt['state'] in {'ready','partial'}:
                    token['result_sha256']=attempt['result_sha256'];result=self.snapshots.load_result(token['result_sha256'])
                else:result=self.snapshots.process(token,token['profile']['format'])
            except (OSError,ValueError,RuntimeError) as exc:error=str(exc)
            item={'path':Path(value['path']),'relative_path':Path(value['path']).name,'error':error,'captured_id':token['capture_id']}
            if result is not None:item.update(snapshot_token=token,processed_result=result,sha256=token['raw_sha256'],text=result['text'])
            try:
                with self._hold():
                    self._check(value['binding'])
                    # Failed managed replacement preserves its old complete
                    # publication. Path refresh keeps its separate withdrawal
                    # semantics in Documents._publish.
                    with self.db.connect() as c:
                        state=c.execute('SELECT current_capture,latest_attempt,published_capture FROM document_snapshot_state WHERE document_pk=?',(token['document_pk'],)).fetchone()
                    if state is None or state['current_capture']!=token['capture_id'] or state['latest_attempt']!=token['attempt_id']:raise ValueError('上传任务已被新候选或尝试取代')
                    if not error or not state['published_capture']:self.documents._publish(source,{'error':None,'counts':{'ready':int(not error),'failed':int(bool(error)),'candidates':1,'billed_bytes':0,'new_raw_bytes':value['binding']['bytes'],'ignored_entries':0},'files':[item]})
            except (OSError,ValueError,RuntimeError) as exc:error=str(exc)
            if error:
                try:
                    with self._hold():
                        self._check(value['binding'])
                        self.snapshots.fail_current(token,error)
                except (OSError,ValueError,RuntimeError):
                    # A changed Hub/project context must not write into the
                    # new context just to finish an obsolete task's status.
                    pass
            with self.db.connect() as c:
                c.execute('UPDATE document_upload_jobs SET state=?,error=? WHERE document_id=? AND payload=?',('failed' if error else 'done',error,job['document_id'],job['payload']))

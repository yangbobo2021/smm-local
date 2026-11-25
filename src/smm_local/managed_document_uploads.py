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
from .document_protocol import integer
from .document_results import sha
from .document_snapshots import RAW_LIMIT
from .document_transfers import BlobTransfers,BLOCK_LIMIT
from .managed_documents import display_name


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
    def _view(self,status):
        received=status['received']['raw'];state=self.transfers.binding(status['transfer_id'])
        length=state['bytes'];parts=(length+BLOCK_LIMIT-1)//BLOCK_LIMIT
        count=parts if received==length else received//BLOCK_LIMIT
        return {'upload_id':status['transfer_id'],'block_bytes':BLOCK_LIMIT,'received_parts':list(range(count)),'committed':status['committed']}
    def begin(self,body):
        allowed={'project_id','project_key','submission_id','name','sha256','bytes'}
        if self.context_check:allowed|={'hub_id','document_epoch'}
        if not isinstance(body,dict) or set(body)!=allowed:raise ValueError('上传需要当前项目身份、提交身份、显示名及原SHA/长度')
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
            return self._view(self.transfers.begin(binding,{'raw':{'bytes':body['bytes'],'sha256':body['sha256']}}))
    def part(self,upload_id,index,raw,expected_sha):
        integer(index,'分块序号',minimum=0)
        binding=self.transfers.binding(upload_id)
        with self._hold():self._check(binding)
        # Body I/O is bounded and does not hold the Hub guard or a DB lock.
        return self._view(self.transfers.part(upload_id,'raw',index*BLOCK_LIMIT,raw,expected_sha))
    def commit(self,upload_id,body):
        binding=self.transfers.binding(upload_id)
        if not isinstance(body,dict):raise ValueError('提交上下文无效')
        if self.context_check:
            if set(body)!={'hub_id','document_epoch'}:raise ValueError('需要当前Hub身份和文档epoch')
            self.context_check(body)
        elif body:raise ValueError('本机原件提交不接受额外身份')
        with self._hold():self._check(binding)
        _,raw=self.transfers.commit(upload_id,lambda b,raw,result:raw)
        fingerprint=digest(['managed-original',binding])
        with self._hold(),control_lock(self.library.lock):
            self._check(binding)
            with self.db.connect() as c:
                prior=self.library._retry(c,binding['submission_id'],fingerprint)
            if prior is not None:return prior
            self.library._root()
            directory=self.library.root/uuid4().hex;directory.mkdir(mode=0o700)
            path=directory/('file'+Path(binding['name']).suffix.lower())
            try:
                self.library._replace(path,raw)
                with self.db.connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    self.documents._projects(c,[binding['project_id']])
                    seq=c.execute("UPDATE document_meta SET value=value+1 WHERE key='request_seq' RETURNING value").fetchone()[0]
                    sid=uuid4().hex;ident=uuid4().hex
                    c.execute("INSERT INTO document_sources(id,path,kind,recursive,exclude,request_seq) VALUES(?,?,'file',1,'[]',?)",(sid,str(path),seq))
                    c.execute('INSERT INTO document_source_projects VALUES(?,?)',(sid,binding['project_id']))
                    c.execute('INSERT INTO documents(id,path_key,path) VALUES(?,?,?)',(ident,os.path.normcase(str(path)),str(path)))
                    c.execute('INSERT INTO document_library(document_id,source_id,display_name,created_project) VALUES(?,?,?,?)',(ident,sid,binding['name'],binding['project_id']))
                    source=dict(c.execute('SELECT * FROM document_sources WHERE id=?',(sid,)).fetchone())
                    token=self.snapshots.capture_metadata(c,source,path,binding['sha256'],len(raw),Path(path).suffix[1:])
                    c.execute("INSERT INTO document_memberships VALUES(?,?,?,'pending',1,NULL)",(sid,token['document_pk'],path.name))
                    payload={'binding':binding,'source':source,'token':token,'path':str(path)}
                    receipt={'document_id':ident,'capture_id':token['capture_id'],'attempt_id':token['attempt_id'],'status':'pending','version':0,'processing_version':0}
                    c.execute("INSERT INTO document_upload_jobs VALUES(?,?,?,'pending',NULL)",(ident,sid,json.dumps(payload)))
                    c.execute('INSERT INTO document_library_submissions VALUES(?,?,?,?)',(binding['submission_id'],fingerprint,ident,json.dumps(receipt)))
                return receipt
            except BaseException:
                path.unlink(missing_ok=True);directory.rmdir();raise
    def run_pending(self):
        # This is a queue coordinator lock, never acquired by query/read. The
        # existing supervisor separately owns the archive-wide content slot.
        with control_lock(self.snapshots.root/'upload-queue.lock'):
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
                item={'path':Path(value['path']),'relative_path':Path(value['path']).name,'error':error}
                if result is not None:item.update(snapshot_token=token,processed_result=result,sha256=token['raw_sha256'],text=result['text'])
                try:
                    with self._hold():
                        self._check(value['binding'])
                        self.documents._publish(source,{'error':None,'counts':{'ready':int(not error),'failed':int(bool(error)),'candidates':1,'billed_bytes':0,'new_raw_bytes':value['binding']['bytes'],'ignored_entries':0},'files':[item]})
                except (OSError,ValueError,RuntimeError) as exc:error=str(exc)
                with self.db.connect() as c:
                    c.execute('UPDATE document_upload_jobs SET state=?,error=? WHERE document_id=?',('failed' if error else 'done',error,job['document_id']))

"""Immutable captured bytes/results and short transactional snapshot metadata.

Only explicit creator actions call capture/process. Read/receive paths use the
stdlib validation and immutable blobs; they never import a format processor.
"""
from __future__ import annotations
from contextlib import nullcontext
import json
import os
from pathlib import Path
import stat
import tempfile
from uuid import uuid4
from .document_results import encode,sha,validate,RESULT_LIMIT
from .core import utcnow
from .archive_protocol import control_lock

RAW_LIMIT=20*1024*1024
STAGING_LIMIT=256*1024*1024


class Snapshots:
    def __init__(self,db):
        self.db=db;self.root=db.db_path.resolve().parent/'.document-snapshots'
        with db.connect() as c:c.executescript('''
        CREATE TABLE IF NOT EXISTS document_captures(id TEXT PRIMARY KEY,document_pk INTEGER NOT NULL,raw_sha256 TEXT NOT NULL,raw_bytes INTEGER NOT NULL,format TEXT NOT NULL,sequence INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS document_capture_authorizations(capture_id TEXT NOT NULL,source_id TEXT NOT NULL REFERENCES document_sources(id) ON DELETE CASCADE,revision INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(capture_id,source_id));
        CREATE TABLE IF NOT EXISTS document_processing_attempts(id TEXT PRIMARY KEY,capture_id TEXT NOT NULL,config_revision INTEGER NOT NULL,state TEXT NOT NULL,error TEXT,result_sha256 TEXT,created_at TEXT NOT NULL,finished_at TEXT);
        CREATE TABLE IF NOT EXISTS document_snapshot_state(document_pk INTEGER PRIMARY KEY,current_capture TEXT,latest_attempt TEXT,published_capture TEXT,result_sha256 TEXT,processing_version INTEGER NOT NULL DEFAULT 0,profile_sha256 TEXT,published_status TEXT);
        CREATE TABLE IF NOT EXISTS document_published_blobs(kind TEXT NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(kind,sha256));
        CREATE TABLE IF NOT EXISTS document_processing_config(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision INTEGER NOT NULL,payload TEXT NOT NULL);
        INSERT OR IGNORE INTO document_processing_config VALUES(1,0,'{}');
        ''')
    def _directory(self,name):
        path=self.root/name
        for part in [path,*path.parents]:
            if part.exists() and (part.is_symlink() or bool(getattr(part.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))):raise ValueError('快照存储路径不能经过链接或junction')
        path.mkdir(parents=True,exist_ok=True,mode=0o700);return path
    def blob(self,kind,digest):
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('快照摘要无效')
        return self.root/kind/digest
    def _published_blobs(self):
        with self.db.connect() as c:
            values={(row[0],row[1]) for row in c.execute('SELECT kind,sha256 FROM document_published_blobs')}
            # Current snapshots also cover archives opened before the explicit
            # publication ledger existed. No source reading or processing.
            for row in c.execute('SELECT x.raw_sha256,s.result_sha256 FROM document_snapshot_state s JOIN document_captures x ON x.id=s.published_capture'):
                values.add(('raw',row[0]));values.add(('results',row[1]))
            return values
    def _unpublished_bytes(self):
        published=self._published_blobs();total=0
        for kind in ('raw','results'):
            directory=self.root/kind
            if directory.exists():
                directory_state=directory.lstat()
                if not stat.S_ISDIR(directory_state.st_mode) or bool(getattr(directory_state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):raise ValueError('暂存目录不能经过链接或junction')
            for path in directory.iterdir() if directory.exists() else []:
                state=path.lstat()
                if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):raise ValueError('暂存存储只能包含普通文件')
                if (kind,path.name) not in published:total+=state.st_size
        from .document_transfers import reservations
        return total + reservations(self)
    def put(self,kind,raw):
        if kind not in {'raw','results'}:raise ValueError('未知的快照字节类型')
        if len(raw)>(RAW_LIMIT if kind=='raw' else RESULT_LIMIT):raise ValueError('快照原件/结果超过单份上限')
        digest=sha(raw);directory=self._directory(kind);target=directory/digest
        # A dedicated cross-process byte-admission lock reserves capacity before
        # opening a body file. Database reads finish before body I/O; parsing,
        # OCR, networking and query/read paths never acquire this lock.
        with control_lock(self.root/'capacity.lock'):
            from .document_transfers import reclaim_expired
            reclaim_expired(self)
            if target.exists():
                state=target.lstat()
                if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):raise ValueError('现有快照内容不是普通文件')
                with target.open('rb') as stream:saved=stream.read(len(raw)+1)
                if len(saved)!=len(raw) or sha(saved)!=digest:raise ValueError('现有快照内容损坏')
                return digest
            if self._unpublished_bytes()+len(raw)>STAGING_LIMIT:raise ValueError('未发布暂存超过256MiB')
            fd,name=tempfile.mkstemp(prefix='.pending-',dir=directory)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.replace(name,target)
            finally:
                if os.path.exists(name):os.unlink(name)
        return digest
    def config(self,c=None):
        if c is None:
            with self.db.connect() as con:return self.config(con)
        row=c.execute('SELECT revision,payload FROM document_processing_config WHERE singleton=1').fetchone()
        return {'revision':row['revision'],**json.loads(row['payload'])}
    def authorized(self,c,capture_id):
        return bool(c.execute('SELECT 1 FROM document_capture_authorizations a JOIN document_sources s ON s.id=a.source_id WHERE a.capture_id=? AND a.active=1 AND a.revision=s.revision',(capture_id,)).fetchone())
    def capture(self,source,path,raw,format,*,mutation_context=None):
        if len(raw)>RAW_LIMIT:raise ValueError('新格式原文件超过20MiB')
        raw_sha=self.put('raw',raw)
        # Immutable body I/O completes before a creator control lock is held.
        with (mutation_context() if mutation_context is not None else nullcontext()):
            with self.db.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                return self.capture_metadata(c,source,path,raw_sha,len(raw),format)
    def capture_metadata(self,c,source,path,raw_sha,raw_bytes,format):
        # The caller has already saved and verified the immutable raw blob.
        # Creator upload registration can persist source, capture and job in
        # one short transaction without holding a database lock over body I/O.
        profile={'rendering':'smm-document-text-v1','format':format}
        current=c.execute('SELECT revision,refresh_id FROM document_sources WHERE id=?',(source['id'],)).fetchone()
        if current is None or current['revision']!=source['revision'] or current['refresh_id']!=source['refresh_id']:raise ValueError('采集来源已变化')
        key=os.path.normcase(str(path));c.execute('INSERT OR IGNORE INTO documents(id,path_key,path) VALUES(?,?,?)',(uuid4().hex,key,str(path)))
        doc=c.execute('SELECT pk FROM documents WHERE path_key=?',(key,)).fetchone();pk=doc['pk']
        state=c.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(pk,)).fetchone()
        config=self.config(c);profile['config_revision']=config['revision'];profile_sha=sha(encode(profile))
        if state and state['current_capture']:
            old=c.execute('SELECT * FROM document_captures WHERE id=?',(state['current_capture'],)).fetchone()
            if old and old['raw_sha256']==raw_sha and self.authorized(c,old['id']) and state['published_capture']==old['id'] and state['profile_sha256']==profile_sha:
                c.execute('INSERT INTO document_capture_authorizations VALUES(?,?,?,1) ON CONFLICT(capture_id,source_id) DO UPDATE SET revision=excluded.revision,active=1',(old['id'],source['id'],source['revision']))
                return {'document_pk':pk,'capture_id':old['id'],'attempt_id':state['latest_attempt'],'raw_sha256':raw_sha,'result_sha256':state['result_sha256'],'profile_sha256':profile_sha,'reused':True,'config':config,'profile':profile}
        cid=uuid4().hex;aid=uuid4().hex
        c.execute('INSERT INTO document_captures VALUES(?,?,?,?,?,?,?)',(cid,pk,raw_sha,raw_bytes,format,source['request_seq'],utcnow()))
        c.execute('INSERT INTO document_capture_authorizations VALUES(?,?,?,1)',(cid,source['id'],source['revision']))
        c.execute("INSERT INTO document_processing_attempts VALUES(?,?,?,'pending',NULL,NULL,?,NULL)",(aid,cid,config['revision'],utcnow()))
        c.execute('INSERT INTO document_snapshot_state(document_pk,current_capture,latest_attempt) VALUES(?,?,?) ON CONFLICT(document_pk) DO UPDATE SET current_capture=excluded.current_capture,latest_attempt=excluded.latest_attempt',(pk,cid,aid))
        return {'document_pk':pk,'capture_id':cid,'attempt_id':aid,'raw_sha256':raw_sha,'profile_sha256':profile_sha,'reused':False,'config':config,'profile':profile}
    def process(self,token,format):
        from .document_processing import process
        return process(self,token)
    def publish(self,c,pk,token,result):
        state=c.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(pk,)).fetchone()
        if not state or state['current_capture']!=token['capture_id'] or state['latest_attempt']!=token['attempt_id'] or self.config(c)['revision']!=token['config']['revision'] or not self.authorized(c,token['capture_id']):raise ValueError('捕获/处理/配置或授权已变化，旧结果不能发布')
        changed=state['result_sha256']!=token['result_sha256'] or state['profile_sha256']!=token['profile_sha256']
        processing_version=state['processing_version']+int(changed)
        c.executemany('INSERT OR IGNORE INTO document_published_blobs(kind,sha256) VALUES(?,?)',[('raw',token['raw_sha256']),('results',token['result_sha256'])])
        c.execute('UPDATE document_snapshot_state SET published_capture=?,result_sha256=?,processing_version=?,profile_sha256=?,published_status=? WHERE document_pk=?',(token['capture_id'],token['result_sha256'],processing_version,token['profile_sha256'],result['status'],pk))
    def load_result(self,digest):
        path=self.blob('results',digest)
        if path.is_symlink():raise ValueError('结果快照不能经过链接')
        raw=path.read_bytes()
        if len(raw)>RESULT_LIMIT or sha(raw)!=digest:raise ValueError('结果快照损坏或超限')
        return validate(json.loads(raw))
    def detail(self,c,pk):
        state=c.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(pk,)).fetchone()
        if state is None:return {}
        doc=c.execute('SELECT version FROM documents WHERE pk=?',(pk,)).fetchone()
        attempt=c.execute('SELECT * FROM document_processing_attempts WHERE id=?',(state['latest_attempt'],)).fetchone()
        capture=c.execute('SELECT * FROM document_captures WHERE id=?',(state['current_capture'],)).fetchone()
        published=None
        if state['published_capture']:
            saved=c.execute('SELECT * FROM document_captures WHERE id=?',(state['published_capture'],)).fetchone()
            published={'capture_id':saved['id'],'sha256':saved['raw_sha256'],'raw_bytes':saved['raw_bytes'],'version':doc['version'],'processing_version':state['processing_version'],'result_sha256':state['result_sha256'],'status':state['published_status']}
        latest=None if attempt is None else {'attempt_id':attempt['id'],'capture_id':attempt['capture_id'],'config_revision':attempt['config_revision'],'status':attempt['state'],'error':attempt['error'],'created_at':attempt['created_at'],'finished_at':attempt['finished_at']}
        retry=None
        if capture and attempt and attempt['state'] not in {'pending','processing'} and self.authorized(c,capture['id']):
            retry={'capture_id':capture['id'],'sha256':capture['raw_sha256'],'expected_attempt_id':attempt['id'],'expected_version':doc['version'],'expected_processing_version':state['processing_version']}
        # A successful extraction is not yet a successful publication. Compare
        # the whole result, not just CID: reprocessing the same capture with a
        # new profile can still be waiting for its new result to be published.
        publication_pending=bool(attempt and attempt['state'] in {'ready','partial','empty-success'} and
            (state['published_capture']!=attempt['capture_id'] or state['result_sha256']!=attempt['result_sha256']))
        return {'processing_version':state['processing_version'],'published_snapshot':published,'latest_attempt':latest,'retry_target':retry,'publication_pending':publication_pending}
    def retry(self,document_id,capture_id,expected_attempt_id,expected_version,expected_processing_version):
        with self.db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            doc=c.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone()
            if doc is None:raise ValueError('文档不存在')
            target=self.detail(c,doc['pk']).get('retry_target')
            if not target or any(target[k]!=v for k,v in {'capture_id':capture_id,'expected_attempt_id':expected_attempt_id,'expected_version':expected_version,'expected_processing_version':expected_processing_version}.items()):raise ValueError('重处理目标已过期或采集授权已撤销，请重新查看当前状态')
            capture=c.execute('SELECT * FROM document_captures WHERE id=? AND document_pk=?',(capture_id,doc['pk'])).fetchone()
            if capture is None:raise ValueError('捕获不属于此文档')
            config=self.config(c);profile={'rendering':'smm-document-text-v1','format':capture['format'],'config_revision':config['revision']};aid=uuid4().hex
            c.execute('INSERT INTO document_processing_attempts(id,capture_id,config_revision,state,created_at) VALUES(?,?,?,?,?)',(aid,capture_id,config['revision'],'pending',utcnow()))
            c.execute('UPDATE document_snapshot_state SET latest_attempt=? WHERE document_pk=?',(aid,doc['pk']))
            return {'document_pk':doc['pk'],'capture_id':capture_id,'attempt_id':aid,'raw_sha256':capture['raw_sha256'],'profile_sha256':sha(encode(profile)),'reused':False,'config':config,'profile':profile}
    def metadata(self,c,pk):
        state,result=self.result(c,pk)
        if state is None:return {},None
        tables=[{k:v for k,v in table.items() if k!='cells'} for table in result['tables']]
        return {'format':result['format'],'processing_version':state['processing_version'],'result_sha256':state['result_sha256'],'profile':result['profile'],'coverage':result['coverage'],'locations':result['locations'],'tables':tables,'original_available':True,'processing_status':state['published_status']},result
    def load_result(self,digest):
        path=self.blob('results',digest)
        if path.is_symlink():raise ValueError('结果快照不能是链接')
        with path.open('rb') as stream:raw=stream.read(RESULT_LIMIT+1)
        if len(raw)>RESULT_LIMIT or sha(raw)!=digest:raise ValueError('处理结果快照摘要损坏')
        value=json.loads(raw);validate(value);return value
    def result(self,c,pk):
        row=c.execute('SELECT s.*,x.raw_sha256,x.raw_bytes,x.format FROM document_snapshot_state s JOIN document_captures x ON x.id=s.published_capture WHERE s.document_pk=?',(pk,)).fetchone()
        if row is None:return None,None
        return dict(row),self.load_result(row['result_sha256'])
    def original(self,c,pk):
        state,result=self.result(c,pk)
        if state is None:raise ValueError('legacy_original_not_captured: 未保存原字节，不能由文本伪造原件')
        path=self.blob('raw',state['raw_sha256'])
        if path.is_symlink():raise ValueError('原件快照不能是链接')
        with path.open('rb') as stream:raw=stream.read(RAW_LIMIT+1)
        if len(raw)!=state['raw_bytes'] or sha(raw)!=state['raw_sha256']:raise ValueError('原件快照摘要损坏')
        return raw

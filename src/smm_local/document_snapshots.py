"""Immutable captured bytes/results and short transactional snapshot metadata.

Only explicit creator actions call capture/process. Read/receive paths use the
stdlib validation and immutable blobs; they never import a format processor.
"""
from __future__ import annotations
from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import stat
import tempfile
from uuid import uuid4
from .document_results import encode,sha,validate,RESULT_LIMIT
from .core import utcnow
from .archive_protocol import atomic_json, control_lock, digest as protocol_digest

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
        # Establish stable archive identity before any body-admission lock.
        # A database filename can later be reused by a different archive.
        from .references import material
        material(db)
    def _directory(self,name):
        path=self.root/name
        for part in [path,*path.parents]:
            if part.exists() and (part.is_symlink() or bool(getattr(part.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))):raise ValueError('快照存储路径不能经过链接或junction')
        path.mkdir(parents=True,exist_ok=True,mode=0o700);return path
    def blob(self,kind,digest):
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('快照摘要无效')
        return self.root/kind/digest
    def _gc_path(self,name):
        return self._directory('reclamation')/name
    @contextmanager
    def _gc_metadata_lock(self):
        # Separate from capacity.lock: query readers never wait for content
        # processing or network I/O.  Writers hold this only during atomic JSON
        # replacement, preventing Windows readers from blocking that rename.
        lock=self._directory('reclamation')/'metadata.lock'
        if os.path.lexists(lock):
            state=lock.lstat()
            if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):
                raise ValueError('回收元信息锁不能经过链接或特殊文件')
        with control_lock(lock):yield
    def _gc_read(self,name,default):
        path=self.root/'reclamation'/name
        directory=path.parent
        if not os.path.lexists(directory):return default
        state=directory.lstat()
        if not stat.S_ISDIR(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):
            raise ValueError('回收元信息目录不能经过链接或特殊文件')
        with self._gc_metadata_lock():
            if not os.path.lexists(path):return default
            state=path.lstat()
            if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):
                raise ValueError('回收元信息不能经过链接或特殊文件')
            return json.loads(path.read_text(encoding='utf-8'))
    def _gc_write(self,name,value):
        with self._gc_metadata_lock():atomic_json(self._gc_path(name),value)
    def _gc_owner(self,c=None):
        if c is None:
            with self.db.connect() as con:return self._gc_owner(con)
        row=c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
        if row is None:return None
        return protocol_digest(['document-blob-owner-v2',json.loads(row[0]),str(self.db.db_path.resolve())])
    def _own_blob(self,kind,digest,*,created):
        # capacity.lock is held. Existing unregistered bytes may belong to an
        # older/another archive; their ownership must never be guessed.
        owners=self._gc_read('owners.json',{})
        key=kind+'/'+digest
        if key not in owners and not created:return
        values=set(owners.get(key,[]));owner=self._register_gc_owner()
        if owner is None:return
        if owner not in values:
            owners[key]=sorted(values|{owner})
            self._gc_write('owners.json',owners)
    def retired(self,kind,ident):
        return ident in self._gc_read('retired.json',{}).get(kind,[])
    def _register_gc_owner(self):
        with self.db.connect() as c:
            row=c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
            archive=json.loads(row[0]);owner=self._gc_owner(c)
        archives=self._gc_read('archives.json',{})
        value={'archive_id':archive,'database':str(self.db.db_path.resolve())}
        if archives.get(owner)!=value:
            archives[owner]=value;self._gc_write('archives.json',archives)
        return owner

    def _foreign_gc_uses(self,owner,cids,aids):
        # Only explicitly registered sibling DBs with unchanged archive identity
        # can prove last use. Missing/replaced/copied/unknown owners stay billed.
        import sqlite3
        from contextlib import closing
        known={owner};protected=set();receipts={}
        for ident,entry in self._gc_read('archives.json',{}).items():
            if ident==owner:continue
            try:
                path=Path(entry['database'])
                if not path.is_absolute() or path.parent!=self.db.db_path.resolve().parent or path.is_symlink() or path.resolve()!=path:continue
                with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=.05)) as c:
                    c.row_factory=sqlite3.Row;c.execute('BEGIN')
                    archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
                    if archive!=entry['archive_id'] or protocol_digest(['document-blob-owner-v2',archive,str(path)])!=ident:continue
                    uses={(r[0],r[1]) for r in c.execute('SELECT kind,sha256 FROM document_published_blobs')}
                    states={r['document_pk']:dict(r) for r in c.execute('SELECT * FROM document_snapshot_state')}
                    valid=set();retired_captures=set();retired_attempts=set()
                    for row in c.execute('SELECT * FROM document_captures'):
                        state=states.get(row['document_pk'])
                        if state and state['published_capture']==row['id']:
                            uses.add(('raw',row['raw_sha256']))
                            if state['result_sha256']:uses.add(('results',state['result_sha256']))
                        if state and state['current_capture']==row['id'] and self.authorized(c,row['id']):
                            valid.add(row['id']);uses.add(('raw',row['raw_sha256']))
                        else:retired_captures.add(row['id'])
                    for row in c.execute('SELECT a.*,x.document_pk FROM document_processing_attempts a JOIN document_captures x ON x.id=a.capture_id'):
                        state=states.get(row['document_pk'])
                        if row['capture_id'] in valid and state and state['latest_attempt']==row['id'] and not self.retired('attempts',row['id']):
                            if row['result_sha256']:uses.add(('results',row['result_sha256']))
                        else:retired_attempts.add(row['id'])
                    tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    pending={r['submission_id']:json.loads(r['response']) for r in c.execute('SELECT * FROM document_library_submissions')} if 'document_library_submissions' in tables else {}
                    if 'hub_processed_stages' in tables:
                        for row in c.execute('SELECT payload FROM hub_processed_stages'):
                            value=json.loads(row[0]);uses.update({('raw',value['sha256']),('results',value['result_sha256'])})
                known.add(ident);protected.update(uses);cids.update(retired_captures);aids.update(retired_attempts)
                if archive not in receipts:receipts[archive]=pending
                else:receipts[archive]=None  # An ambiguous copied identity proves no retirement.
            except (OSError,sqlite3.Error,ValueError,KeyError,TypeError):
                continue
        return known,protected,receipts

    def _task_cleanup_confirmed(self,task_id):
        if not isinstance(task_id,str) or len(task_id)!=32 or any(c not in '0123456789abcdef' for c in task_id):return False
        directory=self._directory('tasks')/task_id
        try:
            for path in (directory,directory/'supervision.json'):
                info=path.lstat()
                if (not stat.S_ISDIR(info.st_mode) if path==directory else not stat.S_ISREG(info.st_mode)) or path.is_symlink() or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):return False
            state=json.loads((directory/'supervision.json').read_text(encoding='utf-8'))
            if state.get('token')!=task_id:return False
            if state.get('status')=='preparing' and state.get('gate_open') is False:
                from .document_supervisor import matching,cleanup_task
                try:controller=matching(state['controller'])
                except Exception:return False
                if controller is None:
                    state={**state,'status':'failed','error':'控制进程在激活解析前退出'}
                    atomic_json(directory/'supervision.json',state);cleanup_task(directory,state)
            elif os.name=='nt' and not (directory/'cleanup.json').exists():
                from .document_supervisor import recover_windows_task
                recover_windows_task(directory,state)
                state=json.loads((directory/'supervision.json').read_text(encoding='utf-8'))
            path=directory/'cleanup.json';info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):return False
            proof=json.loads(path.read_text(encoding='utf-8'))
            return (state.get('token')==task_id and state.get('status') in {'completed','failed'}
                    and proof=={'token':task_id,'worker':state['worker'],'stopped':True})
        except (OSError,ValueError,KeyError,TypeError,ImportError):return False

    def _pin_uses(self):
        protected=set()
        for path in self._directory('reclamation').glob('pin-*.json'):
            value=self._gc_read(path.name,{})
            lease=value.get('lease')
            keep=True
            if lease==path.stem+'.lock':
                lock=self._gc_path(lease)
                try:
                    info=lock.lstat()
                    if not stat.S_ISREG(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):raise ValueError('pin租约不是普通文件')
                    with control_lock(lock,timeout=0):
                        if value.get('task_id') is None or self._task_cleanup_confirmed(value['task_id']):
                            path.unlink(missing_ok=True);keep=False
                    if not keep:lock.unlink(missing_ok=True)
                except (OSError,RuntimeError,ValueError):pass
            if keep:protected.update(tuple(entry) for entry in value['blobs'])
        return protected

    @contextmanager
    def pin(self,blobs,*,task_id=None):
        entries=sorted(set(blobs))
        for kind,digest in entries:
            if kind not in {'raw','results'}:raise ValueError('未知快照pin类型')
            self.blob(kind,digest)
        ident='pin-'+uuid4().hex
        lease=self._gc_path(ident+'.lock');marker=self._gc_path(ident+'.json')
        # A dedicated kernel lease, not a PID/age heuristic, proves whether the
        # synchronous owner is alive. Content-task pins additionally require
        # the registered task's completed tree/payload cleanup proof.
        try:
            with control_lock(lease,timeout=0):
                with control_lock(self.root/'capacity.lock'):
                    owner=self._register_gc_owner()
                    atomic_json(marker,{'blobs':entries,'lease':lease.name,'task_id':task_id,'owner':owner})
                try:yield
                finally:
                    with control_lock(self.root/'capacity.lock'):
                        if task_id is None or self._task_cleanup_confirmed(task_id):marker.unlink(missing_ok=True)
        finally:
            with control_lock(self.root/'capacity.lock'):
                if not marker.exists():lease.unlink(missing_ok=True)
    def _ambiguous_gc_identity(self):
        # A backup can retain identity/CID/AID at another DB path. Its state
        # cannot retire the original's candidate. Include the calling DB before
        # it has ever registered a blob owner; unavailable old entries stay safe.
        with self.db.connect() as c:
            row=c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
            if row is None:return True
            archive=json.loads(row[0])
        entries=[*self._gc_read('archives.json',{}).values(),
                 {'archive_id':archive,'database':str(self.db.db_path.resolve())}]
        paths={}
        for entry in entries:
            if (not isinstance(entry,dict) or not isinstance(entry.get('archive_id'),str)
                    or not isinstance(entry.get('database'),str)):return True
            identity=entry['archive_id'];database=entry['database']
            if identity in paths and paths[identity]!=database:return True
            paths[identity]=database
        return False

    def reclaim_candidates(self):
        """Conservative canonical GC, called only while capacity.lock is held.

        All publication history stays protected. Unknown/shared ownership and
        unfinished receiver uses remain charged instead of risking data loss.
        """
        if self._ambiguous_gc_identity():return
        from .document_transfers import _states,_expired,_expired_marker
        import time
        protected=set()
        retired=self._gc_read('retired.json',{})
        cids=set(retired.get('captures',[]));aids=set(retired.get('attempts',[]))
        with self.db.connect() as c:
            c.execute('BEGIN')
            protected.update((r[0],r[1]) for r in c.execute('SELECT kind,sha256 FROM document_published_blobs'))
            for r in c.execute('SELECT x.raw_sha256,s.result_sha256 FROM document_snapshot_state s JOIN document_captures x ON x.id=s.published_capture'):
                protected.update({('raw',r[0]),('results',r[1])})
            states={r['document_pk']:dict(r) for r in c.execute('SELECT * FROM document_snapshot_state')}
            valid=set()
            for row in c.execute('SELECT * FROM document_captures'):
                state=states.get(row['document_pk'])
                if state and state['current_capture']==row['id'] and row['id'] not in cids and self.authorized(c,row['id']):
                    valid.add(row['id']);protected.add(('raw',row['raw_sha256']))
                else:cids.add(row['id'])
            for row in c.execute('SELECT a.*,x.document_pk FROM document_processing_attempts a JOIN document_captures x ON x.id=a.capture_id'):
                state=states.get(row['document_pk'])
                if row['capture_id'] in valid and state and state['latest_attempt']==row['id'] and row['id'] not in aids:
                    if row['result_sha256']:protected.add(('results',row['result_sha256']))
                else:aids.add(row['id'])
            tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            row=c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()
            archive_id=json.loads(row[0]) if row else None
            owner=self._gc_owner(c)
            receipts={r['submission_id']:json.loads(r['response']) for r in c.execute('SELECT * FROM document_library_submissions')} if 'document_library_submissions' in tables else {}
            if 'hub_processed_stages' in tables:
                for row in c.execute('SELECT payload FROM hub_processed_stages'):
                    value=json.loads(row[0]);protected.update({('raw',value['sha256']),('results',value['result_sha256'])})
        known,foreign,foreign_receipts=self._foreign_gc_uses(owner,cids,aids)
        protected.update(foreign)
        all_receipts=foreign_receipts
        if archive_id in all_receipts:all_receipts[archive_id]=None
        else:all_receipts[archive_id]=receipts
        # Qualification fences precede every physical deletion, and are kept
        # outside SQLite so restoring an older DB cannot resurrect an identity.
        updated={'captures':sorted(cids),'attempts':sorted(aids)}
        if updated!=retired:self._gc_write('retired.json',updated)
        for folder,state in _states(self):
            if _expired(self,folder,state,time.time()):continue
            binding=state['binding']
            source_receipts=all_receipts.get(binding.get('archive_id'))
            local_upload=(binding.get('purpose')=='managed-original' and binding.get('device_id')=='managed' and source_receipts is not None)
            receipt=source_receipts.get(binding.get('submission_id')) if local_upload else None
            obsolete=bool(receipt and (receipt.get('capture_id') in cids or receipt.get('attempt_id') in aids))
            if obsolete:
                marker=_expired_marker(self,folder.name)
                if not marker.exists():atomic_json(marker,{'retired':True})
            else:protected.update((kind,item['sha256']) for kind,item in state['blobs'].items())
        protected.update(self._pin_uses())
        owners=self._gc_read('owners.json',{})
        for key,values in owners.items():
            kind,digest=key.split('/',1)
            if owner is None or not values or not set(values).issubset(known) or (kind,digest) in protected:continue
            path=self.blob(kind,digest)
            if not os.path.lexists(path):continue
            state=path.lstat()
            if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):
                raise ValueError('回收内容不能经过链接或特殊文件')
            try:path.unlink()
            except PermissionError:continue  # Windows in-use bytes remain billed.
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
            self.reclaim_candidates()
            if target.exists():
                state=target.lstat()
                if not stat.S_ISREG(state.st_mode) or bool(getattr(state,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):raise ValueError('现有快照内容不是普通文件')
                with target.open('rb') as stream:saved=stream.read(len(raw)+1)
                if len(saved)!=len(raw) or sha(saved)!=digest:raise ValueError('现有快照内容损坏')
                self._own_blob(kind,digest,created=False)
                return digest
            if self._unpublished_bytes()+len(raw)>STAGING_LIMIT:raise ValueError('未发布暂存超过256MiB')
            fd,name=tempfile.mkstemp(prefix='.pending-',dir=directory)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.replace(name,target)
                self._own_blob(kind,digest,created=True)
            finally:
                if os.path.exists(name):os.unlink(name)
        return digest
    def config(self,c=None):
        if c is None:
            with self.db.connect() as con:return self.config(con)
        row=c.execute('SELECT revision,payload FROM document_processing_config WHERE singleton=1').fetchone()
        return {'revision':row['revision'],**json.loads(row['payload'])}
    def authorized(self,c,capture_id):
        if self.retired('captures',capture_id):return False
        return bool(c.execute('SELECT 1 FROM document_capture_authorizations a JOIN document_sources s ON s.id=a.source_id WHERE a.capture_id=? AND a.active=1 AND a.revision=s.revision',(capture_id,)).fetchone())
    def capture(self,source,path,raw,format,*,mutation_context=None):
        if len(raw)>RAW_LIMIT:raise ValueError('新格式原文件超过20MiB')
        with self.pin([('raw',sha(raw))]):
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
            if old and old['raw_sha256']==raw_sha and self.authorized(c,old['id']) and state['published_capture']==old['id'] and state['profile_sha256']==profile_sha and not self.retired('attempts',state['latest_attempt']):
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
    def fail_current(self,token,error,*,connection=None):
        """Finish a rejected publication without changing a newer attempt."""
        if token.get('reused'):return False
        def finish(c):
            changed=c.execute("""UPDATE document_processing_attempts SET state='failed',error=?,finished_at=?
                WHERE id=? AND capture_id=? AND config_revision=? AND state!='failed'
                AND EXISTS (SELECT 1 FROM document_snapshot_state s WHERE s.document_pk=?
                    AND s.current_capture=? AND s.latest_attempt=?)""",
                (str(error),utcnow(),token['attempt_id'],token['capture_id'],token['config']['revision'],
                 token['document_pk'],token['capture_id'],token['attempt_id'])).rowcount
            return bool(changed)
        if connection is not None:return finish(connection)
        with self.db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            return finish(c)
    def publish(self,c,pk,token,result):
        state=c.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(pk,)).fetchone()
        if not state or state['current_capture']!=token['capture_id'] or state['latest_attempt']!=token['attempt_id'] or self.config(c)['revision']!=token['config']['revision'] or not self.authorized(c,token['capture_id']) or self.retired('attempts',token['attempt_id']):raise ValueError('捕获/处理/配置或授权已变化，旧结果不能发布')
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
        if capture and attempt and not self.retired('attempts',attempt['id']) and attempt['state'] not in {'pending','processing'} and self.authorized(c,capture['id']):
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

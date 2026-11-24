"""Explicit, local-only text snapshots with file versions and source qualifications.

Nothing in this module watches files, calls federation, or sends model requests.
Only refresh opens source bodies; search and read operate on one SQLite snapshot.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import unicodedata
from uuid import uuid4

from .archive_protocol import sign
from .core import tokens, utcnow
from . import references

MIB = 1024 * 1024
FILE_LIMIT = 2 * MIB
SOURCE_LIMIT = 16 * MIB
CANDIDATE_LIMIT = 1000
LEGACY_SUFFIXES = {'.md', '.markdown', '.txt'}
NEW_SUFFIXES = {'.docx', '.xlsx', '.pdf'}
SUFFIXES = LEGACY_SUFFIXES | NEW_SUFFIXES
IGNORED_DIRS = {'.git', '.hg', '.svn', 'node_modules', '.venv', 'venv', 'build', 'dist'}


def _link(path):
    s = path.lstat()
    return stat.S_ISLNK(s.st_mode) or bool(getattr(s, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def _canonical(path):
    """Use actual entry spellings on macOS without merging distinct hard links."""
    if sys.platform != 'darwin':return path
    actual=Path(path.anchor)
    for part in path.parts[1:]:
        chosen=part
        try:
            names=os.listdir(actual)
            if part not in names:
                folded=unicodedata.normalize('NFD',part).casefold()
                for name in names:
                    if (unicodedata.normalize('NFD',name).casefold()==folded
                            and os.path.samestat((actual/name).stat(),(actual/part).stat())):
                        chosen=name;break
        except OSError:
            # An explicit readable file can live in a traversable parent that
            # does not permit listing. Do not broaden filesystem permissions.
            pass
        actual/=chosen
    return actual


def _root(value):
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError('文档来源必须是当前电脑上的绝对路径')
    path = Path(value)
    if _link(path):
        raise ValueError('文档来源根不能是符号链接或 junction')
    path = _canonical(path.resolve(strict=True))
    if not (path.is_file() or path.is_dir()) or not os.access(path, os.R_OK):
        raise ValueError('文档来源不是当前账户可读的常规文件或目录')
    if path.is_file() and path.suffix.lower() not in SUFFIXES:
        raise ValueError('仅支持 .md/.markdown/.txt 与已安装创建端支持的新文档格式')
    return path, 'directory' if path.is_dir() else 'file'


def _patterns(patterns):
    if not isinstance(patterns, list) or any(not isinstance(x, str) for x in patterns):
        raise ValueError('排除名单必须是路径模式列表')
    for x in patterns:
        if not x or '\\' in x or x.startswith('/') or '..' in x.split('/') or re.match(r'^[A-Za-z]:', x):
            raise ValueError('排除模式须为相对POSIX路径，不能含空值、..、反斜杠或绝对路径')
    return list(dict.fromkeys(patterns))


def _glob(pattern):
    """Compile slash-delimited glob syntax, independently of host glob rules."""
    pieces = []
    for part in pattern.rstrip('/').split('/'):
        if part == '**' and pieces and pieces[-1] == '**':
            continue
        pieces.append(part)
    out = ''
    for i, part in enumerate(pieces):
        if part == '**':
            if i < len(pieces)-1:
                out += '(?:[^/]+/)*'
            elif i == 0:
                out += '(?:[^/]+/)*[^/]*'
            else:
                # The preceding separator belongs to the optional ** tail.
                out = out[:-1] + '(?:/[^/]+)*'
        else:
            out += ''.join('[^/]*' if c == '*' else '[^/]' if c == '?' else re.escape(c) for c in part)
            if i < len(pieces)-1:
                out += '/'
    return re.compile('^' + out + '$')


def _signature(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def _read_file(path, expected):
    """Bind budget metadata to the actual opened regular file, with bounded I/O."""
    # Refuse links in the path at both ends; O_NOFOLLOW also protects the leaf
    # between the first check and open where the OS supports it.
    def check_path():
        if any(_link(p) for p in [path, *path.parents]):
            raise ValueError('读取期间路径变为链接或 junction')
        return path.stat()
    check_path()
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _signature(opened) != _signature(expected):
            raise ValueError('预算预检后文件已变化，请重新刷新')
        chunks = []; remaining = FILE_LIMIT + 1
        while remaining:
            data = os.read(fd, min(65536, remaining))
            if not data:
                break
            chunks.append(data); remaining -= len(data)
        raw = b''.join(chunks)
        if len(raw) > FILE_LIMIT:
            raise ValueError('文件超过2MiB')
        if (_signature(os.fstat(fd)) != _signature(expected) or _signature(check_path()) != _signature(expected)
                or len(raw) != expected.st_size):
            raise ValueError('读取期间文件已变化，请重新刷新')
    finally:
        os.close(fd)
    if b'\x00' in raw:
        raise ValueError('文件含二进制 NUL')
    try:
        text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    except UnicodeError as exc:
        raise ValueError('文件不是严格 UTF-8 文本') from exc
    return hashlib.sha256(raw).hexdigest(), text


def _read_raw(path, expected):
    def check():
        if any(_link(p) for p in [path,*path.parents]):raise ValueError('读取期间路径变为链接或junction')
        return path.stat()
    check();fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0))
    try:
        opened=os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or _signature(opened)!=_signature(expected):raise ValueError('预算预检后文件已变化')
        chunks=[];remaining=20*MIB+1
        while remaining:
            block=os.read(fd,min(65536,remaining))
            if not block:break
            chunks.append(block);remaining-=len(block)
        raw=b''.join(chunks)
        if len(raw)>20*MIB:raise ValueError('原文件超过20MiB')
        if len(raw)!=expected.st_size or _signature(os.fstat(fd))!=_signature(expected) or _signature(check())!=_signature(expected):raise ValueError('读取期间文件已变化')
        return raw
    finally:os.close(fd)


def _query_scope(con, scope, project_id):
    if scope not in {'all', 'project'}:
        raise ValueError('范围必须是 all 或 project')
    if scope == 'all':
        return None
    if type(project_id) is not int or not con.execute('SELECT 1 FROM projects WHERE id=?', (project_id,)).fetchone():
        raise ValueError('项目范围须指定有效的本机项目ID')
    return [project_id] + [r[0] for r in con.execute('SELECT CASE WHEN a=? THEN b ELSE a END FROM project_links WHERE a=? OR b=? ORDER BY 1', (project_id,project_id,project_id))]


def _range(text, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or end-start > 16000:
        raise ValueError('范围须为整个采集文本的Unicode码点 [start,end)，一次1至16000字符')
    return {'text':text[start:end], 'start':start, 'end':end,
            'start_line':1+text.count('\n',0,start), 'end_line':1+text.count('\n',0,end-1)}


class Documents:
    def __init__(self, archive):
        self.db = archive
        with archive.connect() as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS document_sources(
                    id TEXT PRIMARY KEY,path TEXT NOT NULL,kind TEXT NOT NULL,recursive INTEGER NOT NULL,
                    exclude TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'pending',resume_status TEXT NOT NULL DEFAULT 'pending',
                    refresh_id TEXT,request_seq INTEGER NOT NULL DEFAULT 0,started_at TEXT,finished_at TEXT,
                    error TEXT,counts TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS document_source_projects(
                    source_id TEXT REFERENCES document_sources(id) ON DELETE CASCADE,
                    project_id INTEGER REFERENCES projects(id),PRIMARY KEY(source_id,project_id));
                CREATE TABLE IF NOT EXISTS documents(
                    pk INTEGER PRIMARY KEY,id TEXT NOT NULL UNIQUE,path_key TEXT NOT NULL UNIQUE,path TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,sha256 TEXT,text TEXT,text_length INTEGER NOT NULL DEFAULT 0,
                    captured_at TEXT,captured_by_source_id TEXT,publish_seq INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS document_memberships(
                    source_id TEXT REFERENCES document_sources(id) ON DELETE CASCADE,
                    document_pk INTEGER REFERENCES documents(pk),relative_path TEXT NOT NULL,
                    status TEXT NOT NULL,qualification INTEGER NOT NULL,error TEXT,
                    PRIMARY KEY(source_id,document_pk));
                CREATE TABLE IF NOT EXISTS document_meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
                INSERT OR IGNORE INTO document_meta VALUES('request_seq',0);
                CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING fts5(text);
                CREATE INDEX IF NOT EXISTS document_memberships_file ON document_memberships(document_pk);
            ''')
            if 'text_sha256' not in {r['name'] for r in con.execute('PRAGMA table_info(documents)')}:
                con.execute("ALTER TABLE documents ADD COLUMN text_sha256 TEXT")
                for row in con.execute('SELECT pk,text FROM documents WHERE text IS NOT NULL').fetchall():
                    con.execute('UPDATE documents SET text_sha256=? WHERE pk=?',(hashlib.sha256(row['text'].encode('utf-8')).hexdigest(),row['pk']))
            if 'resume_status' not in {r['name'] for r in con.execute('PRAGMA table_info(document_sources)')}:
                con.execute("ALTER TABLE document_sources ADD COLUMN resume_status TEXT NOT NULL DEFAULT 'pending'")
                con.execute("UPDATE document_sources SET resume_status=status WHERE status!='refreshing'")

        from .document_snapshots import Snapshots
        self.snapshots=Snapshots(archive)

    @staticmethod
    def _sources(con):
        result=[]
        for row in con.execute('SELECT * FROM document_sources ORDER BY rowid'):
            source=dict(row);source['recursive']=bool(source['recursive']);source['exclude']=json.loads(source['exclude']);source['counts']=json.loads(source['counts'])
            source['project_ids']=[r[0] for r in con.execute('SELECT project_id FROM document_source_projects WHERE source_id=? ORDER BY project_id',(source['id'],))]
            source['message']='仅本机；保存配置后请明确运行 documents refresh'
            result.append(source)
        return result

    def sources(self):
        with self.db.connect() as con:
            con.execute('BEGIN');return self._sources(con)

    @staticmethod
    def _projects(con, projects):
        if not isinstance(projects, list) or any(type(x) is not int for x in projects):
            raise ValueError('项目名单必须是本机项目ID列表')
        projects=sorted(set(projects))
        for project in projects:
            if not con.execute('SELECT 1 FROM projects WHERE id=?',(project,)).fetchone():
                raise ValueError('本机项目不存在，请用 smm projects 取得ID')
        return projects

    def add(self, path, *, project_ids=None, exclude=None, recursive=True):
        root,kind=_root(path);exclude=_patterns([] if exclude is None else exclude)
        if type(recursive) is not bool:
            raise ValueError('recursive须为布尔值')
        source=uuid4().hex
        with self.db.connect() as con:
            con.execute('BEGIN IMMEDIATE');projects=self._projects(con,[] if project_ids is None else project_ids)
            con.execute('INSERT INTO document_sources(id,path,kind,recursive,exclude) VALUES(?,?,?,?,?)',(source,str(root),kind,recursive,json.dumps(exclude)))
            con.executemany('INSERT INTO document_source_projects VALUES(?,?)',[(source,p) for p in projects])
            return next(s for s in self._sources(con) if s['id']==source)

    @staticmethod
    def _prune(con):
        # A normal refresh is temporary, not a permanent qualification break.
        unused=[r[0] for r in con.execute("SELECT d.pk FROM documents d WHERE d.text IS NOT NULL AND NOT EXISTS(SELECT 1 FROM document_memberships m JOIN document_sources s ON s.id=m.source_id WHERE m.document_pk=d.pk AND m.status='ready' AND s.status IN ('ready','partial','refreshing'))")]
        for pk in unused:
            con.execute('DELETE FROM document_fts WHERE rowid=?',(pk,));con.execute('UPDATE documents SET text=NULL WHERE pk=?',(pk,))

    def set(self, source_id, *, project_ids=None, exclude=None, recursive=True):
        exclude=_patterns([] if exclude is None else exclude)
        if type(recursive) is not bool:
            raise ValueError('recursive须为布尔值')
        with self.db.connect() as con:
            con.execute('BEGIN IMMEDIATE');projects=self._projects(con,[] if project_ids is None else project_ids)
            if not con.execute("UPDATE document_sources SET recursive=?,exclude=?,revision=revision+1,status='pending',resume_status='pending',refresh_id=NULL,error=NULL WHERE id=? RETURNING id",(recursive,json.dumps(exclude),source_id)).fetchone():
                raise ValueError('文档来源不存在')
            con.execute('DELETE FROM document_source_projects WHERE source_id=?',(source_id,));con.executemany('INSERT INTO document_source_projects VALUES(?,?)',[(source_id,p) for p in projects])
            self._prune(con)
            return next(s for s in self._sources(con) if s['id']==source_id)

    def remove(self, source_id):
        with self.db.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            if not con.execute('DELETE FROM document_sources WHERE id=? RETURNING id',(source_id,)).fetchone():
                raise ValueError('文档来源不存在')
            self._prune(con)
        return {'removed':source_id,'message':'已取消此来源；独占材料退出检索/读取，原文件未改变'}

    def files(self, source_id=None):
        archive_id,key=references.material(self.db)
        with self.db.connect() as con:
            con.execute('BEGIN')
            if source_id is not None and not con.execute('SELECT 1 FROM document_sources WHERE id=?',(source_id,)).fetchone():
                raise ValueError('文档来源不存在')
            available={source['id']:source for source in self._sources(con) if source['status'] in {'ready','partial'}}
            qualified={}
            for member in con.execute("SELECT document_pk,source_id,qualification FROM document_memberships WHERE status='ready'"):
                source=available.get(member['source_id'])
                if source is not None:
                    qualified.setdefault(member['document_pk'],[]).append({'id':member['source_id'],'revision':source['revision'],'qualification':member['qualification']})
            rows=con.execute('SELECT d.pk,m.source_id,m.relative_path,m.status,m.qualification,m.error,d.id,d.path,d.version,d.sha256,d.text_length,d.captured_at,d.captured_by_source_id FROM document_memberships m JOIN documents d ON d.pk=m.document_pk'+(' WHERE m.source_id=?' if source_id else '')+' ORDER BY d.path,m.source_id', (source_id,) if source_id else ())
            result=[]
            for row in rows:
                item=dict(row);pk=item.pop('pk');item.update(self.snapshots.detail(con,pk))
                published=item.get('published_snapshot');stamps=sorted(qualified.get(pk,[]),key=lambda stamp:stamp['id'])
                item.update(original_reference=None,original_available=False)
                if published is not None and stamps and row['version']>0:
                    # Empty text has a valid original-info/download reference;
                    # publication and source qualifications, not FTS hits, are
                    # the authority. Never open an external source here.
                    payload={'format':1,'kind':'document','archive_id':archive_id,'document_id':row['id'],'version':row['version'],'sources':stamps,'start':0,'end':min(row['text_length'],2000),'processing_version':published['processing_version'],'result_sha256':published['result_sha256'],'raw_sha256':row['sha256']}
                    item.update(original_reference=sign(payload,key),original_available=True)
                elif stamps and row['version']>0:item['original_reason']='legacy_original_not_captured'
                else:item['original_reason']='no_current_snapshot'
                result.append(item)
            return result

    def reprocess(self,document_id,capture_id,expected_attempt_id,expected_version,expected_processing_version):
        token=self.snapshots.retry(document_id,capture_id,expected_attempt_id,expected_version,expected_processing_version)
        result=self.snapshots.process(token,token['profile']['format'])
        with self.db.connect() as con:
            con.execute('BEGIN IMMEDIATE');pk=token['document_pk']
            self.snapshots.publish(con,pk,token,result)
            doc=con.execute('SELECT * FROM documents WHERE pk=?',(pk,)).fetchone()
            version=doc['version']+int(doc['sha256']!=token['raw_sha256'])
            sequence=con.execute("UPDATE document_meta SET value=value+1 WHERE key='request_seq' RETURNING value").fetchone()[0]
            con.execute('UPDATE documents SET version=?,sha256=?,text=?,text_length=?,text_sha256=?,captured_at=?,publish_seq=? WHERE pk=?',(version,token['raw_sha256'],result['text'],len(result['text']),hashlib.sha256(result['text'].encode('utf-8')).hexdigest(),utcnow(),sequence,pk))
            con.execute('DELETE FROM document_fts WHERE rowid=?',(pk,));con.execute('INSERT INTO document_fts(rowid,text) VALUES(?,?)',(pk,' '.join(tokens(result['text']))))
            sources=[r[0] for r in con.execute('SELECT a.source_id FROM document_capture_authorizations a JOIN document_sources s ON s.id=a.source_id WHERE a.capture_id=? AND a.active=1 AND a.revision=s.revision',(capture_id,))]
            for sid in sources:
                con.execute("UPDATE document_memberships SET qualification=qualification+(status!='ready'),status='ready',error=NULL WHERE document_pk=? AND source_id=?",(pk,sid))
                failures=con.execute("SELECT count(*) FROM document_memberships WHERE source_id=? AND status!='ready'",(sid,)).fetchone()[0]
                status='partial' if failures else 'ready'
                con.execute('UPDATE document_sources SET status=?,resume_status=? WHERE id=?',(status,status,sid))
            detail=self.snapshots.detail(con,pk)
        return {'document_id':document_id,**detail}

    def _scan(self, source):
        root=Path(source['path']);counts={'ready':0,'failed':0,'candidates':0,'billed_bytes':0,'ignored_entries':0,'ignored_format':0,'ignored_excluded':0,'ignored_links':0}
        candidates=[];patterns=[(x.endswith('/'),_glob(x)) for x in source['exclude']]
        if _link(root):
            raise ValueError('来源根已变为链接或 junction')
        def candidate(path,relative):
            counts['candidates']+=1
            try:
                info=path.stat()
                if not stat.S_ISREG(info.st_mode):raise ValueError('候选不是常规文件')
                new=path.suffix.lower() in NEW_SUFFIXES;limit=20*MIB if new else FILE_LIMIT
                if info.st_size<=limit:
                    if new:counts['new_raw_bytes']=counts.get('new_raw_bytes',0)+info.st_size
                    else:counts['billed_bytes']+=info.st_size
                error=('文件超过20MiB' if new else '文件超过2MiB') if info.st_size>limit else None
            except (OSError,ValueError) as exc:info=None;error='stat失败: '+str(exc)
            candidates.append({'path':path,'relative_path':relative,'stat':info,'error':error})
        def walk(directory,prefix=''):
            with os.scandir(directory) as entries:
                for entry in entries:
                    path=Path(entry.path);relative=prefix+entry.name
                    if entry.name.startswith('.'):
                        counts['ignored_excluded']+=1;counts['ignored_entries']+=1;continue
                    if any(not isdir and rx.fullmatch(relative) for isdir,rx in patterns):
                        counts['ignored_excluded']+=1;counts['ignored_entries']+=1;continue
                    try:
                        if _link(path):counts['ignored_links']+=1;counts['ignored_entries']+=1;continue
                        directory_entry=entry.is_dir(follow_symlinks=False)
                        hidden=bool(getattr(entry.stat(follow_symlinks=False),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_HIDDEN',2))
                    except OSError as exc:
                        # A supported path whose metadata cannot be obtained is
                        # still one failed candidate, with no billable size.
                        if path.suffix.lower() not in SUFFIXES:raise
                        counts['candidates']+=1
                        candidates.append({'path':path,'relative_path':relative,'stat':None,'error':'stat失败: '+str(exc)})
                        continue
                    excluded=hidden or (directory_entry and entry.name in IGNORED_DIRS) or any(rx.fullmatch(relative) and (not isdir or directory_entry) for isdir,rx in patterns)
                    if excluded:counts['ignored_excluded']+=1;counts['ignored_entries']+=1;continue
                    if directory_entry:
                        if source['recursive']:walk(path,relative+'/')
                        else:counts['ignored_entries']+=1
                    elif path.suffix.lower() not in SUFFIXES:
                        counts['ignored_format']+=1;counts['ignored_entries']+=1
                    else:candidate(path,relative)
        try:
            if source['kind']=='file':candidate(root,root.name)
            else:walk(root)
        except OSError as exc:
            return {'error':'目录枚举失败: '+str(exc),'counts':counts,'files':[]}
        if counts['candidates']>CANDIDATE_LIMIT or counts['billed_bytes']>SOURCE_LIMIT or counts.get('new_raw_bytes',0)>128*MIB:
            return {'error':'来源超过1000候选或16MiB累计预算','counts':counts,'files':[]}
        for item in candidates:
            if item['error'] is None:
                try:
                    if item['path'].suffix.lower() in NEW_SUFFIXES:
                        raw=_read_raw(item['path'],item['stat'])
                        token=self.snapshots.capture(source,item['path'],raw,item['path'].suffix.lower()[1:])
                        result=self.snapshots.process(token,item['path'].suffix.lower()[1:])
                        item.update(snapshot_token=token,processed_result=result,sha256=token['raw_sha256'],text=result['text'])
                        from .document_results import encode
                        counts['processed_result_bytes']=counts.get('processed_result_bytes',0)+len(encode(result))
                    else:item['sha256'],item['text']=_read_file(item['path'],item['stat'])
                except (OSError,ValueError,RuntimeError) as exc:item['error']=str(exc)
            counts['failed' if item['error'] else 'ready']+=1
        if counts.get('processed_result_bytes',0)>128*MIB:return {'error':'来源完整处理结果超过128MiB','counts':counts,'files':[]}
        return {'error':None,'counts':counts,'files':candidates}

    def refresh(self, source_id=None):
        ids=[s['id'] for s in self.sources()] if source_id is None else [source_id]
        results=[]
        for ident in ids:
            with self.db.connect() as con:
                con.execute('BEGIN IMMEDIATE');source=next((s for s in self._sources(con) if s['id']==ident),None)
                if source is None:raise ValueError('文档来源不存在')
                sequence=con.execute("UPDATE document_meta SET value=value+1 WHERE key='request_seq' RETURNING value").fetchone()[0]
                source.update(refresh_id=uuid4().hex,request_seq=sequence)
                con.execute("UPDATE document_sources SET resume_status=CASE WHEN status='refreshing' THEN resume_status ELSE status END,status='refreshing',refresh_id=?,request_seq=?,started_at=? WHERE id=?",(source['refresh_id'],sequence,utcnow(),ident))
            try:scan=self._scan(source)
            except (OSError,ValueError) as exc:scan={'error':str(exc),'files':[],'counts':{'ready':0,'failed':0,'candidates':0,'billed_bytes':0,'ignored_entries':0}}
            results.append(self._publish(source,scan))
        return {'sources':results,'message':'仅明确刷新读取文件；失败原因见来源和文件状态'}

    def _publish(self, source, scan):
        with self.db.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            current=con.execute('SELECT * FROM document_sources WHERE id=?',(source['id'],)).fetchone()
            if current is None or current['revision']!=source['revision'] or current['refresh_id']!=source['refresh_id']:
                return {'id':source['id'],'published':False,'message':'旧刷新已被新配置、刷新或移除取代'}
            if scan['error']:
                con.execute('UPDATE document_capture_authorizations SET active=0 WHERE source_id=?',(source['id'],))
                con.execute("UPDATE document_memberships SET status='failed',error=? WHERE source_id=?",(scan['error'],source['id']))
                status='failed'
            else:
                seen=set()
                for item in scan['files']:
                    path=str(item['path']);key=os.path.normcase(path)
                    con.execute('INSERT OR IGNORE INTO documents(id,path_key,path) VALUES(?,?,?)',(uuid4().hex,key,path))
                    document=con.execute('SELECT * FROM documents WHERE path_key=?',(key,)).fetchone();pk=document['pk'];seen.add(pk)
                    old=con.execute('SELECT * FROM document_memberships WHERE source_id=? AND document_pk=?',(source['id'],pk)).fetchone()
                    qualification=1 if old is None else old['qualification']+(old['status']!='ready' and item['error'] is None)
                    error=item['error']
                    if not error and document['publish_seq']>source['request_seq'] and document['text'] is None:
                        error='较新文件快照已退出；请重新刷新，不能发布旧内容'
                        scan['counts']['ready']-=1;scan['counts']['failed']+=1
                    if not error and document['publish_seq']<=source['request_seq']:
                        if 'snapshot_token' in item:self.snapshots.publish(con,pk,item['snapshot_token'],item['processed_result'])
                        changed=document['sha256']!=item['sha256']
                        version=document['version']+int(changed)
                        # Re-reading identical bytes preserves content version;
                        # capture metadata still records this successful collection.
                        captured=utcnow();collector=source['id']
                        con.execute('UPDATE documents SET version=?,sha256=?,text=?,text_length=?,captured_at=?,captured_by_source_id=?,publish_seq=? WHERE pk=?', (version,item['sha256'],item['text'],len(item['text']),captured,collector,source['request_seq'],pk))
                        con.execute('UPDATE documents SET text_sha256=? WHERE pk=?',(hashlib.sha256(item['text'].encode('utf-8')).hexdigest(),pk))
                        con.execute('DELETE FROM document_fts WHERE rowid=?',(pk,));con.execute('INSERT INTO document_fts(rowid,text) VALUES(?,?)',(pk,' '.join(tokens(item['text']))))
                    con.execute('INSERT INTO document_memberships VALUES(?,?,?,?,?,?) ON CONFLICT(source_id,document_pk) DO UPDATE SET relative_path=excluded.relative_path,status=excluded.status,qualification=excluded.qualification,error=excluded.error',(source['id'],pk,item['relative_path'],'failed' if error else 'ready',qualification,error))
                for row in con.execute('SELECT document_pk FROM document_memberships WHERE source_id=?',(source['id'],)).fetchall():
                    if row[0] not in seen:con.execute("UPDATE document_memberships SET status='missing',error='本轮未在来源范围发现' WHERE source_id=? AND document_pk=?",(source['id'],row[0]))
                status='partial' if scan['counts']['failed'] else 'ready'
            con.execute('UPDATE document_sources SET status=?,resume_status=?,finished_at=?,error=?,counts=? WHERE id=?',(status,status,utcnow(),scan['error'],json.dumps(scan['counts']),source['id']))
            self._prune(con)
            return next(s for s in self._sources(con) if s['id']==source['id'])

    def search(self, query, *, scope='all', project_id=None, limit=5, exact_project_ids=None):
        if not isinstance(query,str) or not (terms:=list(dict.fromkeys(tokens(query)))):
            raise ValueError('查询词不能为空，须有可检索的中英文内容')
        if type(limit) is not int or not 1<=limit<=50:
            raise ValueError('limit须为1至50整数')
        identity,key=references.material(self.db)
        with self.db.connect() as con:
            con.execute('BEGIN')
            if exact_project_ids is None:projects=_query_scope(con,scope,project_id)
            else:
                projects=self._projects(con,list(exact_project_ids))
            sources=[s for s in self._sources(con) if projects is None or set(s['project_ids']).intersection(projects)]
            available={s['id']:s for s in sources if s['status'] in {'ready','partial'}}
            qualified={}
            for row in con.execute("SELECT * FROM document_memberships WHERE status='ready'"):
                if row['source_id'] in available:
                    qualified.setdefault(row['document_pk'],[]).append({'id':row['source_id'],'revision':available[row['source_id']]['revision'],'qualification':row['qualification']})
            match=' OR '.join('"'+term.replace('"','')+'"' for term in terms)
            results=[]
            rows=con.execute('SELECT d.*,bm25(document_fts) AS score FROM document_fts JOIN documents d ON d.pk=document_fts.rowid WHERE document_fts MATCH ? ORDER BY score,d.path_key,d.id',(match,))
            for row in rows:
                stamps=sorted(qualified.get(row['pk'],[]),key=lambda x:x['id'])
                if not stamps or row['text'] is None:continue
                text=row['text']
                lower=text.lower();positions=[p for t in terms if (p:=lower.find(t))>=0]
                point=min(positions,default=0)
                # Keep the tokenizer's lower() semantics, mapping expanded
                # Unicode offsets (e.g. İ -> i + dot) to original codepoints.
                if len(lower)!=len(text):
                    offset=0
                    for index,char in enumerate(text):
                        width=len(char.lower())
                        if offset+width>point:
                            point=index;break
                        offset+=width
                start=max(0,point-200);end=min(len(text),start+2000)
                payload={'format':1,'kind':'document','archive_id':identity,'document_id':row['id'],'version':row['version'],'sources':stamps,'start':start,'end':end}
                result={k:row[k] for k in ['id','path','version','sha256','text_sha256','text_length','captured_at','captured_by_source_id']}
                result['display_name']=self._display_name(con,row['id'],row['path'])
                metadata,processed=self.snapshots.metadata(con,row['pk'])
                if processed is not None:
                    result.update(metadata)
                    payload.update(processing_version=metadata['processing_version'],result_sha256=metadata['result_sha256'],raw_sha256=row['sha256'])
                    from .document_results import hit_context
                    context,anchor,preview=hit_context(processed,point)
                    if context is not None:
                        result['table_context']=context
                        start=max(0,point-min(200,preview//4));end=min(len(text),start+preview)
                        payload.update(table_anchor=anchor,start=start,end=end)
                results.append({**result,**_range(text,start,end),'source_ids':[s['id'] for s in stamps],
                                'project_ids':sorted({p for stamp in stamps for p in available[stamp['id']]['project_ids']}),
                                'reference':sign(payload,key),'bm25_score':-row['score'],'rank':len(results)+1,'snapshot_kind':'采集版本（仅本机）'})
                if len(results)>=limit:break
            indexed=con.execute("SELECT pk FROM documents WHERE text IS NOT NULL").fetchall()
            return {'results':results,'scope':scope,'effective_project_ids':projects,'archive_scope':'local_documents',
                    'coverage':{'indexed_files':sum(r[0] in qualified for r in indexed),'sources':sources}}

    @staticmethod
    def _display_name(con,ident,path):
        if con.execute("SELECT 1 FROM sqlite_master WHERE name='document_library'").fetchone():
            row=con.execute('SELECT display_name FROM document_library WHERE document_id=?',(ident,)).fetchone()
            if row:return row[0]
        return Path(path).name

    def read(self, reference, *, start=None, end=None, view='text',table_id=None,row_start=None,row_end=None,column_start=None,column_end=None,_raw=False):
        if view not in {'text','table','original-info'}:raise ValueError('不支持的文档读取模式')
        if view!='text' and (start is not None or end is not None):raise ValueError('表格/原件信息与文本范围互斥')
        if view!='table' and any(x is not None for x in (table_id,row_start,row_end,column_start,column_end)):raise ValueError('表格参数须与table视图一起使用')
        payload=references.decode(self.db,reference)
        from .document_protocol import identity,integer
        if type(payload.get('format')) is not int:raise ValueError('文档引用格式无效')
        identity(payload.get('document_id'),'文档引用身份');integer(payload.get('version'),'文档引用版本')
        if not isinstance(payload.get('sources'),list):raise ValueError('来源资格无效')
        for stamp in payload['sources']:
            if not isinstance(stamp,dict):raise ValueError('来源资格无效')
            identity(stamp.get('id'),'来源身份');integer(stamp.get('revision'),'来源版本');integer(stamp.get('qualification'),'来源资格')
        if payload.get('kind')!='document':
            raise ValueError('须使用文档搜索返回的原文引用，不能混用对话引用')
        with self.db.connect() as con:
            con.execute('BEGIN')
            row=con.execute('SELECT * FROM documents WHERE id=?',(payload.get('document_id'),)).fetchone()
            if row is None or row['text'] is None or row['version']!=payload.get('version') or hashlib.sha256(row['text'].encode('utf-8')).hexdigest()!=row['text_sha256'] or len(row['text'])!=row['text_length']:
                raise ValueError('采集版本已失效，请重新检索')
            valid=[]
            for stamp in payload.get('sources',[]):
                member=con.execute('SELECT m.status,m.qualification,s.revision,s.status AS source_status FROM document_memberships m JOIN document_sources s ON s.id=m.source_id WHERE m.document_pk=? AND m.source_id=?',(row['pk'],stamp['id'])).fetchone()
                if member and member['status']=='ready' and member['source_status'] in {'ready','partial'} and member['qualification']==stamp['qualification'] and member['revision']==stamp['revision']:
                    valid.append(stamp['id'])
            if not valid:raise ValueError('当次来源资格已失效或正在刷新，请稍后重新检索')
            result={k:row[k] for k in ['id','path','version','sha256','text_sha256','text_length','captured_at','captured_by_source_id']}
            result['display_name']=self._display_name(con,row['id'],row['path'])
            metadata,processed=self.snapshots.metadata(con,row['pk'])
            if processed is not None:
                if payload.get('processing_version')!=metadata['processing_version'] or payload.get('result_sha256')!=metadata['result_sha256'] or payload.get('raw_sha256')!=row['sha256']:raise ValueError('处理快照已失效，请重新检索')
                result.update(metadata)
            if _raw:return self.snapshots.original(con,row['pk'])
            if view=='original-info':
                state,_=self.snapshots.result(con,row['pk'])
                return {**{k:v for k,v in result.items() if k not in {'locations','tables','coverage'}},'available':state is not None,'bytes':state['raw_bytes'] if state else None,'reason':None if state else 'legacy_original_not_captured','source_ids':valid}
            if view=='table':
                if processed is None:raise ValueError('旧文本没有表格结构')
                from .document_results import table_view
                return {**{k:v for k,v in result.items() if k not in {'locations','tables'}},**table_view(processed,table_id,row_start=row_start,row_end=row_end,column_start=column_start,column_end=column_end,anchor=payload.get('table_anchor')),'source_ids':valid}
            return {**result,**_range(row['text'],payload['start'] if start is None else start,payload['end'] if end is None else end),
                    'source_ids':valid,'snapshot_kind':'采集版本（仅本机）'}

    def original(self,reference):
        return self.read(reference,_raw=True)

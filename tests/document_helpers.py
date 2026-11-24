"""Independent synthetic document fixtures and public API observations."""
import builtins
import io
import itertools
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
from smm_local.api import create_app
from smm_local.core import Archive

ROOT = Path(__file__).resolve().parents[1]
MIB = 1024 * 1024
OBSERVATIONS = itertools.count(1)


def observe(name, value):
    if folder := os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        out = Path(folder); out.mkdir(parents=True, exist_ok=True)
        safe = ''.join(c if c.isalnum() or c in '-_.' else '_' for c in name)
        (out / (f'{next(OBSERVATIONS):05d}-' + safe + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def fingerprint(path):
    raw = path.read_bytes(); s = path.stat()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'mtime_ns': s.st_mtime_ns}


def normal(text):
    return text.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n')


class Fixture:
    def __init__(self, root, db=None):
        self.root = root; root.mkdir(parents=True, exist_ok=True)
        self.db = db or Archive(root / 'archive.sqlite3')
        if db is None:
            empty = root / 'empty-agent'; empty.mkdir(exist_ok=True)
            self.db.set_settings(codex_root=str(empty), claude_root=str(empty))
        self.client = TestClient(create_app(self.db, auto_sync=False, sync_on_start=False))
        self.calls = 0

    def request(self, method, path, body=None, status=200):
        response = self.client.request(method, path, json=body) if body is not None else self.client.request(method, path)
        self.calls += 1
        observe(f'api-{self.calls:03d}', {'method': method, 'path': path, 'request': body, 'expected_status': status,
                                        'status': response.status_code, 'response': response.json()})
        assert response.status_code == status, response.text
        return response.json()

    def bad(self, method, path, body=None):
        r = self.client.request(method, path, json=body) if body is not None else self.client.request(method, path)
        observe(f'rejected-{self.calls:03d}', {'path': path, 'status': r.status_code, 'response': r.json()}); self.calls += 1
        assert 400 <= r.status_code < 500, r.text
        return r

    def project(self, name='P', kind='ordinary'):
        # Existing project storage is setup, not the new project-create assertion.
        with self.db.connect() as c:
            p = c.execute('INSERT INTO projects(name,kind,confirmed) VALUES(?,?,1) RETURNING id', (name, kind)).fetchone()[0]
        self.db.projects()
        return p

    def file(self, name, text='needle original', raw=None):
        p = self.root / 'docs' / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw if raw is not None else text.encode('utf-8'))
        return p

    def add(self, path, projects=(), **kwargs):
        return self.request('POST', '/api/documents/sources', {'path': str(path), 'project_ids': list(projects), **kwargs})

    def set(self, source, **kwargs):
        return self.request('PUT', '/api/documents/sources/' + source['id'], kwargs)

    def sources(self):
        return self.request('GET', '/api/documents/sources')

    def source(self, source):
        return next(s for s in self.sources() if s['id'] == source['id'])

    def refresh(self, source=None):
        return self.request('POST', '/api/documents/refresh', {'source_id': source['id'] if source else None})

    def files(self, source=None):
        suffix = '?source_id=' + source['id'] if source else ''
        return self.request('GET', '/api/documents/files' + suffix)

    def search(self, query='needle', **kwargs):
        return self.request('POST', '/api/documents/search', {'query': query, **kwargs})

    def read(self, hit, **kwargs):
        reference = hit if isinstance(hit, str) else hit['reference']
        return self.request('POST', '/api/documents/read', {'reference': reference, **kwargs})

    def remove(self, source):
        return self.request('DELETE', '/api/documents/sources/' + source['id'])

    def texts(self, response):
        return {Path(h['path']).name: self.read(h)['text'] for h in response['results']}

    def cli(self, *args, code=0):
        env = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=str(ROOT / 'src'))
        p = subprocess.run([sys.executable, '-B', '-m', 'smm_local.cli', '--db', str(self.db.db_path), *map(str, args)],
                           cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', timeout=60)
        observe(f'cli-{self.calls:03d}', {'argv': list(args), 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}); self.calls += 1
        assert p.returncode == code, p.stderr
        return json.loads(p.stdout) if code == 0 else p


def deny_source_reads(monkeypatch, *paths):
    protected = {os.path.normcase(str(Path(p).resolve())) for p in paths};attempts=[]
    def guard(original):
        def wrapped(file, *args, **kwargs):
            if isinstance(file, (str, Path)) and os.path.normcase(str(Path(file).resolve())) in protected:
                attempts.append(str(file))
                raise AssertionError('document source body unexpectedly opened outside explicit refresh')
            return original(file, *args, **kwargs)
        return wrapped
    for module, name in [(builtins, 'open'), (io, 'open'), (os, 'open')]:
        monkeypatch.setattr(module, name, guard(getattr(module, name)))
    return attempts


def names(f,query='needle',project=None):
    args={'scope':'project','project_id':project} if project else {}
    return {Path(h['path']).name:h for h in f.search(query,limit=50,**args)['results']}



def seed_conversation(f, text='conversationnonce original'):
    root=f.root/'agent-fixture';root.mkdir(exist_ok=True)
    path=root/'session.jsonl'
    records=[{'timestamp':'2026-11-22T00:00:00Z','type':'session_meta','payload':{'id':'documents-compat-session','cwd':str(f.root/'conversation-project')}},
             {'timestamp':'2026-11-22T00:00:01Z','type':'response_item','payload':{'type':'message','role':'user','content':[{'type':'input_text','text':text}]}}]
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    f.db.sync_codex(root)
    from smm_local.federation import search_archive
    hit=search_archive(f.db,'conversationnonce',local=True)['results'][0]
    return hit


def document_state(f):
    with f.db.connect() as c:
        names=['document_sources','document_source_projects','documents','document_memberships','document_meta']
        tables={n:[dict(row) for row in c.execute('SELECT * FROM '+n+' ORDER BY 1,2')] for n in names}
        tables['fts']=[tuple(row) for row in c.execute('SELECT rowid,text FROM document_fts ORDER BY rowid')]
    return tables

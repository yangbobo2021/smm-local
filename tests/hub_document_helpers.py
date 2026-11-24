"""Independent synthetic inputs and public HTTP observations for 007."""
from __future__ import annotations
import base64
import hashlib
import json
import sys
import io
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from document_helpers import Fixture, observe, normal, document_state
from smm_local import federation, references
from smm_hub.projects import HubProjects


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class World:
    def __init__(self, pair, tmp_path):
        self.pair=pair; self.root=tmp_path; self.local=Fixture(tmp_path/'client',db=pair.local)
        federation.configure_hub(pair.local,'http://localhost:18770','synthetic-007',str(pair.token_file))
        self.config=federation.hub_config(pair.local)
        self.hub=pair.client; self.calls=pair.calls
        self.device=self.config['device_id']; self.archive=references.material(pair.local)[0]
        self.counter=0;self.controls={}

    def remote(self, method, path, body=None, status=200):
        self.counter+=1
        r=self.hub.request(method,'/v1'+path,json=body) if body is not None else self.hub.request(method,'/v1'+path)
        observe('hub-'+str(self.counter),{'method':method,'path':path,'request':body,'status':r.status_code,'response':r.json(),'expected':status})
        assert r.status_code==status,r.text
        return r.json()

    def reject_remote(self,method,path,body=None):
        r=self.hub.request(method,'/v1'+path,json=body) if body is not None else self.hub.request(method,'/v1'+path)
        observe('hub-rejected',{'path':path,'request':body,'status':r.status_code,'response':r.json()})
        assert 400<=r.status_code<500,r.text
        return r

    def context(self):
        i=self.remote('GET','/info')
        assert 'document_epoch' in i,'Hub must expose document context after authentication'
        return {'hub_id':i['hub_id'],'document_epoch':i['document_epoch']}

    def project(self,name='P'):
        return self.local.project(name)

    def status(self):
        return self.local.request('GET','/api/documents/sync-status')

    def policy(self,project,enabled=True):
        s=self.status();p=next(p for p in s['projects'] if p['project_id']==project)
        return self.local.request('POST','/api/documents/sync-policy',{'project_key':p['project_key'],'enabled':enabled,'expected_hub_id':s['hub_id'],'expected_generation':p['generation']})

    def sync(self):
        return self.local.request('POST','/api/documents/sync',{})

    def cli(self,*args,code=0):
        from smm_local.cli import main
        stdout,stderr=io.StringIO(),io.StringIO();result=0
        with patch.object(sys,'argv',['smm','--db',str(self.pair.local.db_path),*map(str,args)]),redirect_stdout(stdout),redirect_stderr(stderr):
            try:main()
            except SystemExit as exc:result=exc.code or 0
        observe('in-process-cli',{'argv':args,'exit':result,'stdout':stdout.getvalue(),'stderr':stderr.getvalue()})
        assert result==code,stderr.getvalue()
        return json.loads(stdout.getvalue()) if code==0 else {'exit':result,'error':stderr.getvalue()}

    @staticmethod
    def disk(root):
        root=Path(root)
        return {str(p.relative_to(root)):{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in root.rglob('*')
                if p.is_file() and not p.is_symlink() and '.documents' in str(p.relative_to(root)) and not p.name.endswith('.lock')}

    def hub_project_for(self,project):
        key=federation._remote_project_key(self.pair.local,project)
        return next(p for p in HubProjects(self.pair.remote).list() if p['source']=='device' and p['owner']==self.device and p['source_key']==key)

    def source(self,name,text,projects):
        path=self.local.file(name,text);s=self.local.add(path,projects);self.local.refresh(s)
        return path,s

    def hub_project(self,name='Hub P',kind='ordinary'):
        return self.remote('POST','/projects',{**self.context(),'name':name,'kind':kind})

    def project_context(self,p):
        return {**self.context(),'project_id':p['id'],'project_key':p['source_key']}

    def upload(self,p,name,text=None,raw=None,submission=None,hub=False):
        body={'project_id':p['id'] if isinstance(p,dict) else p,'name':name,
              'content_base64':base64.b64encode(raw if raw is not None else text.encode()).decode(),
              'submission_id':submission or uuid4().hex}
        if hub:body.update(self.project_context(p));return self.remote('POST','/documents/library',body)
        return self.local.request('POST','/api/documents/library',body)

    def search_hub(self,q='needle',**kw):
        return self.remote('POST','/documents/search',{**self.context(),'query':q,**kw})

    def read_hub(self,hit,**kw):
        return self.remote('POST','/documents/read',{**self.context(),'reference':hit['reference'],**kw})

    def docs(self,result,hub=False):
        return {h['id']:(self.read_hub(h) if hub else self.local.read(h))['text'] for h in result['results']}

    def protocol(self,project_key=None,generation=1):
        return {**self.context(),'device_id':self.device,'archive_id':self.archive,
                'project_key':project_key or 'a'*32,'generation':generation}

    def control(self,p=None,**kw):
        p=p or self.protocol();reply=self.remote('POST','/documents/control',{**p,'project_name':'Device P','enabled':True,'sequence':1,'retained':[],**kw})
        self.controls[(p['device_id'],p['archive_id'],p['project_key'])]=reply['sequence']
        return reply

    def doc(self,text='needle original',ident=None,version=1):
        raw=text.encode();normalized=normal(text);ident=ident or uuid4().hex;name='中文 file '+ident+'.txt'
        return {'document_id':ident,'version':version,'sha256':sha(raw),'text_sha256':sha(normalized.encode()),'text':normalized,'text_length':len(normalized),'capture_sequence':version,
                'path':'/origin/'+name,'display_name':name,'captured_at':'2026-11-23T00:00:00Z','captured_by_source_id':'b'*32}

    def stage(self,p,d):
        return self.remote('POST','/documents/stage',{**p,'document':d})

    def manifest(self,p,documents,source_id=None,sequence=1,revision=1,submission=None):
        return {**p,'control_sequence':self.controls.get((p['device_id'],p['archive_id'],p['project_key']),1),'source_id':source_id or 'b'*32,'revision':revision,'sequence':sequence,'submission_id':submission or uuid4().hex,
                'files':[{k:d[k] for k in ('document_id','version','sha256','text_sha256','path','display_name','captured_at','captured_by_source_id','capture_sequence')}|{'relative_path':d['display_name'],'qualification':1} for d in documents]}

    def publish(self,m):
        return self.remote('POST','/documents/publish',m)

    def snapshot(self):
        with self.pair.remote.connect() as c:
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name LIKE '%document%' OR name IN ('projects','hub_projects'))") if not r[0].startswith('sqlite_')]
            return {n:[dict(r) for r in c.execute('SELECT * FROM "'+n+'" ORDER BY 1')] for n in names}


def assert_text(read,text,start=0,end=None):
    text=normal(text);end=len(text) if end is None else end
    assert read['text']==text[start:end]
    assert (read['start'],read['end'])==(start,end)
    assert read['start_line']==1+text.count('\n',0,start)
    assert read['end_line']==1+text.count('\n',0,end-1)

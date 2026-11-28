"""Actual isolated Hub, sending creator and empty querying creator."""
from contextlib import contextmanager
import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
from document_helpers import ROOT,observe
from document_formats_platform import utf8_environment
from document_formats_cli_observer import HOOK
from test_document_formats_management import native_input
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server


class RemoteWorld:
    def __init__(self,root,monkeypatch,formats):
        self.root=root;root.mkdir();self.monkeypatch=monkeypatch;self.formats=formats;self.items=[]
        for name in ('SMM_008_PUBLICATION_GATE','SMM_008_WEB_PROCESSING_GATE','SMM_008_WEB_READ_ONLY','SMM_008_RESTART_PAUSE'):monkeypatch.delenv(name,raising=False)
        self.hub=Server(root/'hub','hub');self.sender=Server(root/'sender','local');self.reader=Server(root/'reader','local');self.servers=[self.hub,self.sender,self.reader]
        self.hub.db=self.hub.root/'smm-hub.sqlite3';self.stopped_sender=False
        self.readonly=root/'readonly.jsonl';self.protected=[];self.readonly_before=b''
        self.query_log=root/'service-query.jsonl';self.query_before=b'';self.service_audits={}
        for server in self.servers:
            (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\nfrom document_formats_remote_observer import install\ninstall()\n',encoding='utf-8')
            (server.root/'query-allowed').write_bytes(b'allowed query control')
    def save(self,name,value):keep('remote/'+name,json.dumps(value,ensure_ascii=False,indent=2).encode())
    def cli(self,server,*args,env=None,reject=False):
        argv=[sys.executable,'-B','-m','smm_local.cli','--db',str(server.db),'documents',*map(str,args)]
        p=subprocess.run(argv,cwd=server.root,env=env or utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'tests'),str(ROOT/'src')])) ,capture_output=True,timeout=45)
        tag=uuid4().hex;keep('remote/cli/'+tag+'.stdout',p.stdout);keep('remote/cli/'+tag+'.stderr',p.stderr)
        observe('remote-cli',{'command':argv,'exit':p.returncode,'stdout_file':'remote/cli/'+tag+'.stdout','stderr_file':'remote/cli/'+tag+'.stderr'})
        assert p.returncode!=0 if reject else p.returncode==0,p.stderr
        return p if reject else json.loads(p.stdout)
    def projects(self,server):
        if server.owner=='hub':return [server.call('POST','/projects',{**server.context,'name':'remote '+kind,'kind':kind}).json() for kind in ('ordinary','global')]
        return [server.call('POST','/projects',{'name':'remote ordinary'}).json(),server.call('POST','/projects/global').json()]
    def send(self,server,project,raw,format,key):
        begin=server.call('POST','/documents/uploads',{**server.context,'project_id':project['id'],'project_key':project['source_key'] if server.owner=='hub' else project['stable_key'],'submission_id':key,'name':'same.'+format,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}).json()
        for index,offset in enumerate(range(0,len(raw),begin['block_bytes'])):
            part=raw[offset:offset+begin['block_bytes']];server.call('PUT','/documents/uploads/'+begin['upload_id']+'/parts/'+str(index),raw=part,headers={'X-Chunk-SHA256':hashlib.sha256(part).hexdigest()})
        return server.call('POST','/documents/uploads/'+begin['upload_id']+'/commit',server.context).json()
    def settled(self,server,count):
        until=time.monotonic()+90
        while True:
            rows=server.call('GET','/documents/files').json()
            if len(rows)==count and all(r.get('published_snapshot') is not None and r['latest_attempt']['status']=='ready' and r['published_snapshot']['capture_id']==r['latest_attempt']['capture_id'] for r in rows):return rows
            assert time.monotonic()<until,{'phase':'real creator did not publish','rows':rows}
            time.sleep(.05)
    def prepare(self):
        from smm_local.core import Archive
        from smm_local import federation,references
        from smm_local.document_sync import DocumentSync
        for server in self.servers:server.start()
        self.sender_db=Archive(self.sender.db);self.reader_db=Archive(self.reader.db);self.hub_db=Archive(self.hub.db)
        for origin,server in [('hub',self.hub),('device',self.sender)]:
            projects=self.projects(server)
            for group,project in enumerate(projects):
                for format in self.formats:
                    for index in (1,2):
                        key='remote'+origin+str(group)+format+str(index);raw,truth=native_input(format,key);keep('remote/inputs/'+key+'.'+format,raw);self.save('truth/'+key+'.json',truth)
                        receipt=self.send(server,project,raw,format,key);self.items.append({'kind':origin,'server':server,'project':project,'raw':raw,'truth':truth,'format':format,'key':key,'query':truth['words'][0].split()[0],'source_document_id':receipt['document_id'],'receipt':receipt,'sha256':hashlib.sha256(raw).hexdigest()})
            rows=self.settled(server,len(projects)*len(self.formats)*2)
            for item in self.items:
                if item['server'] is not server:continue
                row=next(r for r in rows if r['id']==item['source_document_id']);assert row['sha256']==item['sha256'] and row['version']==row['processing_version']==1
                item['path']=Path(row['path']);self.protected.append(item['path'])
        token=self.root/'hub-token';token.write_text(self.hub.token,encoding='ascii')
        for db,name in [(self.sender_db,'synthetic sender'),(self.reader_db,'synthetic reader')]:
            connected=federation.configure_hub(db,'http://127.0.0.1:'+str(self.hub.port),name,str(token));assert connected['connected'] is True
        sender_identity=references.material(self.sender_db)[0];sender_device=federation.hub_config(self.sender_db)['device_id'];hub_archive=references.material(self.hub_db)[0]
        sync=DocumentSync(self.sender_db);status=sync.status();pids={i['project']['id'] for i in self.items if i['kind']=='device'}
        for p in status['projects']:
            if p['project_id'] in pids:sync.choose(p['project_key'],True,status['hub_id'],p['generation'])
        self.save('sync-result.json',sync.sync());assert not sync.status()['pending'] and not sync.status()['conflict']
        rows=self.hub.call('GET','/documents/files').json();assert len(rows)==len({r['id'] for r in rows})==len(self.items)
        for item in self.items:
            item['origin']={'device_id':self.hub.context['hub_id'] if item['kind']=='hub' else sender_device,'archive_id':hub_archive if item['kind']=='hub' else sender_identity,'document_id':item['source_document_id']}
            matches=[r for r in rows if r['origin']==item['origin']];assert len(matches)==1 and matches[0]['sha256']==item['sha256'] and matches[0]['version']==matches[0]['processing_version']==1
            item['hub_id']=matches[0]['id'];item['hub_ref']=matches[0]['original_reference'];item['hub_project_ids']=matches[0]['project_ids']
            raw=self.hub.call('POST','/documents/original',{**self.hub.context,'reference':item['hub_ref']}).content;assert raw==item['raw']
        assert self.reader.call('GET','/documents/files').json()==[]
        stopped=self.sender.stop();assert stopped['forced'] is False;self.stopped_sender=True
        for path in self.protected:path.unlink()
    def freeze_query_services(self):
        # Only the controller may have parsed during explicit preparation.
        for server in (self.reader,self.hub):
            stopped=server.stop();assert stopped['forced'] is False
        self.monkeypatch.setenv('SMM_008_WEB_READ_ONLY',str(self.readonly))
        self.monkeypatch.setenv('SMM_008_REMOTE_QUERY','1')
        self.monkeypatch.setenv('SMM_008_REMOTE_QUERY_LOG',str(self.query_log))
        old_port=self.hub.port;self.hub.start(deny=self.protected)
        # Each restart uses a new test port; reconfigure using the public client.
        from smm_local import federation
        token=self.root/'hub-token'
        for db,name in [(self.reader_db,'synthetic reader'),(self.sender_db,'synthetic sender')]:
            assert federation.configure_hub(db,'http://127.0.0.1:'+str(self.hub.port),name,str(token))['connected']
        self.reader.start(deny=self.protected)
        for server in (self.hub,self.reader):
            self.enroll_query_server(server)
        self.readonly_before=self.readonly.read_bytes();keep('remote/readonly-controls.jsonl',self.readonly_before)
    def enroll_query_server(self,server):
        response=server.client.post('/__test_processing_probe');self.save(server.root.name+'-readonly-controls.json',{'status':response.status_code,'body':response.json()});assert response.status_code==200 and set(response.json()['blocked'])=={'processing','subprocess'}
        response=server.client.post('/__test_remote_query_probe');self.save(server.root.name+'-query-controls.json',{'status':response.status_code,'body':response.json()});assert response.status_code==200 and set(response.json()['blocked'])=={'source','resolve','connect'}
        expected={'internal_socketpair','allowed_file'}|({'configured_hub'} if server.owner=='local' else set());assert set(response.json()['positive'])==expected
        events=server.events();assert len(events)==1 and events[0]['event']=='open'
        self.service_audits[server]=server.log.read_bytes()
        self.query_before=self.query_log.read_bytes();self.readonly_before=self.readonly.read_bytes()
        keep('remote/controls/'+server.root.name+'-service-source.jsonl',self.service_audits[server]);keep('remote/controls/'+server.root.name+'-service-network.jsonl',self.query_before)
    def query_environment(self,server=None):
        server=server or self.reader;folder=self.root/('query-observer-'+server.owner+'-'+server.root.name);folder.mkdir();log=folder/'events.jsonl'
        code=HOOK.replace("if event=='socket.getaddrinfo':reason='network'","if event=='socket.getaddrinfo' and not (args[0]=='127.0.0.1' and str(args[1])==os.environ['SMM_008_QUERY_HUB_PORT']):reason='network'")
        code=code.replace("if event=='socket.connect' and not internal_socketpair(sys._getframe(1),args[0],args[1]):reason='network'","if event=='socket.connect' and not internal_socketpair(sys._getframe(1),args[0],args[1]) and not (isinstance(args[1],tuple) and args[1][:2]==('127.0.0.1',int(os.environ['SMM_008_QUERY_HUB_PORT']))):reason='network'")
        shutil.copyfile(ROOT/'tests/document_formats_platform.py',folder/'document_formats_platform.py');(folder/'sitecustomize.py').write_text(code,encoding='utf-8')
        env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(folder),str(ROOT/'src')]),SMM_008_CLI_SOURCES=json.dumps(list(map(str,self.protected))),SMM_008_CLI_OBSERVER=str(log),SMM_008_QUERY_HUB_PORT=str(self.hub.port))
        positive=subprocess.run([sys.executable,'-B','-c',"import socket,sys;s=socket.create_connection(('127.0.0.1',int(sys.argv[1])));s.close()",str(self.hub.port)],env=env,capture_output=True,timeout=10);assert positive.returncode==0,positive.stderr
        negatives=[("open",[sys.executable,'-B','-c','from pathlib import Path;import sys;Path(sys.argv[1]).read_bytes()',str(self.protected[0])]),('import',[sys.executable,'-B','-c','import pdfplumber']),('spawn',[sys.executable,'-B','-c','import subprocess,sys;subprocess.run([sys.executable,"-c","raise SystemExit(0)"])']),('network',[sys.executable,'-B','-c',"import socket;socket.socket().connect(('192.0.2.1',9))"])]
        for name,argv in negatives:
            p=subprocess.run(argv,env=env,capture_output=True,timeout=10);keep('remote/controls/'+server.root.name+'-'+name+'.stderr',p.stderr);assert p.returncode!=0 and b'CLI read observer forbidden' in p.stderr
        before=log.read_bytes();keep('remote/controls/'+server.root.name+'-events.jsonl',before);self.save('controls/'+server.root.name+'.json',{'positive_exit':positive.returncode,'negative_cases':[n for n,_ in negatives],'events':[json.loads(x) for x in before.splitlines()]})
        return env,log,before
    def query_unchanged(self,log,before):
        assert log.read_bytes()==before
        assert self.readonly.read_bytes()==self.readonly_before
        assert self.query_log.read_bytes()==self.query_before
        assert all(server.log.read_bytes()==baseline for server,baseline in self.service_audits.items())
        assert all(not p.exists() for p in self.protected)
    def close(self):
        original=sys.exception();errors=[]
        for server in reversed(self.servers):
            try:server.stop()
            except BaseException as exc:errors.append(str(exc))
        if errors:
            self.save('cleanup-errors.json',errors)
            if original is None:raise AssertionError(errors)


@contextmanager
def remote_world(tmp_path,monkeypatch,formats=('docx','xlsx','pdf')):
    world=RemoteWorld(tmp_path/'world',monkeypatch,formats)
    try:
        world.prepare();yield world
    finally:world.close()

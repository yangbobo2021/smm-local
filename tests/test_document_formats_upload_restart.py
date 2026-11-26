"""Real creator process restart, persisted chunks/jobs and saved-byte publication."""
import hashlib,json,os,signal,socket,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
import httpx,psutil,pytest
from document_helpers import observe,ROOT
from document_formats_upload_fixture import upload_input
from test_document_formats_retry import keep
from document_formats_platform import path_key,utf8_environment,process_identity,spawn_identity,same_existing_path,matching_process,process_tree,refresh_owned_records,verify_server,terminate_verified,diagnostics_on_failure,preserve_diagnostics


def test_restart_source_audit_has_actual_positive_and_negative_controls(tmp_path):
    protected=tmp_path/'forbidden';protected.write_text('do not read')
    allowed=tmp_path/'allowed';allowed.write_text('can read')
    hooks=tmp_path/'hooks';hooks.mkdir();(hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\n')
    log=tmp_path/'audit.jsonl'
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_RESTART_DENY=json.dumps([str(protected)]),SMM_008_RESTART_AUDIT=str(log))
    positive=subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;assert Path(sys.argv[1]).read_text()=="can read"',str(allowed)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    negative=subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;Path(sys.argv[1]).read_text()',str(protected)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert positive.returncode==0 and negative.returncode!=0 and 'restart source read denied' in negative.stderr
    events=[json.loads(line) for line in log.read_text().splitlines()]
    assert len(events)==1 and events[0]['path']==path_key(protected) and events[0]['event']=='open'
    observe('restart-source-audit-control',{'positive':positive.returncode,'negative':negative.returncode,'events':events})


class Server:
    def __init__(self,root,owner):
        self.root=root;root.mkdir();self.owner=owner;self.db=root/'archive.sqlite3';self.token='008-synthetic-'+uuid4().hex
        self.hooks=root/'hooks';self.hooks.mkdir();(self.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\n',encoding='utf-8')
        self.number=0;self.process=None;self.client=None;self.handles=[];self.serving_stamp=None;self.known_tree=[]
    @diagnostics_on_failure
    def start(self,*,pause=False,deny=()):
        self.start_failed=False
        try:
            assert self.process is None,'stop the previous task server first'
            return self._start(pause=pause,deny=deny)
        except BaseException:
            self.start_failed=True
            raise
    def _start(self,*,pause=False,deny=()):
        self.number+=1;tag=str(self.number);self.log=self.root/('audit-'+tag+'.jsonl');self.pause=self.root/('pause-'+tag+'.jsonl');self.nonce=uuid4().hex;self.serving_stamp=None;self.known_tree=[]
        with socket.socket() as port:port.bind(('127.0.0.1',0));self.port=port.getsockname()[1]
        env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(self.hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_TEST_DB=str(self.db),SMM_008_TEST_OWNER=self.owner,SMM_008_TEST_TOKEN=self.token,SMM_008_TEST_NONCE=self.nonce,SMM_008_RESTART_DENY=json.dumps(list(map(str,deny))),SMM_008_RESTART_AUDIT=str(self.log))
        env.pop('SMM_008_RESTART_PAUSE',None)
        if pause:env['SMM_008_RESTART_PAUSE']=str(self.pause)
        self.stdout=self.root/('server-'+tag+'.stdout');self.stderr=self.root/('server-'+tag+'.stderr')
        outs=self.stdout.open('wb');errors=self.stderr.open('wb');self.handles=[outs,errors]
        self.argv=[sys.executable,'-B','-m','document_formats_restart_server','--port',str(self.port)]
        self.process=subprocess.Popen(self.argv,env=env,cwd=self.root,stdout=outs,stderr=errors,start_new_session=os.name!='nt')
        self.bootstrap_stamp=spawn_identity(psutil.Process(self.process.pid));self.launcher_stamp=self.bootstrap_stamp;self.created=self.bootstrap_stamp['created']
        self.allowed_executables={path_key(p) for p in (sys.executable,getattr(sys,'_base_executable',sys.executable),psutil.Process().exe())}
        packet={'bootstrap':self.bootstrap_stamp,'requested_argv':self.argv,'http_identity':None,'expected_archive':str(self.db),'expected_cwd':str(self.root),'expected_owner':self.owner,'expected_nonce':self.nonce,'permitted_executables':sorted(self.allowed_executables)}
        identity_path=self.root/('identity-'+tag+'.json')
        identity_path.write_text(json.dumps(packet,ensure_ascii=False),encoding='utf-8')
        observe('restart-server-spawn',packet)
        self.client=httpx.Client(base_url='http://127.0.0.1:'+str(self.port),headers={'Authorization':'Bearer '+self.token} if self.owner=='hub' else {},timeout=10,trust_env=False)
        until=time.monotonic()+20
        while True:
            assert self.process.poll() is None,self.stderr.read_text(encoding='utf-8')
            try:
                identity=self.client.get('/__test_identity')
                if identity.status_code==200:break
            except httpx.TransportError:pass
            assert time.monotonic()<until,'isolated service did not start'
            time.sleep(.03)
        packet.update(http_status=identity.status_code,http_identity=identity.json())
        try:packet['current_tree']=process_tree(self.bootstrap_stamp)
        except Exception as error:packet['current_tree_error']=str(error)
        identity_path.write_text(json.dumps(packet,ensure_ascii=False),encoding='utf-8')
        observe('restart-server-before-enrollment',packet)
        self.serving_stamp=verify_server(self.bootstrap_stamp,identity.json(),argv=self.argv,archive=self.db,owner=self.owner,nonce=self.nonce,cwd=self.root,executables=self.allowed_executables)
        self.launcher_stamp=process_identity(psutil.Process(self.process.pid))
        self.known_tree=packet.get('current_tree',[])
        self.serving_pid=self.serving_stamp['pid'];self.actual_argv=self.serving_stamp['argv'];self.actual_exe=self.serving_stamp['exe']
        self.prefix='/api' if self.owner=='local' else '/v1'
        self.context={} if self.owner=='local' else {k:self.call('GET','/info').json()[k] for k in ('hub_id','document_epoch')}
        observe('restart-server-start',{'argv':self.argv,'launcher':self.launcher_stamp,'serving':self.serving_stamp,'identity':identity.json(),'stage':self.number})
    def call(self,method,path,body=None,*,raw=None,headers=None):
        args={'headers':headers or {}}
        if body is not None:args['json']=body
        if raw is not None:args['content']=raw
        response=self.client.request(method,self.prefix+path,**args)
        value=response.json() if 'json' in response.headers.get('content-type','') else {'bytes':len(response.content),'sha256':hashlib.sha256(response.content).hexdigest()}
        observe('restart-http',{'owner':self.owner,'stage':self.number,'method':method,'path':path,'body':body,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'status':response.status_code,'response':value})
        assert response.status_code==200,response.text
        return response
    @diagnostics_on_failure
    def stop(self):
        original=sys.exception()
        try:return self._stop()
        except BaseException as error:
            # A failed cleanup cannot replace a startup or test-body exception.
            value={'status':'incomplete','error':str(error),'original_error':str(original) if original is not None else None,'bootstrap':getattr(self,'bootstrap_stamp',None),'launcher':getattr(self,'launcher_stamp',None),'serving':self.serving_stamp}
            try:
                (self.root/'cleanup-incomplete.json').write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
                observe('restart-server-cleanup-incomplete',value)
                preserve_diagnostics(self.root,'failed-cleanup-'+str(self.number))
            except Exception as diagnostic_error:
                value['diagnostic_error']=str(diagnostic_error)
                try:sys.stderr.write('restart cleanup incomplete: '+json.dumps(value,ensure_ascii=False)+'\n')
                except Exception:pass
            if original is None and not getattr(self,'start_failed',False):raise
            return value
    def _stop(self):
        if self.process is None:return
        process=self.process;forced=False
        known={(item['pid'],item['created']):item for item in self.known_tree+self._owned_tree()}
        if self.serving_stamp is not None:known[(self.serving_stamp['pid'],self.serving_stamp['created'])]=self.serving_stamp
        members=list(known.values())
        if self.serving_stamp is not None and matching_process(self.serving_stamp) is not None:
            response=self.client.post('/__test_shutdown',headers={'X-SMM-Test-Nonce':self.nonce})
            assert response.status_code==200,response.text
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            forced=True
            known={(item['pid'],item['created']):item for item in members+self._owned_tree()}
            members=refresh_owned_records(list(known.values()),self.allowed_executables)
            terminate_verified(members,owner=process)
        remaining=refresh_owned_records(members,self.allowed_executables)
        if remaining:
            forced=True;terminate_verified(remaining,owner=process)
        assert not refresh_owned_records(members,self.allowed_executables)
        if self.client is not None:self.client.close()
        for handle in self.handles:handle.close()
        evidence={'owner':self.owner,'stage':self.number,'pid':self.serving_stamp['pid'] if self.serving_stamp else None,'launcher':self.launcher_stamp,'serving':self.serving_stamp,'members':members,'exit':process.returncode,'forced':forced,'stdout':self.stdout.read_text(encoding='utf-8'),'stderr':self.stderr.read_text(encoding='utf-8'),'audit':self.events(),'pause_events':[json.loads(line) for line in self.pause.read_text(encoding='utf-8').splitlines()] if self.pause.exists() else []}
        observe('restart-server-stop',evidence)
        with httpx.Client(timeout=.2,trust_env=False) as check:
            with pytest.raises(httpx.TransportError):check.get('http://127.0.0.1:'+str(self.port)+'/__test_identity')
        self.process=None
        return evidence
    def _owned_tree(self):
        members=process_tree(self.bootstrap_stamp)
        if members:
            launcher=members[0]
            assert launcher['argv'][1:]==self.argv[1:]
            assert any(same_existing_path(launcher['exe'],p) for p in self.allowed_executables)
            actual=matching_process(launcher);assert actual is not None and same_existing_path(actual.cwd(),self.root)
        return members
    def events(self):return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()] if self.log.exists() else []


@pytest.mark.parametrize('owner',['local','hub'])
def test_isolated_http_server_factory_and_cleanup(tmp_path,owner):
    server=Server(tmp_path/owner,owner)
    try:
        server.start()
        assert server.call('GET','/documents/files').json()==[]
        stopped=server.stop();assert stopped['forced'] is False and stopped['audit']==[]
    finally:server.stop()


@pytest.mark.parametrize('owner',['local','hub'])
def test_real_creator_restart_resumes_chunks_and_pending_captures(tmp_path,owner):
    # TC-008-managed-upload-restart: two distinct applicable targets per creator.
    server=Server(tmp_path/owner,owner);items=[]
    try:
        server.start()
        if owner=='local':
            projects=[server.call('POST','/projects',{'name':'restart ordinary'}).json(),server.call('POST','/projects/global').json()]
        else:
            projects=[server.call('POST','/projects',{**server.context,'name':'restart '+kind,'kind':kind}).json() for kind in ('ordinary','global')]
        for key,project in zip(('alpha','beta'),projects):
            label=owner+'restart'+key;raw,truth=upload_input('docx',label)
            keep('inputs/'+label+'.docx',raw);keep('truth/'+label+'.json',json.dumps(truth,ensure_ascii=False).encode())
            body={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if owner=='local' else project['source_key'],'submission_id':label,'name':'same.docx','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            start=server.call('POST','/documents/uploads',body).json();size=start['block_bytes'];assert len(raw)>size and start['received_parts']==[]
            chunk=raw[:size];part=server.call('PUT','/documents/uploads/'+start['upload_id']+'/parts/0',raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()}).json()
            assert part['received_parts']==[0]
            items.append({'raw':raw,'truth':truth,'body':body,'upload':start['upload_id'],'size':size,'project':project,'label':label})
        assert server.call('GET','/documents/files').json()==[]
        stopped=server.stop();assert stopped['forced'] is False and stopped['audit']==[]
        server.start(pause=True)
        for item in items:
            start=server.call('POST','/documents/uploads',item['body']).json()
            assert start['upload_id']==item['upload'] and start['received_parts']==[0] and start['block_bytes']==item['size']
            for index,offset in enumerate(range(item['size'],len(item['raw']),item['size']),1):
                chunk=item['raw'][offset:offset+item['size']]
                server.call('PUT','/documents/uploads/'+item['upload']+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
            item['receipt']=server.call('POST','/documents/uploads/'+item['upload']+'/commit',server.context).json()
        listed=server.call('GET','/documents/files').json();assert len(listed)==2
        assert len({item['receipt']['document_id'] for item in items})==2
        for item in items:
            row=next(row for row in listed if row['id']==item['receipt']['document_id'])
            assert row['published_snapshot'] is None and row['version']==row['processing_version']==0
            assert row['latest_attempt']['status']=='pending' and row['latest_attempt']['attempt_id']==item['receipt']['attempt_id'] and row['latest_attempt']['capture_id']==item['receipt']['capture_id']
            assert row['original_reference'] is None and row['original_available'] is False
            item['path']=Path(row['path'])
        stopped=server.stop();assert stopped['pause_events'] and stopped['audit']==[]
        for item in items:item['path'].unlink()
        server.start(deny=[item['path'] for item in items])
        until=time.monotonic()+45
        while True:
            listed=server.call('GET','/documents/files').json()
            if len(listed)==2 and all((row.get('latest_attempt') or {}).get('status')=='failed' or (row.get('published_snapshot') is not None and (row.get('latest_attempt') or {}).get('status') in {'ready','partial'} and row['published_snapshot']['capture_id']==row['latest_attempt']['capture_id']) for row in listed):break
            assert time.monotonic()<until,{'phase':'captured jobs did not resume after actual process restart','files':listed}
            time.sleep(.1)
        def verify_all(phase):
            listed=server.call('GET','/documents/files').json()
            assert {row['id'] for row in listed}=={item['receipt']['document_id'] for item in items}
            for item in items:
                ident=item['receipt']['document_id'];entry=next(row for row in listed if row['id']==ident)
                assert entry['version']==entry['processing_version']==1 and entry['published_snapshot']['status']=='ready'
                assert entry['latest_attempt']['attempt_id']==item['receipt']['attempt_id'] and entry['latest_attempt']['capture_id']==item['receipt']['capture_id']
                assert entry['latest_attempt']['status']=='ready' and entry['latest_attempt']['finished_at'] and entry['latest_attempt']['error'] is None
                hits=server.call('POST','/documents/search',{**server.context,'query':item['label'],'scope':'project','project_id':item['project']['id'],**({'local':True} if owner=='local' else {})}).json()['results']
                assert len(hits)==1 and hits[0]['id']==ident and hits[0]['version']==hits[0]['processing_version']==1
                hit=hits[0];assert hit['sha256']==hashlib.sha256(item['raw']).hexdigest()
                reference=item.setdefault('reference',hit['reference'])
                read=server.call('POST','/documents/read',{**server.context,'reference':reference,'start':0,'end':hit['text_length']}).json()
                assert read['id']==ident and all(word in read['text'] for word in item['truth']['words']) and all(word not in read['text'] for word in item['truth']['excluded'])
                assert len(read['tables'])==len(item['truth']['tables'])
                for expected in item['truth']['tables']:
                    table=next(t for t in read['tables'] if all(t['location'].get(k)==v for k,v in expected['location'].items()))
                    view=server.call('POST','/documents/read',{**server.context,'reference':reference,'view':'table','table_id':table['table_id'],'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1}).json()
                    actual=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
                    assert (view['rows'],view['columns'])==(expected['rows'],expected['columns']) and len(actual)==len(expected['cells']) and set(actual)==set(expected['cells'])
                response=server.call('POST','/documents/original',{**server.context,'reference':reference})
                keep('downloads/'+phase+'-'+item['label']+'.docx',response.content);assert response.content==item['raw']
                receipt=server.call('POST','/documents/uploads/'+item['upload']+'/commit',server.context).json()
                assert all(receipt[k]==item['receipt'][k] for k in ('document_id','capture_id','attempt_id')) and receipt['status']=='ready'
            assert len(server.call('GET','/documents/library').json())==2
            assert not any(event['event']=='open' for event in server.events())
        verify_all('resumed')
        stopped=server.stop();assert len([e for e in stopped['audit'] if e['event']=='subprocess.Popen'])==2
        server.start(deny=[item['path'] for item in items]);verify_all('stable-restart')
        stopped=server.stop();assert stopped['forced'] is False and stopped['audit']==[]
    finally:server.stop()

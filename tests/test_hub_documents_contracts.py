"""007 public contracts: no real documents, services or remote credentials."""
from __future__ import annotations
import base64
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Event, Thread
from uuid import uuid4
from zipfile import ZipFile
import pytest
from fastapi.testclient import TestClient
from test_005_contracts import add_local, connect, seed_remote
from types import SimpleNamespace
from document_helpers import Fixture, normal, document_state, deny_source_reads, observe, ROOT, seed_conversation
from hub_document_helpers import World, assert_text, sha
from smm_local import federation, references
from smm_local.documents import Documents, FILE_LIMIT, SOURCE_LIMIT
from smm_local.core import Archive
from smm_hub.hub import create_hub
from smm_hub.projects import HubProjects


@pytest.fixture
def w(tmp_path,monkeypatch):
    local=Archive(tmp_path/'local.sqlite3');remote=Archive(tmp_path/'hub-state'/'smm-hub.sqlite3')
    existing=local.create_project('Existing before Hub')
    histories=tmp_path/'histories';histories.mkdir();empty=tmp_path/'empty';empty.mkdir()
    local.set_settings(codex_root=str(histories),claude_root=str(empty))
    token='synthetic-007-'+('a'*40);token_file=tmp_path/'token';token_file.write_text(token)
    calls=[]
    with TestClient(create_hub(remote,token),headers={'Authorization':'Bearer '+token}) as client:
        def request(config,route,payload=None):
            calls.append((route,json.loads(json.dumps(payload))))
            r=client.get('/v1'+route) if payload is None else client.post('/v1'+route,json=payload)
            if r.status_code>=400:
                error=federation.HubUnavailable(str(r.json()));error.status=r.status_code;raise error
            return r.json()
        monkeypatch.setattr(federation,'_request',request)
        pair=SimpleNamespace(local=local,remote=remote,client=client,histories=histories,token_file=token_file,calls=calls,hub_id=client.get('/v1/info').json()['hub_id'])
        yield World(pair,tmp_path)


# @case-id: TC-007-policy-choice
def test_policy_choice(w,monkeypatch):
    existing=next(x['id'] for x in w.pair.local.projects() if x['name']=='Existing before Hub')
    p,q,waiting=w.project('P'),w.project('Q'),w.project('Pending')
    path,shared=w.source('shared.txt','needle shared private',[p,q])
    _,old_source=w.source('existing.txt','needle existing private',[existing])
    w.source('unbound.txt','needle unbound hidden',[])
    w.local.add(w.local.file('pending.txt','needle pending'),[waiting])
    conversation=add_local(w.pair,'dialogue-choice','Dialogue P','dialoguenonce separate')
    states=w.status();assert len(states['projects'])==5
    assert {x['project_id'] for x in states['projects']}=={existing,p,q,waiting,conversation['project_id']}
    assert all(x['enabled'] is False and x['generation']==0 for x in states['projects'])
    forbidden=[]
    with w.pair.local.connect() as c:
        forbidden=[str(value) for row in c.execute('SELECT id,path,sha256,text FROM documents') for value in row if value]
        forbidden += [Path(r[0]).name for r in c.execute('SELECT path FROM documents')]
        forbidden += [r[0] for r in c.execute('SELECT id FROM document_sources')]
    for mode in ['none','only','all']:
        federation.choose_upload(w.pair.local,mode,[conversation['project_id']] if mode=='only' else [])
        for paused in [False,True]:
            w.pair.local.set_settings(sync_paused=paused);marker=len(w.calls);w.sync()
            assert all(not x['enabled'] for x in w.status()['projects'])
            assert w.search_hub()['results']==[]
            wire=json.dumps(w.calls[marker:]);assert not any(value in wire for value in forbidden)
    w.pair.local.set_settings(sync_paused=False);dialogue_before=federation.upload_status(w.pair.local)
    # Actual public CLI parser/entry, with values obtained from displayed status.
    for project in [p,existing]:
        state=w.status();entry=next(x for x in state['projects'] if x['project_id']==project)
        w.cli('documents','sync-policy',entry['project_key'],'--enabled','yes','--expected-hub-id',state['hub_id'],'--expected-generation',entry['generation'])
    w.cli('documents','sync');assert federation.upload_status(w.pair.local)==dialogue_before
    result=w.search_hub(limit=50);bytext=w.docs(result,True);assert set(bytext.values())=={'needle shared private','needle existing private'}
    pp=w.hub_project_for(p);qq=w.hub_project_for(q)
    hit=next(h for h in result['results'] if w.read_hub(h)['text']=='needle shared private')
    assert hit['project_ids']==[pp['id']] and qq['id'] not in hit['project_ids']
    before=w.status();old=next(x for x in states['projects'] if x['project_id']==p)
    current=next(x for x in before['projects'] if x['project_id']==p)
    for key,hid,g in [(old['project_key'],states['hub_id'],0),(current['project_key'],'f'*32,current['generation']),('f'*32,before['hub_id'],0)]:
        w.local.bad('POST','/api/documents/sync-policy',{'project_key':key,'expected_hub_id':hid,'expected_generation':g,'enabled':False});assert w.status()==before
    w.source('later.txt','needle future P',[p]);w.sync();assert set(w.docs(w.search_hub(limit=50),True).values())=={'needle shared private','needle existing private','needle future P'}
    w.pair.local.rename_project(p,'Renamed P');assert next(x for x in w.status()['projects'] if x['project_id']==p)['enabled']
    # Two concurrent submissions use the SAME displayed generation; only one wins.
    snapshot=w.status();entry=next(x for x in snapshot['projects'] if x['project_id']==q)
    gate=Event();answers=[]
    def choose(enabled):
        assert gate.wait(10);r=w.local.client.post('/api/documents/sync-policy',json={'project_key':entry['project_key'],'enabled':enabled,'expected_hub_id':snapshot['hub_id'],'expected_generation':entry['generation']});answers.append((enabled,r.status_code))
    threads=[Thread(target=choose,args=(enabled,)) for enabled in [False,True]]
    for t in threads:t.start()
    gate.set()
    for t in threads:t.join(15);assert not t.is_alive()
    assert sorted(code==200 for _,code in answers)==[False,True]
    winner=next(enabled for enabled,code in answers if code==200);saved=next(x for x in w.status()['projects'] if x['project_id']==q)
    assert saved['enabled']==winner and saved['generation']==entry['generation']+1
    # Offline explicit choice is durable but its confirmation must remain pending.
    original=federation._request
    def offline(*a,**kw):raise federation.HubUnavailable('synthetic offline')
    monkeypatch.setattr(federation,'_request',offline);w.policy(existing,False)
    offline_state=w.status();entry=next(x for x in offline_state['projects'] if x['project_id']==existing)
    assert not entry['enabled'] and entry['generation']>entry['confirmed_generation'] and offline_state['pending']
    w.local=Fixture(w.root/'restart',db=Archive(w.pair.local.db_path));assert w.status()==offline_state
    monkeypatch.setattr(federation,'_request',original);w.sync();assert not next(x for x in w.status()['projects'] if x['project_id']==existing)['enabled']
    # Real H1 -> H2 switch, with equal generation. The old displayed HID must fail.
    old_status=w.status();old_entry=next(x for x in old_status['projects'] if x['project_id']==p)
    second_db=Archive(w.root/'second-hub'/'smm-hub.sqlite3')
    with TestClient(create_hub(second_db,'b'*48),headers={'Authorization':'Bearer '+('b'*48)}) as second:
        def dispatch(config,route,payload=None):
            if config['address'].rstrip('/').endswith(':18771'):
                r=second.get('/v1'+route) if payload is None else second.post('/v1'+route,json=payload)
                if r.status_code>=400:raise federation.HubUnavailable(r.text)
                return r.json()
            return original(config,route,payload)
        monkeypatch.setattr(federation,'_request',dispatch)
        federation.configure_hub(w.pair.local,'http://localhost:18771','synthetic-007',str(w.pair.token_file))
        new_status=w.status();assert new_status['hub_id']!=old_status['hub_id'] and all(not x['enabled'] for x in new_status['projects'])
        while next(x for x in w.status()['projects'] if x['project_id']==p)['generation']<old_entry['generation']:w.policy(p,True)
        new_status=w.status();new_entry=next(x for x in new_status['projects'] if x['project_id']==p);assert new_entry['generation']==old_entry['generation']
        w.local.bad('POST','/api/documents/sync-policy',{'project_key':old_entry['project_key'],'enabled':False,'expected_hub_id':old_status['hub_id'],'expected_generation':old_entry['generation']});assert w.status()==new_status
        federation.configure_hub(w.pair.local,'http://localhost:18770','synthetic-007',str(w.pair.token_file))
    monkeypatch.setattr(federation,'_request',original)
    assert next(x for x in w.status()['projects'] if x['project_id']==p)['enabled']
    # An unverified target cannot borrow a prior Hub's authorization.
    monkeypatch.setattr(federation,'_request',offline)
    federation.configure_hub(w.pair.local,'http://localhost:18772','synthetic-007',str(w.pair.token_file))
    unverified=w.status();assert not unverified['hub_id']
    w.local.bad('POST','/api/documents/sync-policy',{'project_key':old_entry['project_key'],'enabled':True,'expected_hub_id':old_status['hub_id'],'expected_generation':old_entry['generation']})
    monkeypatch.setattr(federation,'_request',original);federation.configure_hub(w.pair.local,'http://localhost:18770','synthetic-007',str(w.pair.token_file))
    # Numeric ID reuse is distinct; merges preserve the TARGET's own choice.
    orphan=w.project('orphan');key=federation._remote_project_key(w.pair.local,orphan)
    with w.pair.local.connect() as c:c.execute('DELETE FROM projects WHERE id=?',(orphan,));c.execute('INSERT INTO projects(id,name) VALUES(?,?)',(orphan,'new identity'))
    fresh=w.status();new=next(x for x in fresh['projects'] if x['project_id']==orphan);assert new['project_key']!=key and not new['enabled']
    w.local.bad('POST','/api/documents/sync-policy',{'project_key':key,'enabled':True,'expected_hub_id':fresh['hub_id'],'expected_generation':0});assert w.status()==fresh
    for target_enabled in [False,True]:
        src,dst=w.project('merge source'),w.project('merge target');_,source=w.source('merge-'+str(target_enabled)+'.txt','mergenonce '+str(target_enabled),[src]);w.policy(src)
        if target_enabled:w.policy(dst)
        source_key=federation._remote_project_key(w.pair.local,src);w.pair.local.merge_projects(src,dst);w.sync()
        after=w.status();target=next(x for x in after['projects'] if x['project_id']==dst);assert target['enabled']==target_enabled
        remote=w.search_hub(query='mergenonce',limit=50)
        assert all(source_key not in {x['project_key'] for x in h['provenance']} for h in remote['results'])
        scoped=w.search_hub(query='mergenonce',scope='project',project_id=w.hub_project_for(dst)['id'])
        assert list(w.docs(scoped,True).values())==(['mergenonce True'] if target_enabled else [])


# @case-id: TC-007-sync-publication
def test_sync_publication(w):
    from smm_local.archive_protocol import sign
    p=w.protocol();w.control(p)
    docs=[w.doc('needle S'+str(i)+' F'+str(j)+'\r\n中文😀',version=2 if j==1 else 1) for i in [1,2] for j in [1,2]]
    source_ids=['b'*32,'c'*32];source_for={}
    for index,doc in enumerate(docs):doc['captured_by_source_id']=source_ids[index//2];source_for[doc['document_id']]=source_ids[index//2]
    project=next(x for x in HubProjects(w.pair.remote).list() if x['source_key']==p['project_key'])
    def verify(expected):
        hits=w.search_hub(limit=50)['results'];assert {h['origin']['document_id'] for h in hits}=={d['document_id'] for d in expected}
        byid={h['origin']['document_id']:h for h in hits}
        for d in expected:
            h=byid[d['document_id']];assert_text(w.read_hub(h),d['text'])
            assert h['sha256']==d['sha256'] and h['text_sha256']==d['text_sha256'] and h['text_length']==len(d['text'])
            assert h['version']==d['version'] and h['captured_at']==d['captured_at'] and h['received_at']
            assert h['project_ids']==[project['id']]
            assert h['origin']=={'device_id':w.device,'archive_id':w.archive,'document_id':d['document_id']}
            assert {x['source_id'] for x in h['provenance']}=={source_for[d['document_id']]}
            assert h['captured_by_source_id']==d['captured_by_source_id']
        return byid
    published=[]
    for i,sid in enumerate(source_ids):
        pair=docs[i*2:i*2+2]
        # Begin with a real qualified V1 of the SAME file/source. Its citation
        # provides all authentic routing/qualification fields for the staged V2.
        old=w.doc('needle old source '+str(i),ident=pair[0]['document_id'],version=1);old['captured_by_source_id']=sid
        w.stage(p,old);w.publish(w.manifest(p,[old],source_id=sid,sequence=1));published.append(old)
        old_hit=verify(published)[old['document_id']]
        w.stage(p,pair[0]);m=w.manifest(p,pair,source_id=sid,sequence=2)
        before=w.snapshot();w.reject_remote('POST','/documents/publish',m);assert w.snapshot()==before
        verify(published) # V1 is still visible, V2 and the new sibling are not.
        # Validly signed future-version citation; no malformed nested placeholder.
        # The IDENTICAL reference must succeed after complete publication below.
        outer=references.routing_metadata(old_hit['reference']);inner=references.routing_metadata(outer['reference'])
        inner.update(version=pair[0]['version'],start=0,end=min(2000,len(pair[0]['text'])))
        for packet in [inner,outer]:
            for key in ['version','sha256','text_sha256','text_length']:
                if key in packet:packet[key]=pair[0][key]
        key=references.material(w.pair.remote)[1];outer['reference']=sign(inner,key);future=sign(outer,key)
        w.reject_remote('POST','/documents/read',{**w.context(),'reference':future})
        corrupt={**pair[1],'text_sha256':'f'*64};before=w.snapshot();w.reject_remote('POST','/documents/stage',{**p,'document':corrupt});assert w.snapshot()==before
        w.stage(p,pair[1]);verify(published)
        bad=deepcopy(m);bad['files'].append({**bad['files'][0],'document_id':'f'*32})
        before=w.snapshot();w.reject_remote('POST','/documents/publish',bad);assert w.snapshot()==before
        w.publish(m);published=[d for d in published if d['document_id']!=old['document_id']]+pair;verify(published)
        actual=w.remote('POST','/documents/read',{**w.context(),'reference':future});assert_text(actual,pair[0]['text'])


# @case-id: TC-007-sync-retry
def test_sync_retry(w,monkeypatch,tmp_path):
    import socket,time
    from urllib.request import Request,urlopen
    project=w.project();pa,s1=w.source('one.txt','retrynonce first',[project]);pb,s2=w.source('two.txt','retrynonce second',[project])
    original=federation._request;lost={'once':False}
    def drop(config,route,payload=None):
        result=original(config,route,payload)
        if route=='/documents/publish' and not lost['once']:
            lost['once']=True;raise federation.HubUnavailable('lost accepted receipt')
        return result
    monkeypatch.setattr(federation,'_request',drop);w.policy(project);w.sync();assert lost['once']
    monkeypatch.setattr(federation,'_request',original);w.sync()
    expected={w.local.files(s1)[0]['id']:'retrynonce first',w.local.files(s2)[0]['id']:'retrynonce second'}
    first=w.search_hub(query='retrynonce',limit=50)
    assert len(first['results'])==2 and {h['origin']['document_id'] for h in first['results']}==set(expected)
    for h in first['results']:assert_text(w.read_hub(h),expected[h['origin']['document_id']])
    w.local=Fixture(w.root/'restart',db=Archive(w.pair.local.db_path));w.sync();w.sync()
    with TestClient(create_hub(Archive(w.pair.remote.db_path),w.pair.token_file.read_text()),headers={'Authorization':'Bearer '+w.pair.token_file.read_text()}) as rebuilt:
        again=rebuilt.post('/v1/documents/search',json={**w.context(),'query':'retrynonce','limit':50});assert again.status_code==200
        assert {(h['origin']['document_id'],h['version']) for h in again.json()['results']}=={(doc,1) for doc in expected}
        for h in first['results']:
            r=rebuilt.post('/v1/documents/read',json={**w.context(),'reference':h['reference']});assert r.status_code==200;assert_text(r.json(),expected[h['origin']['document_id']])
    # One source keeps failing before acceptance, but another still publishes.
    pa.write_text('retrynonce first V2');pb.write_text('retrynonce second V2');Documents(w.pair.local).refresh()
    def fail_one(config,route,payload=None):
        if route=='/documents/publish' and payload.get('source_id')==s1['id']:raise federation.HubUnavailable('persistent first source failure')
        return original(config,route,payload)
    monkeypatch.setattr(federation,'_request',fail_one);out=w.sync();assert out['pending'] and out['errors']
    hits=w.search_hub(query='retrynonce',limit=50)['results'];byid={h['origin']['document_id']:h for h in hits}
    assert_text(w.read_hub(byid[w.local.files(s1)[0]['id']]),'retrynonce first')
    assert_text(w.read_hub(byid[w.local.files(s2)[0]['id']]),'retrynonce second V2')
    monkeypatch.setattr(federation,'_request',original);w.sync()
    assert set(w.docs(w.search_hub(query='retrynonce',limit=50),True).values())=={'retrynonce first V2','retrynonce second V2'}
    # Actual Hub child process crashes after durable staging, before manifest.
    context=w.protocol('d'*32);w.control(context);a,b=w.doc('processprobe first'),w.doc('processprobe second')
    manifest=w.manifest(context,[a,b],source_id='d'*32)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    token=w.pair.token_file.read_text();url='http://127.0.0.1:'+str(port)
    def http(route,payload=None):
        body=None if payload is None else json.dumps(payload).encode()
        req=Request(url+'/v1'+route,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urlopen(req,timeout=10) as response:return json.loads(response.read())
    def start(label):
        log=tmp_path/(label+'.log');stream=log.open('wb')
        argv=[sys.executable,'-m','smm_hub.cli','--db',str(w.pair.remote.db_path),'serve-hub','--token-file',str(w.pair.token_file),'--port',str(port)]
        child=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            assert child.poll() is None,log.read_text(errors='replace')
            try:
                if http('/info')['hub_id']==context['hub_id']:return child,stream,log,argv
            except OSError:pass
            time.sleep(.05)
        child.kill();child.wait();stream.close();raise AssertionError('isolated Hub did not start')
    child,stream,log,argv=start('interrupted-hub')
    try:
        stage=http('/documents/stage',{**context,'document':a});assert http('/documents/stage',{**context,'document':a})==stage
        assert http('/documents/search',{**w.context(),'query':'processprobe'})['results']==[]
    finally:
        child.kill();child.wait(timeout=10);stream.close();observe('actual-interrupted-hub',{'argv':argv,'pid':child.pid,'exit':child.returncode,'expected':'explicit forced interruption after staging','log':log.read_text(errors='replace')})
    child,stream,log,argv=start('resumed-hub')
    try:
        assert http('/documents/stage',{**context,'document':a})==stage
        http('/documents/stage',{**context,'document':b});receipt=http('/documents/publish',manifest)
        assert http('/documents/publish',manifest)==receipt
        hits=http('/documents/search',{**w.context(),'query':'processprobe','limit':50})['results'];assert len(hits)==2
        expected_process={a['document_id']:a['text'],b['document_id']:b['text']}
        assert {h['origin']['document_id'] for h in hits}==set(expected_process)
        for h in hits:assert_text(http('/documents/read',{**w.context(),'reference':h['reference']}),expected_process[h['origin']['document_id']])
        changed=deepcopy(manifest);changed['files'][0]['relative_path']='different.txt';before=w.snapshot();w.reject_remote('POST','/documents/publish',changed);assert w.snapshot()==before
    finally:
        child.terminate();child.wait(timeout=10);stream.close();observe('actual-resumed-hub',{'argv':argv,'pid':child.pid,'exit':child.returncode,'log':log.read_text(errors='replace')})
    from scripts.acceptance.hub_documents_checks import stopped
    stopped([child.pid],[('127.0.0.1',port)])


# @case-id: TC-007-sync-boundaries
def test_sync_boundaries(w):
    p=w.protocol();w.control(p)
    exact=w.doc('needle '+('x'*(FILE_LIMIT-7)));assert len(exact['text'].encode())==FILE_LIMIT
    w.stage(p,exact);w.publish(w.manifest(p,[exact]))
    h=w.search_hub()['results'][0];assert h['text_length']==FILE_LIMIT and h['text_sha256']==sha(exact['text'].encode())
    for start in range(0,FILE_LIMIT,16000):assert_text(w.read_hub(h,start=start,end=min(FILE_LIMIT,start+16000)),exact['text'],start,min(FILE_LIMIT,start+16000))
    over=w.doc('needle '+('x'*(FILE_LIMIT-6)))
    # All hashes and lengths match the oversized body. Only the size differs.
    assert len(over['text'].encode())==FILE_LIMIT+1
    before=w.snapshot();w.reject_remote('POST','/documents/stage',{**p,'document':over});assert w.snapshot()==before
    small=w.doc('needle legitimate small body')
    for field,value in [('text_length',True),('version',True),('document_id',True),('sha256','bad'),('text_sha256','a'*64),('text_length',-1)]:
        before=w.snapshot();w.reject_remote('POST','/documents/stage',{**p,'document':{**small,field:value}});assert w.snapshot()==before
    body=json.dumps({**p,'document':small}).encode();body+=b' '*(SOURCE_LIMIT-len(body))
    r=w.hub.post('/v1/documents/stage',content=body,headers={'Content-Type':'application/json'});assert r.status_code==200,r.text
    before=w.snapshot();r=w.hub.post('/v1/documents/stage',content=body+b' ',headers={'Content-Type':'application/json'});assert r.status_code==413 and w.snapshot()==before
    m=w.manifest(p,[small],source_id='c'*32);w.publish(m)
    got=next(x for x in w.search_hub(limit=50)['results'] if x['origin']['document_id']==small['document_id']);assert_text(w.read_hub(got),small['text'])
    for files in [[{'document_id':'unknown'}],[{**m['files'][0],'qualification':True}],[m['files'][0],{**m['files'][0],'qualification':2}],[{**m['files'][0],'sha256':'a'*64}]]:
        bad=w.manifest(p,[],source_id='c'*32,sequence=2);bad['files']=files;before=w.snapshot();w.reject_remote('POST','/documents/publish',bad);assert w.snapshot()==before
    observe('boundary-witness',{'text_bytes':FILE_LIMIT,'text_sha256':exact['text_sha256'],'over_text_bytes':len(over['text'].encode()),'request_bytes':len(body),'request_sha256':sha(body),'over_request_bytes':len(body)+1})
    # A small old directory capture can legitimately hold >16MiB CURRENT text
    # after overlapping per-file sources advance its nine independent members.
    project,other=w.project('Growth allowed'),w.project('Growth never allowed');root=w.root/'overlap-growth';root.mkdir();raws={};paths=[]
    for i in range(9):
        path=root/(str(i)+'.txt');path.write_bytes(('budgetgrowth small '+str(i)).encode());paths.append(path)
    source=w.local.add(root,[project]);w.local.refresh(source)
    billed=w.local.source(source)['counts']['billed_bytes'];assert billed<SOURCE_LIMIT
    for i,path in enumerate(paths):
        prefix=('budgetgrowth '+str(i)+'\n').encode();raw=prefix+b'x'*(FILE_LIMIT-len(prefix));path.write_bytes(raw);raws[str(path.resolve())]=raw
        leaf=w.local.add(path,[other]);w.local.refresh(leaf)
    assert w.local.source(source)['counts']['billed_bytes']==billed
    files=w.local.files(source);assert len(files)==9 and all(f['version']==2 for f in files)
    expected={f['id']:raws[f['path']] for f in files}
    with pytest.MonkeyPatch.context() as patch:
        attempted=deny_source_reads(patch,*paths);w.policy(project);w.sync();assert attempted==[]
    hp=w.hub_project_for(project);hq=w.hub_project_for(other)
    hits=w.search_hub(query='budgetgrowth',scope='project',project_id=hp['id'],limit=50)['results']
    assert len(hits)==9 and {h['origin']['document_id'] for h in hits}==set(expected)
    for hit in hits:
        raw=expected[hit['origin']['document_id']];assert hit['version']==2 and hit['sha256']==sha(raw) and hit['text_sha256']==sha(raw)
        assert hit['text_length']==FILE_LIMIT and hit['project_ids']==[hp['id']]
        for start in range(0,FILE_LIMIT,16000):
            end=min(FILE_LIMIT,start+16000);assert_text(w.read_hub(hit,start=start,end=end),raw.decode(),start,end)
    assert w.search_hub(query='budgetgrowth',scope='project',project_id=hq['id'])['results']==[]
    observe('grown-source-budget',{'old_billed_bytes':billed,'current_bytes':sum(map(len,expected.values())),'files':{doc:sha(raw) for doc,raw in expected.items()},'exact_returned_ids':[h['origin']['document_id'] for h in hits]})
    # The same 006 raw/candidate budget is enforced through actual Hub CLI.
    def cli(*args):
        result=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents',*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        observe('native-budget-cli',{'args':args,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==0,result.stderr
        return json.loads(result.stdout)
    native_project=w.hub_project('Native budget');native_root=w.root/'native-budget';native_root.mkdir();native_raw={}
    for i in range(8):
        prefix=('nativebudget '+str(i)+'\n').encode();raw=prefix+b'y'*(FILE_LIMIT-len(prefix));path=native_root/(str(i)+'.txt');path.write_bytes(raw);native_raw[str(path.resolve())]=raw
    native_source=cli('add',native_root,'--project-id',native_project['id']);cli('refresh','--source-id',native_source['id'])
    state=next(x for x in cli('sources') if x['id']==native_source['id']);assert state['status']=='ready' and state['counts']['billed_bytes']==SOURCE_LIMIT
    exact_hits=cli('search','nativebudget','--scope','project','--project-id',native_project['id'],'--limit','50')['results'];assert len(exact_hits)==8
    for hit in exact_hits:
        raw=native_raw[hit['path']];assert hit['text_sha256']==sha(raw) and hit['text_length']==FILE_LIMIT
        assert_text(cli('read','--reference',hit['reference'],'--start','0','--end','40'),raw.decode(),0,40)
        assert_text(cli('read','--reference',hit['reference'],'--start',FILE_LIMIT-40,'--end',FILE_LIMIT),raw.decode(),FILE_LIMIT-40,FILE_LIMIT)
    ninth=native_root/'8.txt';ninth.write_bytes(b'y'*FILE_LIMIT);cli('refresh','--source-id',native_source['id'])
    state=next(x for x in cli('sources') if x['id']==native_source['id']);assert state['status']=='failed' and state['counts']['billed_bytes']==SOURCE_LIMIT+FILE_LIMIT
    assert cli('search','nativebudget','--scope','project','--project-id',native_project['id'])['results']==[]
    ninth.unlink();cli('refresh','--source-id',native_source['id'])
    for hit in exact_hits:w.reject_remote('POST','/documents/read',{**w.context(),'reference':hit['reference']})
    count_root=w.root/'native-candidates';count_root.mkdir()
    for i in range(1000):(count_root/(str(i)+'.txt')).write_bytes(b'')
    count_source=cli('add',count_root,'--project-id',native_project['id']);cli('refresh','--source-id',count_source['id'])
    state=next(x for x in cli('sources') if x['id']==count_source['id']);assert state['status']=='ready' and state['counts']['candidates']==1000
    assert len(cli('files','--source-id',count_source['id']))==1000
    (count_root/'1000.txt').write_bytes(b'');cli('refresh','--source-id',count_source['id'])
    state=next(x for x in cli('sources') if x['id']==count_source['id']);assert state['status']=='failed' and state['counts']['candidates']==1001



# @case-id: TC-007-paused-lifecycle
def test_paused_lifecycle(w,monkeypatch):
    for paused in [False,True]:
        project=w.project('Lifecycle '+str(paused));nonce='life'+str(int(paused));roots=[];sources=[];originals={}
        for i in range(5):
            root=w.root/('lifecycle-'+str(paused)+'-'+str(i));root.mkdir();roots.append(root)
            for name in ['a.txt','b.txt']:
                text=nonce+' original '+str(i)+' '+name;(root/name).write_text(text);originals[(i,name)]=text
            source=w.local.add(root,[project]);w.local.refresh(source);sources.append(source)
        w.policy(project);w.sync();hp=w.hub_project_for(project)
        def search():return w.search_hub(query=nonce,scope='project',project_id=hp['id'],limit=50)
        expected=dict(originals)
        def verify():
            result=search();values=w.docs(result,True)
            assert len(result['results'])==len(expected) and set(values.values())==set(expected.values())
            return result
        initial=verify();oldrefs={w.read_hub(h)['text']:h for h in initial['results']}
        if paused:w.policy(project,False)
        marker=len(w.calls)
        for name in ['a.txt','b.txt']:(roots[0]/name).write_text(nonce+' edited 0 '+name)
        (roots[0]/'new.txt').write_text(nonce+' newly discovered')
        w.local.refresh(sources[0]);w.sync()
        if not paused:
            for name in ['a.txt','b.txt']:expected[(0,name)]=nonce+' edited 0 '+name
            expected[(0,'new.txt')]=nonce+' newly discovered'
        verify()
        if paused:
            wire=json.dumps(w.calls[marker:]);assert all(x not in wire for x in [nonce+' edited',nonce+' newly discovered','new.txt'])
            assert not any(route in {'/documents/stage','/documents/publish'} for route,_ in w.calls[marker:])
        (roots[0]/'a.txt').unlink();w.local.refresh(sources[0]);w.sync();expected.pop((0,'a.txt'));verify()
        # Configuration replacement invalidates BOTH formerly qualified members.
        w.local.set(sources[1],project_ids=[project]);w.sync()
        for name in ['a.txt','b.txt']:expected.pop((1,name))
        verify()
        for name in ['a.txt','b.txt']:w.reject_remote('POST','/documents/read',{**w.context(),'reference':oldrefs[originals[(1,name)]]['reference']})
        w.local.refresh(sources[1]);w.sync()
        if not paused:
            for name in ['a.txt','b.txt']:expected[(1,name)]=originals[(1,name)]
        verify()
        # Source removal happens while still in the selected paused/active state,
        # and offline: Hub must keep its last snapshot until acknowledgement.
        before_offline=dict(expected);request=federation._request
        def offline(*a,**kw):raise federation.HubUnavailable('lifecycle disconnected')
        monkeypatch.setattr(federation,'_request',offline);w.local.remove(sources[2]);out=w.sync()
        assert out['pending'] and out['errors'];verify()
        w.local=Fixture(w.root/('restart-'+str(paused)),db=Archive(w.pair.local.db_path));assert w.status()['pending']
        monkeypatch.setattr(federation,'_request',request);w.sync()
        for name in ['a.txt','b.txt']:expected.pop((2,name))
        verify()
        # Entire-source failure, not another unlink. Two unchanged bodies were
        # qualified before pause; same-byte recovery cannot lend old eligibility.
        original_scan=Documents._scan
        def source_failure(self,source):
            if source['id']==sources[3]['id']:raise PermissionError('synthetic whole-source read failure')
            return original_scan(self,source)
        with monkeypatch.context() as m:
            m.setattr(Documents,'_scan',source_failure);w.local.refresh(sources[3])
        assert w.local.source(sources[3])['status']=='failed';w.sync()
        for name in ['a.txt','b.txt']:expected.pop((3,name))
        verify();w.local.refresh(sources[3]);w.sync()
        if not paused:
            for name in ['a.txt','b.txt']:expected[(3,name)]=originals[(3,name)]
        verify()
        for name in ['a.txt','b.txt']:w.reject_remote('POST','/documents/read',{**w.context(),'reference':oldrefs[originals[(3,name)]]['reference']})
        from smm_local import documents as document_module
        original_read=document_module._read_file;broken=roots[4]/'a.txt'
        def one_unreadable(path,expected_stat):
            if Path(path)==broken:raise PermissionError('synthetic single-member unreadable')
            return original_read(path,expected_stat)
        with monkeypatch.context() as m:
            m.setattr(document_module,'_read_file',one_unreadable);w.local.refresh(sources[4])
        assert w.local.source(sources[4])['status']=='partial';w.sync();expected.pop((4,'a.txt'));verify()
        assert_text(w.read_hub(oldrefs[originals[(4,'b.txt')]]),originals[(4,'b.txt')])
        w.reject_remote('POST','/documents/read',{**w.context(),'reference':oldrefs[originals[(4,'a.txt')]]['reference']})
        w.local.refresh(sources[4]);w.sync()
        if not paused:expected[(4,'a.txt')]=originals[(4,'a.txt')]
        verify()
        w.reject_remote('POST','/documents/read',{**w.context(),'reference':oldrefs[originals[(4,'a.txt')]]['reference']})
        w.policy(project);w.sync()
        expected={(0,'b.txt'):nonce+' edited 0 b.txt',(0,'new.txt'):nonce+' newly discovered',**{(i,name):originals[(i,name)] for i in [1,3,4] for name in ['a.txt','b.txt']}}
        verify()
        for original_text,hit in oldrefs.items():
            if original_text==originals[(4,'b.txt')]:assert_text(w.read_hub(hit),original_text)
            else:w.reject_remote('POST','/documents/read',{**w.context(),'reference':hit['reference']})
    # Global automatic pause differs from project pause: only background BODY
    # stops. Its real periodic worker still retries known withdrawal control.
    from smm_local.api import create_app
    project=w.project('Global pause');first,s1=w.source('global-a.txt','autononce A1',[project]);second,s2=w.source('global-b.txt','autononce B1',[project]);w.policy(project);w.sync();hp=w.hub_project_for(project)
    first.write_text('autononce A2');Documents(w.pair.local).refresh(s1['id'])
    third=w.local.file('global-new.txt','autononce NEW');s3=Documents(w.pair.local).add(str(third),project_ids=[project]);Documents(w.pair.local).refresh(s3['id'])
    Documents(w.pair.local).remove(s2['id']);w.pair.local.set_settings(sync_paused=True,sync_interval_seconds=10)
    policy_before=federation.upload_status(w.pair.local)['policy'];seen=Event();request=federation._request;calls=[]
    def record(config,route,payload=None):
        calls.append((route,deepcopy(payload)));reply=request(config,route,payload)
        if route=='/documents/control' and payload.get('project_key')==federation._remote_project_key(w.pair.local,project):seen.set()
        return reply
    monkeypatch.setattr(federation,'_request',record)
    source_attempts=[];original_scan=Documents._scan
    def forbidden_scan(self,source):source_attempts.append(source['id']);raise AssertionError('automatic retry scanned document source')
    with monkeypatch.context() as m:
        m.setattr(Documents,'_scan',forbidden_scan)
        with TestClient(create_app(w.pair.local,auto_sync=True,sync_on_start=False)):
            assert seen.wait(15),'paused worker did not retry document control'
            # An observed control request has committed; synchronizing controls
            # explicitly makes this assertion independent of thread scheduling.
            # No manual full sync until after background body/withdraw checks.
            assert not any(route in {'/documents/stage','/documents/publish'} for route,_ in calls)
            result=w.search_hub(query='autononce',scope='project',project_id=hp['id'],limit=50)
            assert list(w.docs(result,True).values())==['autononce A1']
            wire=json.dumps(calls);assert 'autononce A2' not in wire and 'autononce NEW' not in wire and s3['id'] not in wire
        assert source_attempts==[]
        w.cli('documents','sync')
    result=w.search_hub(query='autononce',scope='project',project_id=hp['id'],limit=50)
    assert set(w.docs(result,True).values())=={'autononce A2','autononce NEW'}
    assert w.pair.local.get_settings()['sync_paused'] is True and federation.upload_status(w.pair.local)['policy']==policy_before


# @case-id: TC-007-overlap-publication
def test_overlap_publication(w):
    p,q=w.project('P'),w.project('Q');path,s1=w.source('same.txt','needle V1',[p]);s2=w.local.add(path,[q]);w.local.refresh(s2)
    w.policy(p);w.policy(q);w.sync();hp,hq=w.hub_project_for(p),w.hub_project_for(q)
    def verify(version,text,collector,p_qualified=True,q_qualified=True):
        found={}
        for label,project,wanted_sources in [('P',hp,[s1['id']] if p_qualified else []),('Q',hq,[s2['id']] if q_qualified else []),('all',None,([s1['id']] if p_qualified else [])+([s2['id']] if q_qualified else []))]:
            options={'scope':'project','project_id':project['id']} if project else {}
            result=w.search_hub(limit=50,**options);assert len(result['results'])==bool(wanted_sources)
            if not wanted_sources:continue
            hit=result['results'][0];assert hit['version']==version and hit['captured_by_source_id']==collector
            assert_text(w.read_hub(hit),text)
            assert {s['source_id'] for s in hit['provenance']}==set(wanted_sources)
            assert set(hit['project_ids'])==({hp['id']} if label=='P' else {hq['id']} if label=='Q' else ({hp['id']} if p_qualified else set())|({hq['id']} if q_qualified else set()))
            found[label]=hit
        assert len({h['id'] for h in found.values()})<=1
        return found
    v1=verify(1,'needle V1',s2['id']);w.policy(q,False)
    path.write_text('needle V2');w.local.refresh(s1);w.sync();v2=verify(2,'needle V2',s1['id'])
    for old in v1.values():w.reject_remote('POST','/documents/read',{**w.context(),'reference':old['reference']})
    w.local.remove(s1);w.sync();q_only=verify(2,'needle V2',s1['id'],False,True)
    assert_text(w.read_hub(v2['all']),'needle V2')
    w.reject_remote('POST','/documents/read',{**w.context(),'reference':v2['P']['reference']})
    # Q's unchanged old source is still continuous, not a fallback to its V1.
    assert_text(w.read_hub(v2['Q']),'needle V2')
    w.local.set(s2,project_ids=[]);w.sync();verify(2,'needle V2',s1['id'],False,False)
    for hit in [*v2.values(),*q_only.values()]:w.reject_remote('POST','/documents/read',{**w.context(),'reference':hit['reference']})


# @case-id: TC-007-origin-identity
def test_origin_identity(w):
    contexts=[w.protocol(),{**w.protocol(),'device_id':'c'*32,'archive_id':'d'*32}]
    d=w.doc();manifests=[]
    for p in contexts:
        w.control(p);w.stage(p,d);m=w.manifest(p,[d]);w.publish(m);manifests.append(m)
    # Same-device overlap creates a second qualification, not a second file.
    for p in contexts:w.publish(w.manifest(p,[d],source_id='e'*32))
    hits=w.search_hub(limit=50)['results'];assert len(hits)==2
    assert {(h['origin']['device_id'],h['origin']['archive_id'],h['origin']['document_id']) for h in hits}=={(w.device,w.archive,d['document_id']),('c'*32,'d'*32,d['document_id'])}
    for h in hits:
        assert_text(w.read_hub(h),d['text']);assert len(h['source_ids'])==2
        assert {x['source_id'] for x in h['provenance']}=={'b'*32,'e'*32}
    for p,m in zip(contexts,manifests):
        conflict=w.doc('needle different',ident=d['document_id']);before=w.snapshot()
        w.reject_remote('POST','/documents/stage',{**p,'document':conflict});assert w.snapshot()==before
        changed=deepcopy(m);changed['files'][0]['relative_path']='other.txt'
        w.reject_remote('POST','/documents/publish',changed);assert w.snapshot()==before
        # Each legal alternative breaks only one part of the authorized identity.
        for field,legal in [('device_id','f'*32),('archive_id','f'*32),('project_key','f'*32)]:
            for value in [legal,'invalid',-1,True]:
                w.reject_remote('POST','/documents/stage',{**p,field:value,'document':d});assert w.snapshot()==before


# @case-id: TC-007-ordering-concurrency
def test_ordering_concurrency(w,monkeypatch):
    # Hub version, source config, snapshot order and project generation are
    # independent fences: change only one while keeping the others current.
    p=w.protocol();w.control(p);d=w.doc();w.stage(p,d);w.publish(w.manifest(p,[d]))
    d2=w.doc('needle newest',ident=d['document_id'],version=2);w.stage(p,d2);w.publish(w.manifest(p,[d2],sequence=2))
    old_version={**d,'capture_sequence':d2['capture_sequence'],'captured_at':d2['captured_at'],'captured_by_source_id':d2['captured_by_source_id']}
    for old in [w.manifest(p,[old_version],sequence=3),w.manifest(p,[d2],sequence=1)]:
        before=w.snapshot();w.reject_remote('POST','/documents/publish',old);assert w.snapshot()==before
    # Same bytes/version can have a newer actual collector. A late older
    # source may add eligibility or be rejected, but cannot roll metadata back.
    new_meta={**d2,'capture_sequence':3,'captured_at':'2026-11-23T00:00:01Z','captured_by_source_id':'c'*32}
    w.stage(p,new_meta);w.publish(w.manifest(p,[new_meta],source_id='c'*32,sequence=1))
    before=w.snapshot();late=w.hub.post('/v1/documents/publish',json=w.manifest(p,[d2],sequence=3))
    assert late.status_code==200 or 400<=late.status_code<500
    if late.status_code!=200:assert w.snapshot()==before
    current_hit=w.search_hub()['results'][0];assert current_hit['captured_by_source_id']=='c'*32 and current_hit['captured_at']==new_meta['captured_at'];assert_text(w.read_hub(current_hit),'needle newest')
    # Only source config is stale; snapshot order and file capture are current.
    w.publish(w.manifest(p,[new_meta],sequence=4,revision=2))
    before=w.snapshot();w.reject_remote('POST','/documents/publish',w.manifest(p,[new_meta],sequence=5,revision=1));assert w.snapshot()==before
    paused={**p,'generation':2}
    w.control(paused,enabled=False,sequence=4,retained=[{'source_id':'b'*32,'revision':2,'files':[{'document_id':d['document_id'],'qualification':1}]}])
    before=w.snapshot();w.reject_remote('POST','/documents/publish',w.manifest(p,[new_meta],sequence=5,revision=2));assert w.snapshot()==before
    w.control(paused,enabled=False,sequence=5,retained=[]);assert w.search_hub()['results']==[]
    before=w.snapshot();w.reject_remote('POST','/documents/control',{**p,'project_name':'old','enabled':True,'sequence':100,'retained':[]});assert w.snapshot()==before
    current={**p,'generation':3};w.control(current,sequence=6);w.stage(current,d2);w.publish(w.manifest(current,[d2],sequence=6,revision=2))
    assert list(w.docs(w.search_hub(),True).values())==['needle newest']
    # Actual Local sync is suspended AFTER accepted publication, BEFORE its ack
    # reaches the client. Another control action must finish in that interval.
    project=w.project('Local concurrent');path,source=w.source('concurrent.txt','concurrentnonce v1',[project]);w.policy(project);w.sync()
    path.write_text('concurrentnonce v2');Documents(w.pair.local).refresh(source['id'])
    original=federation._request;arrived=Event();release=Event();once={'done':False};errors=[]
    pause_offline={'enabled':True}
    def delayed(config,route,payload=None):
        if route=='/documents/control' and payload.get('project_key')==federation._remote_project_key(w.pair.local,project) and payload.get('generation',0)>1 and pause_offline['enabled']:
            raise federation.HubUnavailable('new pause control cannot reach Hub')
        response=original(config,route,payload)
        if route=='/documents/publish' and payload.get('project_key')==federation._remote_project_key(w.pair.local,project) and not once['done']:
            once['done']=True;arrived.set();assert release.wait(15),'test release not signalled'
        return response
    monkeypatch.setattr(federation,'_request',delayed)
    def sync_worker():
        try:w.sync()
        except BaseException as exc:errors.append(exc)
    worker=Thread(target=sync_worker);worker.start();assert arrived.wait(15)
    # A separate connection's immediate transaction checks the SQLite lock too.
    completed=Event();choice=[]
    def choose_new():
        try:
            with w.pair.local.connect() as c:
                c.execute('PRAGMA busy_timeout=1000');c.execute('BEGIN IMMEDIATE');c.execute("UPDATE settings SET value=value WHERE key='sync_paused'")
            status=w.status();pstate=next(x for x in status['projects'] if x['project_id']==project)
            r=w.local.client.post('/api/documents/sync-policy',json={'project_key':pstate['project_key'],'enabled':False,'expected_hub_id':status['hub_id'],'expected_generation':pstate['generation']})
            assert r.status_code==200,r.text;choice.append(w.status())
        except BaseException as exc:errors.append(exc)
        finally:completed.set()
    chooser=Thread(target=choose_new);chooser.start()
    try:assert completed.wait(3),'client holds its control lock/SQLite transaction across network wait'
    finally:release.set();worker.join(15);chooser.join(15)
    assert not worker.is_alive() and not chooser.is_alive() and not errors,errors
    final=w.status();old_choice=next(x for x in choice[0]['projects'] if x['project_id']==project);latest=next(x for x in final['projects'] if x['project_id']==project)
    assert old_choice['confirmed_generation']<old_choice['generation'] and choice[0]['pending']
    assert latest['generation']==old_choice['generation'] and not latest['enabled']
    assert latest['confirmed_generation']<latest['generation'] and final['pending'],'late old ack cleared a newer unconfirmed pause'
    w.local=Fixture(w.root/'pending-restart',db=Archive(w.pair.local.db_path));assert w.status()['pending']
    pause_offline['enabled']=False;w.sync()
    confirmed=next(x for x in w.status()['projects'] if x['project_id']==project);assert confirmed['confirmed_generation']==confirmed['generation'] and not confirmed['enabled']
    # Normal current control/sync still succeeds after the race.
    w.policy(project);w.sync();assert list(w.docs(w.search_hub(query='concurrentnonce'),True).values())==['concurrentnonce v2']


# @case-id: TC-007-recovery-controls
def test_recovery_controls(w,tmp_path):
    import sqlite3,re
    # Real old dialogue/005 state is present and must survive document recovery.
    add_local(w.pair,'legacy-recover','Conversation','legacyrecover original');federation.choose_upload(w.pair.local,'all',[]);federation.push_pending(w.pair.local)
    from test_vibeinsight_sync import FixtureSource,event
    from smm_hub.vibeinsight import VibeInsightSync
    VibeInsightSync(w.pair.remote,'fixture',batch_size=2).run(FixtureSource([event(0,'legacy-vibe-a','user',text='legacyvibenonce A'),event(1,'legacy-vibe-b','assistant',text='legacyvibenonce B')],['git.example/team/alpha']))

    def legacy(db):
        with db.connect() as c:
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in {'messages','conversations','hub_managed_devices'} or r[0].startswith(('local_upload_','upload_message_','hub_upload_','hub_policy_','hub_vibeinsight_'))]
            return {name:[dict(row) for row in c.execute('SELECT * FROM '+name+' ORDER BY 1')] for name in names}
    def cli(*args,code=0):
        result=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents',*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        observe('recovery-cli',{'argv':args,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==code,result.stderr
        return json.loads(result.stdout) if code==0 else result
    def guard(db):return Path(str(db.db_path.resolve())+'.documents-guard.json')
    def invalidate(db,fault,backup):
        path=guard(db);assert path.is_file()
        if fault=='rollback':
            with sqlite3.connect(backup) as src,db.connect() as dst:src.backup(dst)
        elif fault=='missing':path.unlink()
        elif fault=='corrupt':path.write_text('not-json',encoding='utf-8')
        else:
            data=json.loads(path.read_text());changed=[]
            def alter(value):
                if isinstance(value,dict):return {key:alter(v) for key,v in value.items()}
                if isinstance(value,list):return [alter(v) for v in value]
                if isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value):changed.append(value);return ('e' if value!='e'*64 else 'f')*64
                return value
            altered=alter(data);assert changed,'guard probe found no fingerprint to alter';path.write_text(json.dumps(altered),encoding='utf-8')
    for side in ['hub','local']:
        for fault in ['rollback','missing','corrupt','inconsistent']:
            label=side+'-'+fault;project=w.project(label);nonce='recover'+side+fault
            path,source=w.source(label+'.txt',nonce+' original',[project]);w.policy(project);w.sync()
            selected_generation=next(x for x in w.status()['projects'] if x['project_id']==project)['generation']
            hp=w.hub_project(label);native_path=tmp_path/(label+'-native.txt');native_path.write_text(nonce+' native')
            added=cli('add',native_path,'--project-id',hp['id']);cli('refresh','--source-id',added['id'])
            old=w.search_hub(query=nonce,limit=50)['results'];assert len(old)==2
            expected={h['id']:(nonce+' native' if h['origin']['document_id']!=w.local.files(source)[0]['id'] else nonce+' original') for h in old}
            for hit in old:assert_text(w.read_hub(hit),expected[hit['id']])
            if side=='hub':
                protocol=w.protocol(federation._remote_project_key(w.pair.local,project),generation=selected_generation)
                def current_control():return next(payload['sequence'] for route,payload in reversed(w.calls) if route=='/documents/control' and payload.get('project_key')==protocol['project_key'])
                probe=w.doc('guardpositive independent '+label);w.stage(protocol,probe)
                valid_manifest=w.manifest(protocol,[probe],source_id=uuid4().hex);valid_manifest['control_sequence']=current_control();w.publish(valid_manifest)
                candidate=w.doc('guardpending independent '+label,ident=probe['document_id'],version=2);w.stage(protocol,candidate)
                pending_manifest=w.manifest(protocol,[candidate],source_id=valid_manifest['source_id'],sequence=2);pending_manifest['control_sequence']=current_control()
            db=w.pair.remote if side=='hub' else w.pair.local;backup=tmp_path/(label+'.sqlite3')
            with db.connect() as src,sqlite3.connect(backup) as dst:src.backup(dst)
            before_local,before_hub=legacy(w.pair.local),legacy(w.pair.remote)
            legacy_guards={p:sha(p.read_bytes()) for p in [Path(str(w.pair.local.db_path.resolve())+'.upload-guard.json'),Path(str(w.pair.remote.db_path.resolve())+'.upload-guard.json')] if p.exists()}
            # Advance protected state beyond the backup with actual control.
            if side=='hub':w.local.remove(source);w.sync()
            else:w.policy(project,True)
            if side=='local':
                path.write_text(nonce+' pending V2');Documents(w.pair.local).refresh(source['id'])
                def no_remote(*args,**kwargs):raise federation.HubUnavailable('offline independent guard diagnosis')
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr(federation,'_request',no_remote);healthy=w.status();assert not healthy['conflict'] and not healthy.get('protection_error')
            if side=='hub' and fault!='rollback':pending_manifest['control_sequence']=current_control()
            invalidate(db,fault,backup)
            if side=='local' and fault=='rollback':Documents(w.pair.local).refresh(source['id'])
            if side=='hub':
                context=w.context();before=w.snapshot()
                w.reject_remote('POST','/documents/search',{**context,'query':nonce})
                for hit in old:w.reject_remote('POST','/documents/read',{**context,'reference':hit['reference']})
                new_body=w.doc('guardstage independent '+label)
                w.reject_remote('POST','/documents/stage',{**protocol,'document':new_body});assert w.snapshot()==before
                # Body V2 was staged while healthy, using the SAME real G and
                # source/config metadata as the proven successful V1 publication.
                # T matches the actual restored/current DB, so only guard fails.
                w.reject_remote('POST','/documents/publish',pending_manifest);assert w.snapshot()==before
                status=cli('recovery-status');assert status['conflict'] and status['state']
                cli('recover','--expected-state',status['state'])
                assert w.search_hub(query=nonce)['results']==[]
                # Stale state must not reset this new boundary again.
                current=w.snapshot();cli('recover','--expected-state',status['state'],code=2);assert w.snapshot()==current
                sources=cli('sources');retained=next((s for s in sources if s['id']==added['id']),None)
                assert retained is not None and retained['status']=='pending'
                marker=len(w.calls);w.sync();assert not any(route=='/documents/stage' for route,_ in w.calls[marker:])
                for hit in old:w.reject_remote('POST','/documents/read',{**w.context(),'reference':hit['reference']})
                # Explicit own refresh and explicit device selection rebuild new
                # eligibility; no old reference becomes valid in the new epoch.
                if retained:cli('refresh','--source-id',retained['id'])
                source=w.local.add(path,[project]);w.local.refresh(source)
                fresh_key=federation._remote_project_key(w.pair.local,project);marker=len(w.calls)
                w.policy(project);w.sync();texts=set(w.docs(w.search_hub(query=nonce,limit=50),True).values())
                assert texts=={nonce+' original',nonce+' native'}
                assert all(payload['project_key']==fresh_key for route,payload in w.calls[marker:] if route=='/documents/stage')
                for hit in old:w.reject_remote('POST','/documents/read',{**w.context(),'reference':hit['reference']})
            else:
                request=federation._request
                def no_remote_status(*args,**kwargs):raise federation.HubUnavailable('remote unavailable during Local protection diagnosis')
                with pytest.MonkeyPatch.context() as patch:
                    patch.setattr(federation,'_request',no_remote_status);diagnosis=w.status()
                    assert diagnosis['conflict'] and diagnosis['protection_error']
                marker=len(w.calls);out=w.sync();assert out['pending'] and out['errors'] and w.status()['conflict']
                assert all(not payload.get('enabled') for route,payload in w.calls[marker:] if route=='/documents/control')
                assert not any(route in {'/documents/stage','/documents/publish'} for route,_ in w.calls[marker:])
                # Explicit selection repairs Local guard without silently enabling
                # other stale choices; old bodies/versions are not guessed anew.
                marker=len(w.calls);fresh_key=federation._remote_project_key(w.pair.local,project)
                w.policy(project);w.sync();assert nonce+' pending V2' in set(w.docs(w.search_hub(query=nonce,limit=50),True).values())
                assert all(payload['project_key']==fresh_key for route,payload in w.calls[marker:] if route=='/documents/stage')
            assert legacy(w.pair.local)==before_local and legacy(w.pair.remote)==before_hub
            for path,digest in legacy_guards.items():assert sha(path.read_bytes())==digest


# @case-id: TC-007-hub-native
def test_hub_native(w,tmp_path,monkeypatch):
    state=tmp_path/'native';state.mkdir();db=Archive(state/'smm-hub.sqlite3');token='n'*48
    with TestClient(create_hub(db,token),headers={'Authorization':'Bearer '+token}) as client:
        def cli(*args,code=0):
            p=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(state),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
            observe('hub-native-cli',{'args':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==code,p.stderr
            return json.loads(p.stdout) if code==0 else p
        project=cli('project','create','Native P');same=cli('project','create','Native P');globalp=cli('project','ensure-global');assert len({project['id'],same['id'],globalp['id']})==3
        roots=[];sources=[]
        for i in [1,2]:
            root=tmp_path/('Native 中文 '+str(i));root.mkdir()
            for name in ['a.txt','b.md']:(root/name).write_text('nativeprobe '+str(i)+' '+name)
            source=cli('documents','add',root,'--project-id',project['id']);assert source['status']=='pending';roots.append(root);sources.append(source)
        assert cli('documents','search','nativeprobe')['results']==[]
        for source in sources:cli('documents','refresh','--source-id',source['id'])
        def actual():
            result=cli('documents','search','nativeprobe','--scope','project','--project-id',project['id'],'--limit','50')
            texts={h['id']:cli('documents','read','--reference',h['reference'])['text'] for h in result['results']}
            return result,texts
        result,texts=actual();assert len(texts)==4 and set(texts.values())=={'nativeprobe '+str(i)+' '+name for i in [1,2] for name in ['a.txt','b.md']}
        # Explicitly fail one complete source, then the second: independent files
        # of the other source must survive and cached reads must not open roots.
        shutil.rmtree(roots[0]);cli('documents','refresh','--source-id',sources[0]['id'])
        result,texts=actual();assert len(texts)==2 and set(texts.values())=={'nativeprobe 2 a.txt','nativeprobe 2 b.md'}
        (roots[1]/'a.txt').unlink();(roots[1]/'b.md').unlink()
        # Without refresh the current cached text still reads even nonexistent paths.
        for h in result['results']:assert cli('documents','read','--reference',h['reference'])['text']=='nativeprobe 2 '+Path(h['path']).name
        for name in ['a.txt','b.md']:(roots[1]/name).write_text('nativeprobe 2 '+name)
        cli('documents','set',sources[1]['id'],'--project-id',same['id'],'--exclude','b.md');assert cli('documents','search','nativeprobe')['results']==[]
        cli('documents','refresh','--source-id',sources[1]['id']);hit=cli('documents','search','nativeprobe')['results'][0];assert cli('documents','read','--reference',hit['reference'])['text']=='nativeprobe 2 a.txt'
        listed=cli('documents','sources');assert {s['id'] for s in listed}=={s['id'] for s in sources} and all(s['origin']['kind']=='hub' for s in listed)
        cli('documents','remove',sources[1]['id']);assert cli('documents','search','nativeprobe')['results']==[]
    project=w.project();path,source=w.source('device.txt','needle device',[project]);w.policy(project);w.sync()
    hp=w.hub_project();asset=w.upload(hp,'hub.txt','needle Hub independent',hub=True)
    listing=w.remote('GET','/documents/sources');imported=[s for s in listing if s['origin']['kind']=='device'];native=[s for s in listing if s['origin']['kind']=='hub']
    assert len(imported)==1 and len(native)==1 and imported[0]['origin']['source_id']==source['id'] and native[0]['id']==asset['source_id']
    # Real CLI rejects replica refresh/remove; never attempts the origin path.
    before=w.snapshot();disk=w.disk(w.pair.remote.db_path.parent)
    for action in ['refresh','remove']:
        argv=[sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents',action]+(['--source-id',imported[0]['id']] if action=='refresh' else [imported[0]['id']])
        audit_file=tmp_path/('replica-'+action+'-opens.jsonl')
        audit_code='\n'.join(['import json,pathlib,sys','target='+repr(str(path.resolve())),'audit='+repr(str(audit_file)),
            'def hook(event,args):',' if event=="open" and isinstance(args[0],str) and str(pathlib.Path(args[0]).resolve())==target:',
            '  with open(audit,"a",encoding="utf-8") as out:out.write(json.dumps({"event":event,"path":args[0]})+"\\n")',
            '  raise AssertionError("replica origin source opened")','sys.addaudithook(hook)',
            'from smm_hub.cli import main','sys.argv='+repr(argv[2:]),'main()'])
        # argv[2:] begins with the module name, which argparse treats as argv[0].
        result=subprocess.run([sys.executable,'-c',audit_code],capture_output=True,text=True,encoding='utf-8')
        assert result.returncode==2 and result.stderr
        assert not audit_file.exists() or audit_file.read_bytes()==b''
        assert w.snapshot()==before and w.disk(w.pair.remote.db_path.parent)==disk
    assert set(w.docs(w.search_hub(limit=50),True).values())=={'needle device','needle Hub independent'}


# @case-id: TC-007-project-scope
def test_project_scope(w):
    import asyncio
    from smm_local.mcp_server import create_mcp
    convo=add_local(w.pair,'only-conversation','C','chatneedle local C');c=convo['project_id'];d,e=w.project('D'),w.project('E')
    _,ds=w.source('d.txt','docneedle local D',[d]);w.source('e.txt','docneedle negative E',[e]);w.pair.local.link_projects(c,d);w.pair.local.link_projects(d,e)
    def docset(result,expected):
        actual=w.docs(result);assert len(result['results'])==len(expected) and set(actual.values())==expected
    def chat(result):
        assert {h['source_session_id'] for h in result['results']}=={'only-conversation'} and len(result['results'])==1
        actual=w.local.request('POST','/api/read',{'reference':result['results'][0]['reference']})
        assert [(m['position'],m['role'],m['text']) for m in actual['messages']]==[(1,'user','chatneedle local C')]
    docset(w.local.search('docneedle',scope='project',project_id=c,local=True),{'docneedle local D'})
    chat(w.local.request('POST','/api/search',{'query':'chatneedle','scope':'project','project_id':d,'local':True}))
    hp,he,hq=w.hub_project('D'),w.hub_project('E'),w.hub_project('D');assert hp['id']!=hq['id']
    hglobal=w.hub_project('Global','global');assert hglobal['project_kind']=='global'
    primary=w.upload(hp,'hub.txt','docneedle Hub D',hub=True);w.upload(he,'negative.txt','docneedle Hub E',hub=True)
    w.upload(hq,'same-name-negative.txt','docneedle same-name negative',hub=True);w.upload(hglobal,'global.txt','docneedle Hub global',hub=True)
    federation.choose_upload(w.pair.local,'only',[c]);federation.push_pending(w.pair.local)
    projects=HubProjects(w.pair.remote);hc=w.hub_project_for(c);projects.link(hc['id'],hp['id']);projects.link(hp['id'],he['id'])
    docset(w.local.search('docneedle',scope='project',project_id=c,limit=50),{'docneedle Hub D'})
    chat(w.local.request('POST','/api/search',{'query':'chatneedle','scope':'project','hub_project_id':hp['id']}))
    docset(w.local.search('docneedle',scope='project',hub_project_id=hp['id'],limit=50),{'docneedle Hub D','docneedle Hub E'})
    docset(w.local.search('docneedle',scope='project',hub_project_id=hglobal['id']),{'docneedle Hub global'})
    # Both public discovery entries must actually contain the requested roots.
    listing=w.local.request('GET','/api/projects?include_hub=true')
    assert {p['id'] for p in listing['hub']}=={p['id'] for p in projects.list()}
    assert {p['id'] for p in listing['local']}=={p['id'] for p in w.pair.local.projects()}
    assert {p['id'] for p in w.cli('projects','--hub')}=={p['id'] for p in projects.list()}
    server=create_mcp(w.pair.local)
    listed=json.loads(asyncio.run(server.call_tool('list_projects',{'include_hub':True}))[0][0].text)
    assert {p['id'] for p in listed['hub']}=={p['id'] for p in projects.list()}
    default=json.loads(asyncio.run(server.call_tool('list_projects',{}))[0][0].text);assert isinstance(default,list)
    assert {p['id'] for p in default}=={p['id'] for p in w.pair.local.projects()}
    # Multi-bind own source, without manufacturing an association edge.
    edges=projects.links();w.remote('PUT','/documents/sources/'+primary['source_id'],{**w.project_context(hp),'project_ids':[hp['id'],hq['id']],'exclude':[],'recursive':True})
    command=[sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents','refresh','--source-id',primary['source_id']]
    refreshed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8');assert refreshed.returncode==0,refreshed.stderr
    assert projects.links()==edges
    docset(w.local.search('docneedle',scope='project',hub_project_id=hq['id'],limit=50),{'docneedle Hub D','docneedle same-name negative'})
    # Zero-bound source appears only in all, including for Hub-native paths.
    native_path=w.root/'Hub unbound.txt';native_path.write_text('docneedle Hub unbound')
    add=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents','add',str(native_path)],capture_output=True,text=True,encoding='utf-8');assert add.returncode==0,add.stderr
    added=json.loads(add.stdout);assert added['project_ids']==[]
    refresh=subprocess.run(command[:-1]+[added['id']],capture_output=True,text=True,encoding='utf-8');assert refresh.returncode==0,refresh.stderr
    assert 'docneedle Hub unbound' in set(w.docs(w.local.search('docneedle',limit=50)).values())
    docset(w.local.search('docneedle',scope='project',project_id=c,limit=50),{'docneedle Hub D'})
    # Rename preserves stable registration and association. Merge moves binding,
    # then the new project needs an explicit Hub association for online C scope.
    w.policy(d);w.sync();hd=w.hub_project_for(d);projects.link(hc['id'],hd['id'])
    w.pair.local.rename_project(d,'Renamed D');w.sync();assert w.hub_project_for(d)['id']==hd['id']
    docset(w.local.search('docneedle',scope='project',project_id=c,limit=50),{'docneedle Hub D','docneedle local D'})
    target=w.project('Merge target');w.policy(target);w.pair.local.merge_projects(d,target);w.sync()
    assert w.local.source(ds)['project_ids']==[target]
    docset(w.local.search('docneedle',scope='project',project_id=c,limit=50),{'docneedle Hub D'})
    projects.link(hc['id'],w.hub_project_for(target)['id'])
    docset(w.local.search('docneedle',scope='project',project_id=c,limit=50),{'docneedle Hub D','docneedle local D'})
    sources=w.local.sources();global_local=w.pair.local.ensure_global_project()['id'];w.pair.local.map_path(str(w.root/'client'/'docs'),global_local)
    assert w.local.sources()==sources
    docset(w.local.search('docneedle',scope='project',project_id=global_local,local=True),set())


# @case-id: TC-007-search-candidates
def test_search_candidates(w,monkeypatch):
    import math
    from collections import Counter
    project=w.project();path,source=w.source('same.txt','needle needle quartz short',[project]);w.policy(project);w.sync();w.policy(project,False)
    known={}
    shared_id=w.local.files(source)[0]['id'];known[(w.device,w.archive,shared_id,1)]='needle needle quartz short'
    for i,text in enumerate(['needle privateonlynonce needle needle short','quartz privateonlynonce '+'filler '*80],1):
        _,private=w.source('private-'+str(i)+'.txt',text,[project]);doc=w.local.files(private)[0]
        known[(w.device,w.archive,doc['id'],doc['version'])]=text
    local_long='prefix '*400+'needle privateonlynonce '+('suffix '*500)
    _,long_source=w.source('private-long.txt',local_long,[project]);long_doc=w.local.files(long_source)[0];known[(w.device,w.archive,long_doc['id'],long_doc['version'])]=local_long
    hp=w.hub_project()
    for i,text in enumerate(['head '*500+'quartz remote long '+('tail '*600),'needle remote long '+'other '*40,'quartz tie text','quartz tie text'],1):
        asset=w.upload(hp,'remote-'+str(i)+'.md',text,hub=True)
        hit=next(h for h in w.search_hub(query='needle quartz',limit=50)['results'] if h['id']==asset['id'])
        o=hit['origin'];known[(o['device_id'],o['archive_id'],o['document_id'],hit['version'])]=text
    query='needle quartz'
    def identity(h):o=h['origin'];return(o['device_id'],o['archive_id'],o['document_id'],h['version'])
    def expected(local,remote,limit):
        # Candidate inputs are the two normally returned lists; original bodies
        # are checked against the independently submitted fixtures before math.
        candidates={}
        for h in local+remote:
            key=identity(h);assert len(h['text'])<=2000;assert_text(h,known[key],h['start'],h['end'])
            assert h['text_length']==len(known[key])
            if len(known[key])>2000:assert len(h['text'])<len(known[key]) and any(term in h['text'] for term in ['needle','quartz'])
            assert h['text_sha256']==sha(known[key].encode())
            candidates[key]=h
        documents={key:Counter(text['text'].split()) for key,text in candidates.items()}
        count=len(documents);average=max(1,sum(sum(c.values()) for c in documents.values())/count)
        scores={}
        for key,counts in documents.items():
            score=0
            for term in ['needle','quartz']:
                frequency=sum(term in c for c in documents.values());tf=counts[term]
                if tf:score+=math.log1p((count-frequency+.5)/(frequency+.5))*tf*2.2/(tf+1.2*(.25+.75*sum(counts.values())/average))
            scores[key]=score
        return sorted(candidates,key=lambda key:(-scores[key],key))[:limit],scores
    original_search=Documents.search;searches=[]
    def record_search(self,*args,**kwargs):
        result=original_search(self,*args,**kwargs);searches.append((str(self.db.db_path.resolve()),kwargs.get('limit',5),len(result['results'])));return result
    monkeypatch.setattr(Documents,'search',record_search)
    marker=len(w.calls)
    for limit in [1,50]:
        local=w.local.search(query,local=True,limit=limit)['results'];remote=w.search_hub(query=query,limit=limit)['results']
        wanted,scores=expected(local,remote,limit);result=w.local.search(query,limit=limit)
        assert [identity(h) for h in result['results']]==wanted
        assert all(abs(h['rerank_score']-scores[identity(h)])<1e-9 for h in result['results'])
        for h in result['results']:assert_text(w.local.read(h),known[identity(h)],h['start'],h['end'])
        assert all(n<=requested for _,requested,n in searches)
    result=w.local.search(query,limit=50);assert set(map(identity,result['results']))==set(known)
    combined=next(h for h in result['results'] if identity(h)==(w.device,w.archive,shared_id,1))
    assert combined['archive_scope']=='combined' and len(combined['origin_references'])==2
    wire=json.dumps(w.calls[marker:]);assert 'privateonlynonce' not in wire and 'private-1.txt' not in wire and 'private-2.txt' not in wire
    for route,payload in w.calls[marker:]:
        if route=='/documents/search':
            assert set(payload)<={'hub_id','document_epoch','query','limit','scope','project_id','scope_reference','device_id','archive_id'}
            assert payload['query']==query
        elif route=='/documents/read':assert set(payload)<={'hub_id','document_epoch','reference','start','end'}

    assert {payload['limit'] for route,payload in w.calls[marker:] if route=='/documents/search'}=={1,50}
    stable=[identity(h) for h in result['results']];request=federation._request
    def reverse(config,route,payload=None):
        result=request(config,route,payload)
        if route=='/documents/search':result['results'].reverse()
        return result
    monkeypatch.setattr(federation,'_request',reverse);assert [identity(h) for h in w.local.search(query,limit=50)['results']]==stable
    # A conflicting copy must not be merged with the trustworthy Local original.
    def corrupt(config,route,payload=None):
        result=request(config,route,payload)
        if route=='/documents/search':
            h=next(h for h in result['results'] if h['origin']['document_id']==shared_id);h['text_sha256']='f'*64
        return result
    monkeypatch.setattr(federation,'_request',corrupt);bad=w.local.search(query,limit=50)
    assert bad['coverage']['hub']=='partial' and bad['candidate_failures']
    retained=next(h for h in bad['results'] if identity(h)==(w.device,w.archive,shared_id,1));assert retained['archive_scope']=='local';assert_text(w.local.read(retained),known[identity(retained)])
    monkeypatch.setattr(federation,'_request',request)
    path.write_text('needle quartz privateonlynonce new version');w.local.refresh(source)
    versions=[h for h in w.local.search(query,limit=50)['results'] if h['origin']['document_id']==shared_id]
    assert {h['version'] for h in versions}=={1,2} and len(versions)==2
    for h in versions:assert_text(w.local.read(h),'needle needle quartz short' if h['version']==1 else 'needle quartz privateonlynonce new version')
    # Another valid device with identical bytes remains an independent candidate.
    other={**w.protocol('e'*32),'device_id':'e'*32,'archive_id':'f'*32};w.control(other);doc=w.doc('needle needle quartz short');w.stage(other,doc);w.publish(w.manifest(other,[doc]))
    duplicates=[h for h in w.local.search(query,limit=50)['results'] if h['text']=='needle needle quartz short'];assert len(duplicates)==2
    assert {h['origin']['device_id'] for h in duplicates}=={w.device,'e'*32}


# @case-id: TC-007-search-fallback
def test_search_fallback(w,monkeypatch):
    p,q,r=w.project('P'),w.project('Q'),w.project('Local R');w.pair.local.link_projects(p,r)
    paths=[]
    for name,project in [('P',p),('Q',q),('R',r)]:
        path,_=w.source(name+'.txt','needle '+name+' private',[project]);paths.append(path)
    # First query performs minimal registration, without authorizing body.
    initial=w.local.search('needle',scope='project',project_id=p)
    assert initial['archive_scope']=='combined' and initial['coverage']['hub']=='complete'
    hp,hq=w.hub_project_for(p),w.hub_project_for(q);projects=HubProjects(w.pair.remote);projects.link(hp['id'],hq['id'])
    native=w.hub_project();w.upload(native,'hub.txt','needle Hub available',hub=True);projects.link(hp['id'],native['id'])
    def values(result):return set(w.docs(result).values())
    root={'scope':'project','project_id':p,'limit':50}
    scope_requests=[];request=federation._request
    def capture(config,route,payload=None):
        result=request(config,route,payload)
        if route=='/query-scope':scope_requests.append((deepcopy(payload),deepcopy(result)))
        return result
    local_search=Documents.search;local_scopes=[]
    def capture_local(self,*args,**kw):
        if self.db.db_path.resolve()==w.pair.local.db_path.resolve():local_scopes.append(deepcopy(kw))
        return local_search(self,*args,**kw)
    monkeypatch.setattr(federation,'_request',capture);marker=len(w.calls)
    with monkeypatch.context() as trace:
        trace.setattr(Documents,'search',capture_local)
        connected=w.local.search('needle',**root)
    assert values(connected)=={'needle P private','needle Q private','needle Hub available'}
    assert len(local_scopes)==1 and set(local_scopes[0]['exact_project_ids'])=={p,q}
    assert len(scope_requests)==1
    frozen=scope_requests[0][1];assert {p['id'] for p in frozen['effective_projects']}=={hp['id'],hq['id'],native['id']}
    searches=[payload for route,payload in w.calls[marker:] if route=='/documents/search'];assert len(searches)==1 and searches[0]['scope_reference']==frozen['scope_reference']
    assert {p['id'] for p in connected['effective_projects']}=={hp['id'],hq['id'],native['id']}
    monkeypatch.setattr(federation,'_request',request)
    request=federation._request;attempts=[]
    def offline(*args,**kwargs):attempts.append(args);raise federation.HubUnavailable('synthetic disconnected')
    monkeypatch.setattr(federation,'_request',offline)
    fallback=w.local.search('needle',**root);assert values(fallback)=={'needle P private'} and fallback['coverage']['hub']=='unavailable' and fallback['fallback_reason']
    marker=len(attempts)
    with monkeypatch.context() as m:
        attempts_source=deny_source_reads(m,*paths);local=w.local.search('needle',local=True,**root)
        assert values(local)=={'needle P private','needle R private'} and len(attempts)==marker and attempts_source==[] and local['coverage']['hub']=='not_requested'
    # Deliberately collide namespaces; offline Hub root must not guess this Local.
    monkeypatch.setattr(federation,'_request',request)
    while max(x['id'] for x in w.pair.local.projects())<native['id']:w.project('ID filler')
    collision=next(x['id'] for x in w.pair.local.projects() if x['id']==native['id']);w.source('collision.txt','needle collision must not leak',[collision])
    monkeypatch.setattr(federation,'_request',offline)
    remote_root=w.local.search('needle',scope='project',hub_project_id=native['id'],limit=50)
    assert remote_root['results']==[] and remote_root['fallback_reason'] and remote_root['coverage']['hub']=='unavailable'
    for options in [{'scope':'project','project_id':p,'hub_project_id':native['id']},{'scope':'project','hub_project_id':native['id'],'local':True},{'scope':'all','project_id':p},{'scope':'project','project_id':999999},{'scope':'project','hub_project_id':-1},{'scope':'all','hub_project_id':native['id']}]:
        w.local.bad('POST','/api/documents/search',{'query':'needle',**options})
    monkeypatch.setattr(federation,'_request',request)
    zero=w.local.search('zero-no-match',**root);assert zero['results']==[] and zero['coverage']['hub']=='complete' and zero['coverage']['local']=='complete' and not zero['fallback_reason']
    def old(config,route,payload=None):
        result=request(config,route,payload)
        if route=='/info':result['capabilities']=[c for c in result['capabilities'] if not c.startswith('documents-')]
        return result
    monkeypatch.setattr(federation,'_request',old);limited=w.local.search('needle',**root);assert limited['fallback_reason'] and values(limited)=={'needle P private'}
    assert limited['coverage']['hub']=='unsupported' and limited['coverage']['hub']!=fallback['coverage']['hub']
    # Invalid signature preserves its routing payload, so the Hub rejects the
    # signed scope; it cannot be silently retained for a wider Local search.
    def invalid_scope(config,route,payload=None):
        result=request(config,route,payload)
        if route=='/query-scope':result['scope_reference']=result['scope_reference'][:-1]+('0' if result['scope_reference'][-1]!='0' else '1')
        return result
    monkeypatch.setattr(federation,'_request',invalid_scope);invalid=w.local.search('needle',**root);assert invalid['fallback_reason'] and values(invalid)=={'needle P private'}
    for status,wanted in [(None,{'needle P private','needle Q private'}),(409,{'needle P private'})]:
        def after_scope(config,route,payload=None):
            if route=='/documents/search':
                error=federation.HubUnavailable('after shared scope');error.status=status;raise error
            return request(config,route,payload)
        monkeypatch.setattr(federation,'_request',after_scope);result=w.local.search('needle',**root)
        assert values(result)==wanted and result['fallback_reason'] and result['coverage']['hub']=='unavailable'
    monkeypatch.setattr(federation,'_request',request)
    # Local-only failure cannot discard a usable authenticated Hub candidate.
    search=Documents.search
    def local_failure(self,*args,**kw):
        if self.db.db_path.resolve()==w.pair.local.db_path.resolve():raise ValueError('synthetic local query failure')
        return search(self,*args,**kw)
    with monkeypatch.context() as m:
        m.setattr(Documents,'search',local_failure);result=w.local.search('needle',**root)
        assert values(result)=={'needle Hub available'} and result['coverage']['local']=='partial' and result['candidate_failures']


# @case-id: TC-007-read-exact
def test_read_exact(w,monkeypatch):
    text='\ufeff前言😀e\u0301\r\nneedle 命中\r尾部\n'+('长'*16050)+'😀尾巴'
    project=w.project();path,source=w.source('unicode.txt',text,[project])
    old_local=w.local.search('needle',local=True)['results'][0]
    w.policy(project);w.sync();remote=w.search_hub()['results'][0]
    combined=w.local.search('needle')['results'][0];assert combined['archive_scope']=='combined'
    hp=w.hub_project();native_asset=w.upload(hp,'native.md',text+'native independent',hub=True)
    native=next(h for h in w.search_hub(limit=50)['results'] if h['id']==native_asset['id'])
    # A valid different body is available at each endpoint, making wrong routing visible.
    local_negative,_=w.source('local-negative.txt','needle wrong LOCAL source',[project])
    w.upload(hp,'remote-negative.md','needle wrong HUB source',hub=True)
    path.unlink() # neither a Hub path nor the original Local path is reachable
    with monkeypatch.context() as m:
        attempts=deny_source_reads(m,path,local_negative,Path(native_asset['path']))
        for h,isremote,expected in [(old_local,False,text),(remote,True,text),(combined,False,text),(native,True,text+'native independent')]:
            length=len(normal(expected))
            for start,end in [(1,10),(length-8,length),*[(x,min(length,x+16000)) for x in range(0,length,16000)]]:
                actual=w.read_hub(h,start=start,end=end) if isremote else w.local.read(h,start=start,end=end)
                assert_text(actual,expected,start,end)
            actual=w.read_hub(h) if isremote else w.local.read(h)
            assert_text(actual,expected,h['start'],h['end'])
        assert attempts==[]
    # Invalid Local qualification only; exact bundled Hub copy remains valid.
    w.local.set(source,project_ids=[project])
    actual=w.local.read(combined,start=0,end=30);assert_text(actual,text,0,30);assert actual['archive_scope']=='hub'
    # Invalid Hub endpoint only; the original exact Local citation remains valid.
    path.write_bytes(text.encode());w.local.refresh(source);w.sync()
    fresh=w.local.search('needle',limit=50)['results'];bundle=next(h for h in fresh if h['origin']['document_id']==old_local['origin']['document_id'])
    assert bundle['archive_scope']=='combined'
    original=federation._request
    def unavailable(config,route,payload=None):
        if route=='/documents/read':raise federation.HubUnavailable('only Hub read disconnected')
        return original(config,route,payload)
    monkeypatch.setattr(federation,'_request',unavailable)
    actual=w.local.read(bundle,start=0,end=30);assert_text(actual,text,0,30);assert actual['archive_scope']=='local'


# @case-id: TC-007-read-rejection
def test_read_rejection(w):
    from smm_local.archive_protocol import sign
    project=w.project();path,source=w.source('ref.txt','needle original 😀',[project]);w.policy(project);w.sync()
    hit=w.search_hub()['results'][0];combined=w.local.search('needle')['results'][0]
    ref=hit['reference'];payload=references.routing_metadata(ref);key=references.material(w.pair.remote)[1]
    inner=references.routing_metadata(payload['reference'])
    for start,end in [(-1,2),(0,0),(2,1),(0,16001),(True,2),(0,99999)]:
        w.reject_remote('POST','/documents/read',{**w.context(),'reference':ref,'start':start,'end':end})
    w.reject_remote('POST','/documents/read',{**w.context(),'reference':ref[:-4]+'aaaa'})
    for field in ['document_epoch','hub_id','archive_id','kind']:
        for value in ['f'*32,False,-1]:
            w.reject_remote('POST','/documents/read',{**w.context(),'reference':sign({**payload,field:value},key)})
    for field in ['device_id','archive_id','document_id']:
        for value in ['f'*32,False,-1]:
            forged=deepcopy(payload);forged['origin'][field]=value
            w.reject_remote('POST','/documents/read',{**w.context(),'reference':sign(forged,key)})
    for field in ['archive_id','document_id','version']:
        for value in (['f'*32,False,-1] if field!='version' else [hit['version']+1,False,-1]):
            wrong=sign({**inner,field:value},key);forged={**payload,'reference':wrong}
            w.reject_remote('POST','/documents/read',{**w.context(),'reference':sign(forged,key)})
    for field in ['id','revision','qualification']:
        for value in (['f'*32,False,-1] if field=='id' else [inner['sources'][0][field]+1,False,-1]):
            nested=deepcopy(inner);nested['sources'][0][field]=value
            w.reject_remote('POST','/documents/read',{**w.context(),'reference':sign({**payload,'reference':sign(nested,key)},key)})
    # Unchanged reingest and new process preserve these exact old citations.
    w.local.refresh(source);w.sync();w.local=Fixture(w.root/'restart',db=Archive(w.pair.local.db_path))
    assert_text(w.read_hub(hit),'needle original 😀');assert_text(w.local.read(combined),'needle original 😀')
    conversation=seed_conversation(w.local);w.local.bad('POST','/api/documents/read',{'reference':conversation['reference']})
    # A new independent source can serve new refs, never lend qualification to old refs.
    path.unlink();w.local.refresh(source);w.sync();path.write_text('needle original 😀');w.local.refresh(source)
    fresh_source=w.local.add(path,[project]);w.local.refresh(fresh_source);w.sync()
    w.reject_remote('POST','/documents/read',{**w.context(),'reference':ref})
    w.local.bad('POST','/api/documents/read',{'reference':combined['reference']})
    latest=w.search_hub()['results'][0];assert_text(w.read_hub(latest),'needle original 😀')
    w.local.remove(source);w.local.remove(fresh_source);w.sync()
    w.reject_remote('POST','/documents/read',{**w.context(),'reference':latest['reference']})
    w.local.bad('POST','/api/documents/read',{'reference':combined['reference']})


# @case-id: TC-007-compatibility
def test_compatibility(w,monkeypatch,tmp_path):
    import asyncio
    from smm_local.mcp_server import create_mcp
    def legacy_state(db):
        with db.connect() as c:
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in {'settings','messages','conversations','hub_managed_devices'} or r[0].startswith(('local_upload_','upload_message_','hub_upload_','hub_policy_','hub_vibeinsight_'))]
            return {name:[dict(r) for r in c.execute('SELECT * FROM '+name+' ORDER BY 1')] for name in sorted(names)}
    from test_vibeinsight_sync import FixtureSource,event
    from smm_hub.vibeinsight import VibeInsightSync
    VibeInsightSync(w.pair.remote,'fixture',batch_size=2).run(FixtureSource([event(0,'legacy-vibe-a','user',text='legacyvibenonce A'),event(1,'legacy-vibe-b','assistant',text='legacyvibenonce B')],['git.example/team/alpha']))
    first=add_local(w.pair,'codex-old','Codex P','compatnonce codex original')
    root=tmp_path/'claude';root.mkdir()
    event={'type':'user','uuid':'claude-message','sessionId':'claude-old','cwd':str(root/'P'),'message':{'role':'user','content':'compatnonce claude original'}}
    (root/'old.jsonl').write_text(json.dumps(event)+'\n');w.pair.local.sync_claude(root)
    hits=federation.search_archive(w.pair.local,'compatnonce',local=True)['results'];assert len(hits)==2
    originals={h['source_session_id']:h['reference'] for h in hits}
    # Actual legacy 005 policies, catalog/receipt and pause state remain identical.
    for mode in ['none','only','all']:
        selected=[first['project_id']] if mode=='only' else []
        federation.choose_upload(w.pair.local,mode,selected);federation.push_pending(w.pair.local)
        for paused in [False,True]:
            w.pair.local.set_settings(sync_paused=paused)
            project=w.project('Docs '+mode+str(paused));path=w.local.file(mode+str(paused)+'.txt','needle isolated '+mode+str(paused))
            source=w.local.add(path,[project]);before_local=legacy_state(w.pair.local);before_hub=legacy_state(w.pair.remote)
            with monkeypatch.context() as m:
                marker=len(w.calls)
                # A source refresh may schedule minimal metadata, never body or old dialogue policy changes.
                w.local.refresh(source);hit=Documents(w.pair.local).search('isolated')['results'][0]
                assert 'isolated' in w.local.read(hit)['text'];w.local.remove(source)
                wire=json.dumps(w.calls[marker:]);assert 'needle isolated '+mode+str(paused) not in wire
            assert legacy_state(w.pair.local)==before_local and legacy_state(w.pair.remote)==before_hub
            assert w.pair.local.get_settings()['sync_paused']==paused
    for session,text in [('codex-old','compatnonce codex original'),('claude-old','compatnonce claude original')]:
        read=federation.read_archive(w.pair.local,reference=originals[session]);assert [m['text'] for m in read['messages']]==[text]
    # Public old local API and all three actual MCP calls, on an archive without Hub.
    local=Fixture(tmp_path/'standalone');project=local.project();path=local.file('readonly.txt','needle MCP independent 😀\nline2');src=local.add(path,[project]);local.refresh(src)
    server=create_mcp(local.db);tools={t.name:t for t in asyncio.run(server.list_tools())}
    assert {name for name in tools if 'document' in name}=={'list_document_sources','search_documents','read_document'}
    for name in ['list_document_sources','search_documents','read_document']:
        assert tools[name].annotations.readOnlyHint is True and tools[name].annotations.destructiveHint is False
    before=document_state(local);settings=local.db.get_settings()
    with monkeypatch.context() as m:
        m.setattr(federation,'_request',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('local archive attempted network')))
        attempts=deny_source_reads(m,path)
        hit=local.search('needle')['results'][0];assert_text(local.read(hit),'needle MCP independent 😀\nline2')
        def tool(name,args):return json.loads(asyncio.run(server.call_tool(name,args))[0][0].text)
        listed=tool('list_document_sources',{});assert {x['id'] for x in listed}=={src['id']}
        result=tool('search_documents',{'query':'needle'});assert len(result['results'])==1
        actual=tool('read_document',{'reference':result['results'][0]['reference']});assert_text(actual,'needle MCP independent 😀\nline2')
        assert document_state(local)==before and local.db.get_settings()==settings and attempts==[]
    # The legacy public regression assertions execute, not merely import.
    command=[sys.executable,'-m','pytest','-q','tests/test_005_contracts.py','tests/test_upload_policy.py','tests/test_upload_isolation.py','tests/test_vibeinsight_sync.py','tests/test_vibeinsight_boundaries.py','tests/test_cli_help.py']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=120)
    observe('legacy-dialogue-policy-vibeinsight-regression',{'argv':command,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    assert result.returncode==0,result.stdout+result.stderr


# @case-id: TC-007-packages
def test_packages(tmp_path):
    uv=shutil.which('uv') or str(Path.home()/'.local/bin/uv')
    out=tmp_path/'packages'
    run=subprocess.run([sys.executable,'scripts/acceptance/hub_documents_packages.py','--uv',uv,'--output',str(out)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=240)
    observe('current-independent-packages',{'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    assert run.returncode==0,run.stderr
    data=json.loads((out/'result.json').read_text())
    assert data['status']=='passed' and len(data['wheels'])==2
    assert set(data['source_wheel_install_sha256'])=={'local','hub'}
    assert all(c['exit_code']==0 for c in data['commands'])


# @case-id: TC-007-library-ingest
def test_library_ingest(w,tmp_path):
    import os
    def state(hub):return(w.snapshot() if hub else document_state(w.local),w.disk(w.pair.remote.db_path.parent if hub else w.pair.local.db_path.parent))
    for hub in [False,True]:
        projects=[w.hub_project('P'+str(i)) if hub else w.local.request('POST','/api/projects',{'name':'P'+str(i)}) for i in range(2)]
        for i,project in enumerate(projects):
            raws=[('\ufeffneedle 项目'+str(i)+'😀\r\nA').encode(),('needle 项目'+str(i)+' e\u0301\rB').encode()]
            saved=[w.upload(project,'same.txt',raw=raw,hub=hub) for raw in raws]
            assert len({a['id'] for a in saved})==2
            for receipt,raw in zip(saved,raws):
                assert receipt['project_ids']==[project['id']] and receipt['version']==1 and receipt['source_revision']==1
                assert receipt['display_name']=='same.txt' and Path(receipt['path']).read_bytes()==raw
                # Storage belongs to this archive, is hidden and UUID-isolated.
                root=Path(receipt['path']).parent.parent
                assert root.name.startswith('.') and root.parent==(w.pair.remote.db_path.parent if hub else w.pair.local.db_path.parent)
            options={'query':'needle','scope':'project','project_id':project['id'],'limit':50}
            result=w.search_hub(**options) if hub else w.local.search(**options,local=True)
            assert {h['id'] for h in result['results']}=={a['id'] for a in saved}
            expected={a['id']:raw for a,raw in zip(saved,raws)}
            for hit in result['results']:
                assert hit['display_name']=='same.txt';raw=expected[hit['id']]
                assert hit['sha256']==sha(raw) and hit['text_sha256']==sha(normal(raw.decode('utf-8')).encode())
                assert_text(w.read_hub(hit) if hub else w.local.read(hit),raw.decode('utf-8'))
        project=projects[0];submission=uuid4().hex
        first=w.upload(project,'once.md',text='needle idempotent',submission=submission,hub=hub)
        assert w.upload(project,'once.md',text='needle idempotent',submission=submission,hub=hub)==first
        route='/documents/library' if hub else '/api/documents/library'
        base={'project_id':project['id'],'submission_id':uuid4().hex,'name':'ok.txt','content_base64':base64.b64encode(b'needle').decode()}
        if hub:base.update(w.project_context(project))
        invalid=[{'submission_id':submission,'name':'once.md','content_base64':base64.b64encode(b'different').decode()}]
        invalid += [{'name':name} for name in ['../escape.txt','..\\escape.txt','/tmp/escape.txt','dir/file.txt','C:\\tmp.txt','nul.txt','aux.md','CON.TXT','colon:name.txt','trailing.txt ','bad\x00.txt']]
        invalid += [{'content_base64':base64.b64encode(raw).decode()} for raw in [b'\xffinvalid',b'has\x00nul',b'x'*(FILE_LIMIT+1)]]
        invalid += [{'name':'unsupported.pdf'},{'content_base64':'not-base64!!'},{'path':str(tmp_path/'client-chosen.txt')},{'storage_path':str(tmp_path/'client-chosen.txt')}]
        for change in invalid:
            before=state(hub)
            if hub:w.reject_remote('POST',route,{**base,**change})
            else:w.local.bad('POST',route,{**base,**change})
            assert state(hub)==before
        assert not (tmp_path/'client-chosen.txt').exists()
        # Linking the actual SMM root must not turn an allowed upload into a
        # write through another directory; all other request fields are valid.
        root=Path(first['path']).parent.parent;real=root.with_name(root.name+'-real');root.rename(real)
        def files(directory):return {str(f.relative_to(directory)):(sha(f.read_bytes()),f.stat().st_size,f.stat().st_mtime_ns) for f in directory.rglob('*') if f.is_file()}
        try:
            if os.name=='nt':
                link=subprocess.run(['cmd','/c','mklink','/J',str(root),str(real)],capture_output=True);assert link.returncode==0,link.stderr
            else:root.symlink_to(real,target_is_directory=True)
            before=files(real);before_db=w.snapshot() if hub else document_state(w.local)
            if hub:w.reject_remote('POST',route,{**base,'submission_id':uuid4().hex,'name':'linked.txt'})
            else:w.local.bad('POST',route,{**base,'submission_id':uuid4().hex,'name':'linked.txt'})
            assert files(real)==before
            assert (w.snapshot() if hub else document_state(w.local))==before_db
        finally:
            if root.is_symlink():root.unlink()
            elif root.exists():os.rmdir(root) # Windows junction only, never real
            real.rename(root)
        # Exact boundary is saved raw and read through every Unicode codepoint,
        # including its tail. One-byte excess above was otherwise valid UTF8.
        raw=b'needle '+b'x'*(FILE_LIMIT-7);large=w.upload(project,'exact-limit.txt',raw=raw,hub=hub)
        assert Path(large['path']).read_bytes()==raw
        result=w.search_hub(query='needle',scope='project',project_id=project['id'],limit=50) if hub else w.local.search('needle',scope='project',project_id=project['id'],local=True,limit=50)
        hit=next(h for h in result['results'] if h['id']==large['id']);assert hit['text_length']==FILE_LIMIT and hit['sha256']==sha(raw)
        for start in range(0,FILE_LIMIT,16000):
            end=min(FILE_LIMIT,start+16000);actual=w.read_hub(hit,start=start,end=end) if hub else w.local.read(hit,start=start,end=end)
            assert_text(actual,raw.decode(),start,end)
        empty=w.upload(project,'empty.txt',raw=b'',hub=hub);assert Path(empty['path']).read_bytes()==b''
        result=w.search_hub(query='needle',scope='project',project_id=project['id'],limit=50) if hub else w.local.search('needle',scope='project',project_id=project['id'],local=True,limit=50)
        assert empty['id'] not in {h['id'] for h in result['results']}
        # Interior dots are a legal display name, not a traversal segment.
        w.upload(project,'legal..name.txt',text='needle legal name',hub=hub)


# @case-id: TC-007-library-update
def test_library_update(w,monkeypatch):
    def request(hub,method,route,body):return w.remote(method,route,body) if hub else w.local.request(method,'/api'+route,body)
    def reject(hub,method,route,body):return w.reject_remote(method,route,body) if hub else w.local.bad(method,'/api'+route,body)
    def query(hub,project):return w.search_hub(scope='project',project_id=project['id'],limit=50) if hub else w.local.search('needle',scope='project',project_id=project['id'],local=True,limit=50)
    def read(hub,hit):return w.read_hub(hit) if hub else w.local.read(hit)
    def body(hub,project,asset,**extra):
        return {'project_id':project['id'],'expected_version':asset['version'],'expected_revision':asset['source_revision'],'submission_id':uuid4().hex,**(w.project_context(project) if hub else {}),**extra}
    def state(hub):return (w.snapshot() if hub else document_state(w.local),w.disk(w.pair.remote.db_path.parent if hub else w.pair.local.db_path.parent))
    for hub in [False,True]:
        project=w.hub_project('Editable') if hub else w.local.request('POST','/api/projects',{'name':'Editable'})
        negative_project=w.hub_project('Negative') if hub else w.local.request('POST','/api/projects',{'name':'Negative'})
        originals=[w.upload(project,'same.txt',text='needle original '+str(i),hub=hub) for i in [1,2]]
        negative=w.upload(negative_project,'same.txt',text='needle untouched',hub=hub)
        old={h['id']:h for h in query(hub,project)['results']};new_refs={}
        for i,asset in enumerate(originals,1):
            route='/documents/library/'+asset['id'];text='needle replacement '+str(i)+'😀\nline2';raw=text.encode()
            update=body(hub,project,asset,content_base64=base64.b64encode(raw).decode());updated=request(hub,'PUT',route,update)
            assert updated['id']==asset['id'] and updated['version']==asset['version']+1
            assert updated['path']==asset['path'] and updated['display_name']=='same.txt' and updated['project_ids']==[project['id']]
            assert Path(updated['path']).read_bytes()==raw
            assert request(hub,'PUT',route,update)==updated # same submission, even though its expected version is now old
            snapshot=state(hub);reject(hub,'PUT',route,{**update,'content_base64':base64.b64encode(b'needle altered retry').decode()});assert state(hub)==snapshot
            hit=next(h for h in query(hub,project)['results'] if h['id']==asset['id']);assert_text(read(hub,hit),text)
            reject(hub,'POST','/documents/read',({**w.context(),'reference':old[asset['id']]['reference']} if hub else {'reference':old[asset['id']]['reference']}))
            # Only the content-version CAS is stale; the source revision remains current.
            snapshot=state(hub);reject(hub,'PUT',route,body(hub,project,updated,expected_version=asset['version'],content_base64=base64.b64encode(b'needle stale version').decode()));assert state(hub)==snapshot
            # Change source config explicitly, then refresh its own managed copy.
            config={'project_ids':[project['id']],'exclude':[],'recursive':True,**(w.project_context(project) if hub else {})}
            request(hub,'PUT','/documents/sources/'+asset['source_id'],config)
            if hub:
                result=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents','refresh','--source-id',asset['source_id']],capture_output=True,text=True,encoding='utf-8');assert result.returncode==0,result.stderr
            else:w.local.refresh({'id':asset['source_id']})
            rows=w.remote('GET','/documents/library?project_id='+str(project['id'])) if hub else w.local.request('GET','/api/documents/library?project_id='+str(project['id']))
            current=next(x for x in rows if x['id']==asset['id']);assert current['source_revision']>updated['source_revision'] and current['version']==updated['version']
            # Only source revision is stale; content version is now current.
            snapshot=state(hub);reject(hub,'PUT',route,body(hub,project,current,expected_revision=updated['source_revision'],content_base64=base64.b64encode(b'needle stale config').decode()));assert state(hub)==snapshot
            current_hit=next(h for h in query(hub,project)['results'] if h['id']==asset['id'])
            same=request(hub,'PUT',route,body(hub,project,current,content_base64=base64.b64encode(raw).decode()))
            assert same['version']==current['version'] and same['path']==asset['path'];assert_text(read(hub,current_hit),text)
            # Actual atomic file replacement is interrupted after replacement.
            # Preserve the complete published version and its raw copy on failure.
            import os
            original_replace=os.replace;injected={'done':False}
            def interrupt(src,dst):
                value=original_replace(src,dst)
                if Path(dst)==Path(same['path']) and not injected['done']:
                    injected['done']=True;raise OSError('synthetic interruption after managed replace')
                return value
            with monkeypatch.context() as m:
                m.setattr(os,'replace',interrupt)
                reject(hub,'PUT',route,body(hub,project,same,content_base64=base64.b64encode(b'needle interrupted half').decode()))
            assert injected['done'] and Path(same['path']).read_bytes()==raw
            assert_text(read(hub,current_hit),text)
            final=next(x for x in (w.remote('GET','/documents/library?project_id='+str(project['id'])) if hub else w.local.request('GET','/api/documents/library?project_id='+str(project['id']))) if x['id']==asset['id'])
            for stale in [{'expected_version':asset['version']},{'expected_revision':asset['source_revision']}]:
                assert final['version']>asset['version'] and final['source_revision']>asset['source_revision']
                before=state(hub);reject(hub,'DELETE',route,body(hub,project,final,**stale));assert state(hub)==before
            request(hub,'DELETE',route,body(hub,project,final))
            assert asset['id'] not in {h['id'] for h in query(hub,project)['results']}
            reject(hub,'POST','/documents/read',({**w.context(),'reference':current_hit['reference']} if hub else {'reference':current_hit['reference']}))
        negative_hit=next(h for h in query(hub,negative_project)['results'] if h['id']==negative['id']);assert_text(read(hub,negative_hit),'needle untouched')
        sid='deleted-'+str(hub);doomed=w.upload(project,'gone.txt',text='needle gone',submission=sid,hub=hub)
        request(hub,'DELETE','/documents/library/'+doomed['id'],body(hub,project,doomed))
        replay={'project_id':project['id'],'name':'gone.txt','submission_id':sid,'content_base64':base64.b64encode(b'needle gone').decode(),**(w.project_context(project) if hub else {})}
        snapshot=state(hub);reject(hub,'POST','/documents/library',replay);assert state(hub)==snapshot
    # Both states start with already-published files, before the pause decision.
    for paused in [False,True]:
        project=w.local.request('POST','/api/projects',{'name':'Sync lifecycle '+str(paused)})
        assets=[w.upload(project,'sync.txt',text='syncnonce original '+str(i),submission='state-'+str(paused)+'-'+str(i)) for i in [1,2]]
        w.policy(project['id']);w.sync();hp=w.hub_project_for(project['id'])
        old={h['origin']['document_id']:h for h in w.search_hub(query='syncnonce',scope='project',project_id=hp['id'],limit=50)['results']}
        if paused:w.policy(project['id'],False)
        for i,asset in enumerate(assets,1):
            raw=('syncnonce replacement '+str(i)).encode();request(False,'PUT','/documents/library/'+asset['id'],body(False,project,asset,content_base64=base64.b64encode(raw).decode()))
        w.sync();actual=w.search_hub(query='syncnonce',scope='project',project_id=hp['id'],limit=50)
        for h in actual['results']:
            i=next(i for i,a in enumerate(assets,1) if a['id']==h['origin']['document_id'])
            assert_text(w.read_hub(h),'syncnonce '+('original ' if paused else 'replacement ')+str(i))
        assert len(actual['results'])==2
        current=w.local.request('GET','/api/documents/library?project_id='+str(project['id']))
        for asset in current:request(False,'DELETE','/documents/library/'+asset['id'],body(False,project,asset))
        w.sync();assert w.search_hub(query='syncnonce',scope='project',project_id=hp['id'])['results']==[]
        for old_hit in old.values():w.reject_remote('POST','/documents/read',{**w.context(),'reference':old_hit['reference']})


# @case-id: TC-007-project-ownership
def test_project_ownership(w,tmp_path):
    import time
    local_project=w.local.request('POST','/api/projects',{'name':'private-local-owner-nonce'})
    local_asset=w.upload(local_project,'owned.txt','needle local owned');w.policy(local_project['id']);w.sync()
    projected=w.hub_project_for(local_project['id']);hub_project=w.hub_project('private-hub-owner-nonce');native=w.upload(hub_project,'owned.txt','needle Hub owned',hub=True)
    def state():return(w.snapshot(),w.disk(w.pair.remote.db_path.parent))
    def update_body(project,asset,**extra):
        return {**w.project_context(project),'expected_version':asset['version'],'expected_revision':asset['source_revision'],'submission_id':uuid4().hex,'content_base64':base64.b64encode(b'needle valid replacement').decode(),**extra}
    # The actual creator is held in the DB. Neither correct project keys nor
    # an association can give a device/VibeInsight projection native write rights.
    projects=HubProjects(w.pair.remote)
    with w.pair.remote.connect() as c:
        other_id=projects.upsert(c,'device','c'*32,'d'*32,'Other device')
        external_id=projects.upsert(c,'vibeinsight','fixture','e'*32,'Vibe readonly')
    readonly_projects=[p for p in projects.list() if p['id'] in {projected['id'],other_id,external_id}]
    assert len(readonly_projects)==3
    projects.link(hub_project['id'],projected['id'])
    external_path=tmp_path/'external Hub.txt';external_path.write_text('needle native external')
    for project in readonly_projects:
        before=state();context={**w.context(),'project_id':project['id'],'project_key':project['source_key']}
        w.reject_remote('POST','/documents/library',{**context,'name':'forged.txt','submission_id':uuid4().hex,'content_base64':base64.b64encode(b'needle forbidden').decode()});assert state()==before
        w.reject_remote('POST','/documents/sources',{**context,'path':str(external_path),'project_ids':[project['id']],'exclude':[],'recursive':True});assert state()==before
        # Source config has a genuine native source and otherwise-current context;
        # only its proposed destination is a read-only external projection.
        w.reject_remote('PUT','/documents/sources/'+native['source_id'],{**w.project_context(hub_project),'project_ids':[project['id']],'exclude':[],'recursive':True});assert state()==before
    hit=next(h for h in w.search_hub(limit=50)['results'] if h['origin']['document_id']==local_asset['id'])
    replica_source=next(s for s in w.remote('GET','/documents/sources') if s['id'] in hit['source_ids'])
    replica={'id':hit['id'],'version':hit['version'],'source_revision':replica_source['revision']}
    project_context={**w.context(),'project_id':projected['id'],'project_key':projected['source_key']}
    for method in ['PUT','DELETE']:
        body={**project_context,'expected_version':replica['version'],'expected_revision':replica['source_revision']}
        if method=='PUT':body.update(submission_id=uuid4().hex,content_base64=base64.b64encode(b'needle forbidden').decode())
        before=state();w.reject_remote(method,'/documents/library/'+replica['id'],body);assert state()==before
    before=state();w.reject_remote('PUT','/documents/sources/'+replica_source['id'],{**project_context,'project_ids':[hub_project['id']],'exclude':[],'recursive':True});assert state()==before
    # Out-of-domain values are checked independently for every relevant route.
    for invalid in [-1,True,'not-an-id']:
        for method,route,body in [('POST','/documents/library',{**w.project_context(hub_project),'name':'bad.txt','submission_id':uuid4().hex,'content_base64':'bmVlZGxl','project_id':invalid}),('PUT','/documents/library/'+native['id'],update_body(hub_project,native,project_id=invalid)),('DELETE','/documents/library/'+native['id'],{**w.project_context(hub_project),'expected_version':native['version'],'expected_revision':native['source_revision'],'project_id':invalid}),('PUT','/documents/sources/'+native['source_id'],{**w.project_context(hub_project),'project_ids':[invalid],'exclude':[],'recursive':True})]:
            before=state();w.reject_remote(method,route,body);assert state()==before
    for invalid in ['not-uuid','f'*32,'-1','true']:
        for method in ['PUT','DELETE']:
            body=update_body(hub_project,native)
            if method=='DELETE':body={k:v for k,v in body.items() if k not in {'content_base64','submission_id'}}
            before=state();w.reject_remote(method,'/documents/library/'+invalid,body);assert state()==before
        before=state();w.reject_remote('PUT','/documents/sources/'+invalid,{**w.project_context(hub_project),'project_ids':[hub_project['id']],'exclude':[],'recursive':True});assert state()==before
    # A Hub-created numeric root unavailable locally cannot be a local CRUD root.
    while hub_project['id'] in {p['id'] for p in w.pair.local.projects()}:hub_project=w.hub_project('Remote only numeric root')
    before_remote=state();before_local=document_state(w.local);before_disk=w.disk(w.pair.local.db_path.parent)
    body={'project_id':hub_project['id'],'name':'proxy.txt','submission_id':uuid4().hex,'content_base64':'bmVlZGxl'}
    w.local.bad('POST','/api/documents/library',body)
    for method in ['PUT','DELETE']:
        body={'project_id':local_project['id'],'expected_version':native['version'],'expected_revision':native['source_revision']}
        if method=='PUT':body.update(submission_id=uuid4().hex,content_base64='bmVlZGxl')
        w.local.bad(method,'/api/documents/library/'+native['id'],body)
    w.local.bad('PUT','/api/documents/sources/'+native['source_id'],{'project_ids':[local_project['id']],'exclude':[],'recursive':True})
    assert state()==before_remote and document_state(w.local)==before_local and w.disk(w.pair.local.db_path.parent)==before_disk
    r=w.local.client.post('/api/hub/documents/library',json={**w.context(),'name':'proxy.txt','content_base64':'bmVlZGxl'});assert 400<=r.status_code<500 and state()==before_remote
    # Generate a genuinely old epoch with maintenance recovery, then make all
    # non-epoch fields current using newly created own assets.
    def cli(*args,code=0):
        result=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        observe('ownership-cli',{'argv':args,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr});assert result.returncode==code,result.stderr
        return json.loads(result.stdout) if code==0 else result
    old_context=w.context();status=cli('documents','recovery-status');cli('documents','recover','--expected-state',status['state'])
    assert w.context()['document_epoch']!=old_context['document_epoch']
    native=w.upload(hub_project,'current.txt','needle current owned',hub=True)
    own_other=w.hub_project('Another own root');config_asset=w.upload(hub_project,'config.txt','needle config owned',hub=True)
    with TestClient(create_hub(Archive(tmp_path/'other-context'/'smm-hub.sqlite3'),'z'*48),headers={'Authorization':'Bearer '+('z'*48)}) as other:
        other_hid=other.get('/v1/info').json()['hub_id']
    operations=[('POST','/projects',{**w.context(),'name':'Current new root','kind':'ordinary'}),('POST','/documents/library',{**w.project_context(hub_project),'name':'context.txt','submission_id':uuid4().hex,'content_base64':base64.b64encode(b'needle context').decode()}),('PUT','/documents/library/'+native['id'],update_body(hub_project,native)),('DELETE','/documents/library/'+native['id'],{**w.project_context(hub_project),'expected_version':native['version'],'expected_revision':native['source_revision']}),('PUT','/documents/sources/'+config_asset['source_id'],{**w.project_context(hub_project),'project_ids':[hub_project['id']],'exclude':[],'recursive':True})]
    for method,route,body in operations:
        variants=[{'hub_id':other_hid},{'document_epoch':old_context['document_epoch']}]
        if 'project_key' in body:variants.append({'project_key':own_other['source_key']})
        for change in variants:
            before=state();w.reject_remote(method,route,{**body,**change});assert state()==before
    # Current-context positive controls for every operation, with exact contents.
    w.remote('POST',operations[0][1],operations[0][2]);w.remote('POST',operations[1][1],operations[1][2])
    updated=w.remote('PUT',operations[2][1],operations[2][2]);assert updated['version']==native['version']+1
    current_hit=next(h for h in w.search_hub(limit=50)['results'] if h['id']==native['id']);assert_text(w.read_hub(current_hit),'needle valid replacement')
    w.remote('DELETE',operations[3][1],{**w.project_context(hub_project),'expected_version':updated['version'],'expected_revision':updated['source_revision']})
    w.remote('PUT',operations[4][1],{**operations[4][2],'project_ids':[hub_project['id'],own_other['id']]})
    cli('documents','refresh','--source-id',config_asset['source_id'])
    assert any(h['id']==config_asset['id'] for h in w.search_hub(scope='project',project_id=own_other['id'])['results'])
    # Empty Authorization overrides TestClient's default bearer. Test both absent
    # authentication semantics and a wrong credential on all live data routes.
    for auth in ['', 'Bearer wrong']:
        r=w.hub.get('/',headers={'Authorization':auth});assert r.status_code==200
        assert 'private-local-owner-nonce' not in r.text and 'private-hub-owner-nonce' not in r.text and 'needle config owned' not in r.text
        for method,route,body in [('GET','/projects',None),('GET','/documents/sources',None),('GET','/documents/library',None),('POST','/documents/search',{**w.context(),'query':'needle'}),*operations]:
            before=state();r=w.hub.request(method,'/v1'+route,json=body,headers={'Authorization':auth});assert r.status_code==401,r.text;assert state()==before
    token=w.pair.token_file.read_text()
    for route in ['/api/status','/api/projects','/api/settings','/api/documents/sync-status']:
        r=w.local.client.get(route);assert r.status_code==200 and token not in r.text
    # Real CLI epoch race. Intercept only its initial context read, using a new
    # child process; every business action still goes through the actual parser.
    source_path=tmp_path/'cli-epoch.txt';source_path.write_text('cliEpochNonce V1')
    source=cli('documents','add',source_path,'--project-id',hub_project['id']);cli('documents','refresh','--source-id',source['id'])
    old_hit=w.search_hub(query='cliEpochNonce')['results'][0];source_path.write_text('cliEpochNonce V2')
    arrived,release=tmp_path/'cli-arrived.json',tmp_path/'cli-release'
    argv=['smm-hub','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents','refresh','--source-id',source['id']]
    code='\n'.join(['import json,pathlib,sys,time','from smm_hub.documents import HubDocuments','from smm_hub.cli import main',
         'original=HubDocuments.context','paused=False',
         'def intercept(self):',' global paused',' value=original(self)',' if not paused:',
         '  paused=True','  pathlib.Path('+repr(str(arrived))+').write_text(json.dumps(value))',
         '  deadline=time.monotonic()+20','  while not pathlib.Path('+repr(str(release))+').exists():',
         '   assert time.monotonic()<deadline, "release missing"','   time.sleep(.01)',' return value',
         'HubDocuments.context=intercept','sys.argv='+repr(argv),'main()'])
    log=tmp_path/'cli-epoch.log'
    race_context=w.context();race_status=cli('documents','recovery-status')
    with log.open('wb') as stream:
        child=subprocess.Popen([sys.executable,'-c',code],stdout=stream,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+15
        while not arrived.exists():
            assert child.poll() is None,log.read_text(errors='replace');assert time.monotonic()<deadline,'CLI context seam not reached';time.sleep(.02)
        captured=json.loads(arrived.read_text());assert captured==race_context
        status=race_status
        recovery=subprocess.Popen([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents','recover','--expected-state',status['state']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        recovered_first=False
        try:
            try:recovery.wait(timeout=3);recovered_first=True
            except subprocess.TimeoutExpired:pass
        finally:
            release.touch();child.wait(timeout=15);stdout,stderr=recovery.communicate(timeout=15)
        assert recovery.returncode in {0,2},stderr.decode(errors='replace')
    observe('actual-cli-epoch-race',{'argv':argv,'captured':captured,'recovery_completed_before_release':recovered_first,'cli_pid':child.pid,'cli_exit':child.returncode,'cli_log':log.read_text(errors='replace'),'recovery_exit':recovery.returncode,'recovery_stdout':stdout.decode(errors='replace'),'recovery_stderr':stderr.decode(errors='replace')})
    assert (recovery.returncode,child.returncode) in {(0,2),(2,0)},'stale write or stale recovery was accepted (or both operations failed)'
    if recovery.returncode==2:
        # The write won and made the original recovery-state stale. Recheck the
        # new state before maintenance; neither path may overwrite a newer one.
        fresh_status=cli('documents','recovery-status');cli('documents','recover','--expected-state',fresh_status['state'])
    assert w.search_hub(query='cliEpochNonce')['results']==[]
    w.reject_remote('POST','/documents/read',{**w.context(),'reference':old_hit['reference']})
    cli('documents','refresh','--source-id',source['id']);assert_text(w.read_hub(w.search_hub(query='cliEpochNonce')['results'][0]),'cliEpochNonce V2')
    from scripts.acceptance.hub_documents_checks import stopped
    stopped([child.pid,recovery.pid],[])

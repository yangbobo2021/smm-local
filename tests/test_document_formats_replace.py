"""Creator-owned replacement failure and latest saved-candidate CLI retry."""
from copy import deepcopy
import hashlib,json,subprocess,sys,time
from itertools import count
from pathlib import Path
from uuid import uuid4
import pytest
from document_helpers import observe,deny_source_reads
from document_formats_upload_fixture import upload_input
from document_formats_partial_fixture import partial_pdf
from document_formats_sync_observer import install as query_guard
from test_document_formats_retry import ENGINE,DATA,FONT,scan_pdf,keep,child_source_guard
from test_hub_documents_contracts import w

pytestmark=pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires prepared creator OCR assets; skipped is not platform acceptance')
DOWNLOAD=count(1)


def business_state(db,configuration=True):
    with db.connect() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%' OR name LIKE 'hub_document_%') ORDER BY name") if not r[0].startswith('document_fts')]
        if not configuration:tables=[t for t in tables if t not in {'document_processing_config','document_processing_probe'}]
        return {t:sorted([dict(r) for r in c.execute('SELECT * FROM "'+t+'"')],key=lambda row:json.dumps(row,sort_keys=True,default=str)) for t in tables}


def transfer_state(db):
    root=db.db_path.resolve().parent
    return {str(p.relative_to(root)):(len(raw),hashlib.sha256(raw).hexdigest()) for p in root.rglob('*') if p.is_file() and '.documents' in str(p.relative_to(root)) and not p.name.endswith('.lock') for raw in [p.read_bytes()]}



def assert_new_scan(value,expected):
    assert value['format']=='pdf' and value['processing_status']=='ready' and value['profile']['config_revision']==1
    assert value['tables']==[] and value['coverage']['errors']==[]
    units=value['coverage']['units'];assert len(units)==1
    assert units[0]['page']==1 and units[0]['method']=='ocr' and units[0]['status']=='ready' and units[0]['languages']=='chi_sim+eng'
    lines=expected.splitlines();locations=value['locations'];assert len(locations)==len(lines)
    for line,loc in zip(lines,locations):
        assert loc['page']==1 and loc['method']=='ocr' and loc['page_width']==600 and loc['page_height']==180 and loc['rotation']==0
        assert 0<=loc['confidence']<=100 and len(loc['bbox'])==4
        x0,y0,x1,y1=loc['bbox'];assert 0<=x0<x1<=1 and 0<=y0<y1<=1
        assert ''.join(value['text'][loc['start']:loc['end']].split())==''.join(line.split())

@pytest.mark.parametrize('owner',['local','hub'])
def test_managed_replace_failed_candidate_retries_saved_new_bytes(w,tmp_path,monkeypatch,owner):
    # TC-008-managed-replace-retry
    db=w.pair.local if owner=='local' else w.pair.remote
    client=w.local.client if owner=='local' else w.hub;prefix='/api' if owner=='local' else '/v1'
    ctx={} if owner=='local' else w.context()
    projects=([w.local.request('POST','/api/projects',{'name':'008 replace'}),w.local.request('POST','/api/projects/global')] if owner=='local' else [w.hub_project('008 replace'),w.hub_project('008 global',kind='global')])
    counter=count(1)
    def request(method,path,body=None,raw=None,headers=None,reject=False):
        kwargs={'headers':headers or {}}
        if raw is not None:kwargs['content']=raw
        elif body is not None:kwargs['json']=body
        r=client.request(method,prefix+path,**kwargs)
        value=r.json() if 'json' in r.headers.get('content-type','') else {'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()}
        observe('replace-'+owner,{'method':method,'path':path,'request':body,'raw_bytes':len(raw) if raw else None,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw else None,'status':r.status_code,'response':value})
        assert (400<=r.status_code<500) if reject else r.status_code==200,r.text
        return r
    def cli(*args):
        argv=([sys.executable,'-B','-m','smm_local.cli','--db',str(db.db_path),'documents'] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(db.db_path.parent),'documents'])+list(map(str,args))
        r=subprocess.run(argv,cwd=w.root,capture_output=True,text=True,encoding='utf-8',timeout=90)
        observe('replace-cli-'+owner,{'argv':argv,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        assert r.returncode==0,r.stderr
        return json.loads(r.stdout)
    def listed():
        rows=request('GET','/documents/files').json();library={r['id']:r for r in request('GET','/documents/library').json()};result={}
        assert {r['id'] for r in rows}==set(library)
        for row in rows:
            for key in ('version','processing_version','published_snapshot','latest_attempt','retry_target'):
                assert row[key]==library[row['id']][key]
        for row in rows:
            if row['id'] in result:
                for k in ('version','processing_version','published_snapshot','latest_attempt','retry_target'):assert row[k]==result[row['id']][k]
            result[row['id']]={**row,'source_revision':library[row['id']]['source_revision']}
        return result
    def wait(ident):
        deadline=time.monotonic()+35
        while True:
            e=listed()[ident]
            if e['latest_attempt']['status'] in {'ready','partial','failed'}:return e
            assert time.monotonic()<deadline,e
            time.sleep(.02)
    def begin_body(item,raw,extra=None):
        p=item['project']
        return {**ctx,'project_id':p['id'],'project_key':p['stable_key'] if owner=='local' else p['source_key'],'submission_id':owner+str(next(counter))+uuid4().hex,'name':item['name'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),**(extra or {})}
    def upload(item,raw,extra=None,before_commit=None):
        body=begin_body(item,raw,extra);reply=request('POST','/documents/uploads',body).json();uid=reply['upload_id']
        for i,offset in enumerate(range(0,len(raw),reply['block_bytes'])):
            part=raw[offset:offset+reply['block_bytes']]
            request('PUT','/documents/uploads/'+uid+'/parts/'+str(i),raw=part,headers={'X-Chunk-SHA256':hashlib.sha256(part).hexdigest()})
        if before_commit:before_commit()
        receipt=request('POST','/documents/uploads/'+uid+'/commit',ctx).json()
        return uid,receipt,wait(receipt['document_id'])
    def compare(e):
        return {'document_id':e['id'],'expected_version':e['version'],'expected_processing_version':e['processing_version'],'expected_revision':e['source_revision'],'capture_id':e['latest_attempt']['capture_id'],'expected_attempt_id':e['latest_attempt']['attempt_id']}
    all_items=[]
    for status in ('ready','partial'):
        for n,project in enumerate(projects):
            label=owner[0].upper()+status[0].upper()+('A' if n==0 else 'B')
            raw,truth=upload_input('pdf',label) if status=='ready' else partial_pdf(label,FONT)
            if status=='partial':truth={'words':[truth['anchor']],'tables':[],'partial':truth}
            newraw=scan_pdf(label)
            item={'name':label+'.pdf','project':project,'raw':raw,'truth':truth,'anchor':truth['words'][0].split()[0],'newraw':newraw,'newtext':label+' RETRY 73428\nCAPTURED ORIGINAL 12345.67','status':status,'stage':'initial'}
            keep('inputs/'+item['name'],raw);keep('inputs/new-'+item['name'],newraw);keep('truth/new-'+item['name']+'.json',json.dumps({'text':item['newtext'],'page':1,'width':600,'height':180,'tables':[],'method':'ocr'}).encode());keep('truth/'+item['name']+'.json',json.dumps(truth,ensure_ascii=False).encode())
            uid,receipt,entry=upload(item,raw);item.update(uid=uid,receipt=receipt,id=entry['id'],entry=entry);all_items.append(item)
    raw,truth=upload_input('docx',owner+'control');control={'name':owner+'control.docx','project':projects[0],'raw':raw,'truth':truth,'anchor':truth['words'][0].split()[0],'status':'ready','stage':'initial'}
    keep('inputs/'+control['name'],raw);keep('truth/'+control['name']+'.json',json.dumps(truth,ensure_ascii=False).encode())
    uid,receipt,entry=upload(control,raw);control.update(uid=uid,receipt=receipt,id=entry['id'],entry=entry);all_items.append(control)
    ids={item['id'] for item in all_items};assert len(ids)==5 and set(listed())==ids
    def snapshot(item,reference=None):
        success=item['stage']=='success';raw=item['newraw'] if success else item['raw'];version=2 if success else 1
        query=item['newtext'].split()[0] if success else item['anchor']
        hits=request('POST','/documents/search',{**ctx,'query':query,'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
        own=[h for h in hits if h['id']==item['id']];assert len(own)==1,hits
        h=own[0];assert h['version']==h['processing_version']==version and h['sha256']==hashlib.sha256(raw).hexdigest()
        ref=reference or h['reference'];value=request('POST','/documents/read',{**ctx,'reference':ref,'start':0,'end':h['text_length']}).json()
        assert value['id']==item['id'] and value['version']==value['processing_version']==version and value['sha256']==h['sha256']
        if success:
            assert ''.join(value['text'].split())==''.join(item['newtext'].split())
            assert_new_scan(value,item['newtext'])
            for key in ('format','processing_status','profile','coverage','locations','tables','result_sha256'):assert h[key]==value[key]
        else:
            assert all(word in value['text'] for word in item['truth']['words'])
            assert value['processing_status']==item['status']
            if item['status']=='partial':
                assert value['text']==item['truth']['words'][0]
                assert any(e['page']==2 and e['method']=='ocr' and '组件探测' in e['reason'] for e in value['coverage']['errors'])
        tables=[request('POST','/documents/read',{**ctx,'reference':ref,'view':'table','table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,'column_start':1,'column_end':t['columns']+1}).json() for t in value['tables']]
        if not success:
            assert len(tables)==len(item['truth']['tables'])
            for expected in item['truth']['tables']:
                found=[t for t in tables if all(t['location'].get(k)==v for k,v in expected['location'].items()) and any(c['text']==expected['cells'][0][2] for c in t['cells'])]
                assert len(found)==1
                t=found[0];assert (t['rows'],t['columns'])==(expected['rows'],expected['columns'])
                actual=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in t['cells']]
                assert len(actual)==len(expected['cells']) and set(actual)==set(expected['cells'])
        info=request('POST','/documents/read',{**ctx,'reference':ref,'view':'original-info'}).json()
        assert info['id']==item['id'] and info['version']==info['processing_version']==version and info['sha256']==h['sha256'] and info['bytes']==len(raw) and info['available'] is True
        assert info['origin']==value['origin'] and info['origin']['document_id']==item['id']
        assert info['origin']['device_id']==(w.device if owner=='local' else ctx['hub_id'])
        download=request('POST','/documents/original',{**ctx,'reference':ref}).content
        keep('downloads/'+hashlib.sha256(download).hexdigest()+'-'+item['name'],download);assert download==raw
        return {'reference':ref,'read':value,'tables':tables,'info':info,'raw_sha256':hashlib.sha256(download).hexdigest()}
    for item in all_items:
        assert item['entry']['version']==item['entry']['processing_version']==1
        assert item['entry']['latest_attempt']['status']==item['status']
        item['baseline']=snapshot(item)
    def assert_publications():
        before=business_state(db);entries=listed();assert set(entries)==ids
        for item in all_items:
            e=entries[item['id']];old=item['entry'];success=item['stage']=='success'
            assert e['version']==e['processing_version']==(2 if success else 1)
            if success:assert e['published_snapshot']['capture_id']==item['failed']['latest_attempt']['capture_id']
            else:assert e['published_snapshot']==old['published_snapshot']
            if item['stage']=='failed':
                assert e['latest_attempt']==item['failed']['latest_attempt'] and e['retry_target']==item['failed']['retry_target']
            elif item['stage']=='initial':assert e['latest_attempt']==old['latest_attempt']
            expected=item['success_baseline'] if success else item['baseline']
            assert snapshot(item,expected['reference'])==expected
        assert business_state(db)==before
    def guarded_publications():
        paths=[Path(e['path']) for e in listed().values()]
        with monkeypatch.context() as guard:
            processing=query_guard(guard);reads=deny_source_reads(guard,*paths)
            assert_publications();assert processing==[] and reads==[]
    for item in all_items[:-1]:
        uid,receipt,e=upload(item,item['newraw'],compare(listed()[item['id']]),guarded_publications)
        old=item['entry'];latest=e['latest_attempt'];target=e['retry_target']
        assert receipt['document_id']==item['id'] and latest['status']=='failed'
        assert latest['capture_id']==receipt['capture_id']!=old['latest_attempt']['capture_id'] and latest['attempt_id']==receipt['attempt_id']!=old['latest_attempt']['attempt_id']
        assert latest['config_revision']==0 and target['sha256']==hashlib.sha256(item['newraw']).hexdigest()
        assert target['capture_id']==latest['capture_id'] and target['expected_attempt_id']==latest['attempt_id']
        assert target['expected_version']==target['expected_processing_version']==1
        item.update(stage='failed',failed=e,new_uid=uid);guarded_publications()
        before=business_state(db);disk=transfer_state(db)
        replay=request('POST','/documents/uploads/'+uid+'/commit',ctx).json()
        assert replay['capture_id']==receipt['capture_id'] and replay['attempt_id']==receipt['attempt_id'] and replay['status']=='failed'
        assert business_state(db)==before and transfer_state(db)==disk
        peer=next(v for v in all_items[:-1] if v['id']!=item['id'] and v['project']['id']==item['project']['id']);peer_e=listed()[peer['id']]
        valid=begin_body(item,item['newraw'],compare(e))
        changes=[('capture_id',old['latest_attempt']['capture_id']),('capture_id',peer_e['latest_attempt']['capture_id']),('expected_attempt_id',old['latest_attempt']['attempt_id']),('expected_attempt_id',peer_e['latest_attempt']['attempt_id']),('expected_version',2),('expected_processing_version',2),('expected_revision',e['source_revision']+1),('project_key',projects[1 if item['project']==projects[0] else 0]['stable_key' if owner=='local' else 'source_key']),('document_id',peer['id']),('name','wrong.xlsx')]
        if owner=='hub':changes += [('hub_id','f'*32),('document_epoch','f'*32)]
        bodies=[{**valid,k:v,'submission_id':uuid4().hex} for k,v in changes]+[begin_body(item,item['newraw'],compare(old))]
        for bad in bodies:
            before=business_state(db);disk=transfer_state(db)
            request('POST','/documents/uploads',bad,reject=True)
            assert business_state(db)==before and transfer_state(db)==disk
        before=business_state(db);disk=transfer_state(db)
        request('POST','/documents/uploads/'+item['uid']+'/commit',ctx,reject=True)
        assert business_state(db)==before and transfer_state(db)==disk
    assert len({i['failed']['latest_attempt']['capture_id'] for i in all_items[:-1]})==len({i['failed']['latest_attempt']['attempt_id'] for i in all_items[:-1]})==4
    before=business_state(db,configuration=False);status=cli('processing-status')
    assert status['config']['revision']==0
    configured=cli('processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    assert configured['config']['revision']==1 and business_state(db,configuration=False)==before
    guarded_publications()
    paths=[Path(e['path']) for e in listed().values()]
    for p in paths:p.unlink()
    log=child_source_guard(tmp_path,paths,monkeypatch);reads=deny_source_reads(monkeypatch,*paths)
    for item in all_items[:-1]:
        e=listed()[item['id']];target=e['retry_target'];args=['reprocess','--document-id',item['id']]
        for k in ('capture_id','expected_attempt_id','expected_version','expected_processing_version'):args+=['--'+k.replace('_','-'),target[k]]
        answer=cli(*args);current=listed()[item['id']];a=current['latest_attempt']
        assert answer['document_id']==item['id'] and a['capture_id']==target['capture_id'] and a['attempt_id']!=target['expected_attempt_id']
        assert a['status']=='ready' and a['config_revision']==1 and a['error'] is None and a['finished_at']
        assert current['version']==current['processing_version']==2
        old=item['baseline'];item['stage']='success';item['success_baseline']=snapshot(item)
        for view in ('text','original-info'):
            request('POST','/documents/read',{**ctx,'reference':old['reference'],'view':view},reject=True)
        for t in old['tables']:request('POST','/documents/read',{**ctx,'reference':old['reference'],'view':'table','table_id':t['table_id']},reject=True)
        request('POST','/documents/original',{**ctx,'reference':old['reference']},reject=True)
        guarded_publications()
    assert reads==[] and (not log.exists() or log.read_text()=='')
    observe('replacement-retry-complete-'+owner,{'document_ids':sorted(ids),'replaced_ids':[i['id'] for i in all_items[:-1]],'control':control['id'],'source_reads':reads,'child_source_reads':log.read_text() if log.exists() else ''})

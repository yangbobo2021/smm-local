"""C1 same-project expansion; original service helper stays unchanged."""
import hashlib,json,time,os,subprocess,sys,sqlite3
from pathlib import Path
import pytest
from document_helpers import observe
from document_formats_upload_fixture import upload_input
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server
from test_document_formats_installed_minimum import assert_complete_source_text

@pytest.mark.parametrize('owner',['local','hub'])
def test_real_creator_restart_resumes_chunks_and_pending_captures(tmp_path,owner):
    # TC-008-managed-upload-restart: four targets per creator, two in each project.
    server=Server(tmp_path/owner,owner);items=[]
    try:
        server.start()
        if owner=='local':
            projects=[server.call('POST','/projects',{'name':'restart ordinary'}).json(),server.call('POST','/projects/global').json()]
        else:
            projects=[server.call('POST','/projects',{**server.context,'name':'restart '+kind,'kind':kind}).json() for kind in ('ordinary','global')]
        for key,project in (('alpha',projects[0]),('beta',projects[0]),('gamma',projects[1]),('delta',projects[1])):
            label=owner+'restart'+key;raw,truth=upload_input('docx',label)
            truth['ordered_groups']=[truth['words'][:12]]
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
        listed=server.call('GET','/documents/files').json();assert len(listed)==4
        assert len({item['receipt']['document_id'] for item in items})==4
        for item in items:
            row=next(row for row in listed if row['id']==item['receipt']['document_id'])
            assert row['published_snapshot'] is None and row['version']==row['processing_version']==0
            assert row['latest_attempt']['status']=='pending' and row['latest_attempt']['attempt_id']==item['receipt']['attempt_id'] and row['latest_attempt']['capture_id']==item['receipt']['capture_id']
            item['pending_attempt']=row['latest_attempt']
            assert item['pending_attempt']['config_revision']==0 and item['pending_attempt']['created_at']
            assert row['original_reference'] is None and row['original_available'] is False
            item['path']=Path(row['path'])
        for project in projects:
            own={i['receipt']['document_id'] for i in items if i['project']['id']==project['id']};assert len(own)==2
            own_rows=server.call('GET','/documents/library?project_id='+str(project['id'])).json()
            assert len(own_rows)==len({e['id'] for e in own_rows})==len(own)
            assert {e['id'] for e in own_rows}==own
        stopped=server.stop();assert stopped['pause_events'] and stopped['audit']==[]
        for item in items:item['path'].unlink()
        server.start(deny=[item['path'] for item in items])
        until=time.monotonic()+45
        while True:
            listed=server.call('GET','/documents/files').json()
            assert len(listed)==len({row['id'] for row in listed})==len(items)
            if len(listed)==4 and all((row.get('latest_attempt') or {}).get('status')=='failed' or (row.get('published_snapshot') is not None and (row.get('latest_attempt') or {}).get('status') in {'ready','partial'} and row['published_snapshot']['capture_id']==row['latest_attempt']['capture_id']) for row in listed):break
            assert time.monotonic()<until,{'phase':'captured jobs did not resume after actual process restart','files':listed}
            time.sleep(.1)
        def verify_all(phase):
            listed=server.call('GET','/documents/files').json()
            assert {row['id'] for row in listed}=={item['receipt']['document_id'] for item in items}
            for item in items:
                ident=item['receipt']['document_id'];entry=next(row for row in listed if row['id']==ident)
                assert entry['version']==entry['processing_version']==1 and entry['published_snapshot']['status']=='ready'
                assert entry['latest_attempt']['attempt_id']==item['receipt']['attempt_id'] and entry['latest_attempt']['capture_id']==item['receipt']['capture_id']
                for field in ('attempt_id','capture_id','config_revision','created_at'):
                    assert entry['latest_attempt'][field]==item['pending_attempt'][field],(phase,item['label'],field)
                assert entry['latest_attempt']['status']=='ready' and entry['latest_attempt']['finished_at'] and entry['latest_attempt']['error'] is None
                hits=server.call('POST','/documents/search',{**server.context,'query':item['label'],'scope':'project','project_id':item['project']['id'],**({'local':True} if owner=='local' else {})}).json()['results']
                assert len(hits)==1 and hits[0]['id']==ident and hits[0]['version']==hits[0]['processing_version']==1
                other=projects[1] if item['project']['id']==projects[0]['id'] else projects[0]
                assert server.call('POST','/documents/search',{**server.context,'query':item['label'],'scope':'project','project_id':other['id'],**({'local':True} if owner=='local' else {})}).json()['results']==[]
                hit=hits[0];assert hit['sha256']==hashlib.sha256(item['raw']).hexdigest()
                reference=item.setdefault('reference',hit['reference'])
                read=server.call('POST','/documents/read',{**server.context,'reference':reference,'start':0,'end':hit['text_length']}).json()
                assert read['profile']['config_revision']==item['pending_attempt']['config_revision']==0
                assert read['id']==ident and all(word not in read['text'] for word in item['truth']['excluded'])
                assert_complete_source_text(read['text'],item['truth'])
                assert read['text']==item.setdefault('complete_text',read['text'])
                assert len(read['tables'])==len(item['truth']['tables'])
                for expected in item['truth']['tables']:
                    table=next(t for t in read['tables'] if all(t['location'].get(k)==v for k,v in expected['location'].items()))
                    view=server.call('POST','/documents/read',{**server.context,'reference':reference,'view':'table','table_id':table['table_id'],'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1}).json()
                    actual=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
                    assert (view['rows'],view['columns'])==(expected['rows'],expected['columns']) and len(actual)==len(expected['cells']) and set(actual)==set(expected['cells'])
                    views=item.setdefault('complete_tables',{})
                    assert view==views.setdefault(table['table_id'],view)
                response=server.call('POST','/documents/original',{**server.context,'reference':reference})
                actual_sha=hashlib.sha256(response.content).hexdigest()
                keep('downloads/'+actual_sha+'.docx',response.content);assert response.content==item['raw']
                observe('restart-original-download',{'owner':owner,'phase':phase,'document_id':ident,'sha256':actual_sha,'bytes':len(response.content),'source_label':item['label']})
                receipt=server.call('POST','/documents/uploads/'+item['upload']+'/commit',server.context).json()
                assert all(receipt[k]==item['receipt'][k] for k in ('document_id','capture_id','attempt_id')) and receipt['status']=='ready'
            assert len(server.call('GET','/documents/library').json())==4
            for project in projects:
                own={i['receipt']['document_id'] for i in items if i['project']['id']==project['id']}
                rows=server.call('GET','/documents/library?project_id='+str(project['id'])).json()
                assert len(rows)==len({e['id'] for e in rows})==len(own) and {e['id'] for e in rows}==own
            assert not any(event['event']=='open' for event in server.events())
        verify_all('resumed')
        stopped=server.stop();assert len([e for e in stopped['audit'] if e['event']=='subprocess.Popen'])==4
        server.start(deny=[item['path'] for item in items]);verify_all('stable-restart')
        stopped=server.stop();assert stopped['forced'] is False and stopped['audit']==[]
    finally:server.stop()


@pytest.mark.parametrize('owner',['local','hub'])
def test_restart_preserves_partial_empty_and_old_publication_with_pending_replacement(tmp_path,owner,monkeypatch):
    from test_document_formats_retry import ENGINE,DATA,FONT
    if not all((ENGINE,DATA,FONT)):
        pytest.skip('explicit real OCR configuration required for restart state matrix')
    from document_formats_partial_fixture import partial_pdf
    from document_formats_managed_empty_fixture import blank_original
    from test_document_formats_management import native_input
    server=Server(tmp_path/owner,owner);items=[]
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    def listed():
        rows=server.call('GET','/documents/files').json()
        assert len(rows)==len({row['id'] for row in rows})==len(items)
        return {row['id']:row for row in rows}
    def library(item):
        rows=server.call('GET','/documents/library?project_id='+str(item['project']['id'])).json()
        assert len(rows)==len({r['id'] for r in rows})
        return next(r for r in rows if r['id']==item['id'])
    def submit(item,raw,replacement=False):
        project=item['project'];body={**server.context,'project_id':project['id'],
            'project_key':project['stable_key'] if owner=='local' else project['source_key'],
            'submission_id':item['key']+('new' if replacement else 'old'),'name':item['key']+'.'+item['format'],
            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        if replacement:
            entry=library(item)
            body.update(document_id=item['id'],expected_version=entry['version'],expected_processing_version=entry['processing_version'],
                expected_revision=entry['source_revision'],capture_id=entry['latest_attempt']['capture_id'],expected_attempt_id=entry['latest_attempt']['attempt_id'])
        start=server.call('POST','/documents/uploads',body).json()
        for number,offset in enumerate(range(0,len(raw),start['block_bytes'])):
            chunk=raw[offset:offset+start['block_bytes']]
            server.call('PUT','/documents/uploads/'+start['upload_id']+'/parts/'+str(number),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
        return server.call('POST','/documents/uploads/'+start['upload_id']+'/commit',server.context).json()
    def wait_ready():
        until=time.monotonic()+45
        while True:
            current=listed()
            if all(row['latest_attempt']['status'] in {'ready','partial','empty-success','failed'} for row in current.values()):return current
            assert time.monotonic()<until,'saved state matrix did not settle'
            time.sleep(.03)
    def check_lists():
        current=listed()
        for project in projects:
            expected={item['id'] for item in items if item['project']['id']==project['id']}
            rows=server.call('GET','/documents/library?project_id='+str(project['id'])).json()
            assert len(rows)==len({r['id'] for r in rows})==len(expected) and {r['id'] for r in rows}==expected
        return current
    def check_attempts(phase):
        current=listed()
        for item in items:
            actual=current[item['id']]['latest_attempt']
            if phase=='initial' or item['status']!='replacement':
                assert actual==item['initial_attempt']
            else:
                expected=item['pending_attempt']
                for field in ('attempt_id','capture_id','config_revision','created_at'):
                    assert actual[field]==expected[field],(phase,item['key'],field)
                assert expected['attempt_id']==item['pending']['attempt_id']
                assert expected['capture_id']==item['pending']['capture_id']
                if phase=='pending':assert actual==expected and actual['status']=='pending'
                else:
                    assert actual['status']=='ready' and actual['finished_at'] and actual['error'] is None
                    assert current[item['id']]['published_snapshot']['capture_id']==expected['capture_id']
        return current
    def business_state():
        with sqlite3.connect(server.db) as connection:
            names=[r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%' OR name LIKE 'hub_document_%' OR name LIKE 'hub_processed_%')")]
            return {name:sorted([list(r) for r in connection.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,default=str)) for name in names}
    def snapshot(item,reference=None,new=False):
        entry=listed()[item['id']];raw=item['new_raw'] if new else item['raw'];truth=item['new_truth'] if new else item['truth']
        version=2 if new else 1;status='ready' if item['status']=='replacement' else item['status'];ref=reference or entry['original_reference']
        if status=='empty-success':
            info=server.call('POST','/documents/read',{**server.context,'reference':ref,'view':'original-info'}).json()
            assert info['id']==item['id'] and info['version']==info['processing_version']==1
            assert info['text_length']==0 and info['processing_status']=='empty-success'
            assert info['available'] is True and info['bytes']==len(raw) and info['sha256']==hashlib.sha256(raw).hexdigest()
            original=server.call('POST','/documents/original',{**server.context,'reference':ref}).content;assert original==raw
            keep('restart-states/downloads/'+hashlib.sha256(original).hexdigest(),original)
            return {'reference':ref,'original_info':info,'text_length':0}
        length=len(item['old']['text']) if item.get('old',{}).get('reference')==ref else entry['text_length']
        value=server.call('POST','/documents/read',{**server.context,'reference':ref,'start':0,'end':length}).json()
        assert value['id']==item['id'] and value['version']==value['processing_version']==version and value['processing_status']==status
        assert value['sha256']==hashlib.sha256(raw).hexdigest()
        assert_complete_source_text(value['text'],truth)
        assert all(w not in value['text'] for w in truth['excluded'])
        assert len(value['tables'])==len(truth['tables']);tables=[];matched=set()
        for summary in value['tables']:
            table=server.call('POST','/documents/read',{**server.context,'reference':ref,'view':'table','table_id':summary['table_id'],
                'row_start':1,'row_end':summary['rows']+1,'column_start':1,'column_end':summary['columns']+1}).json()
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in table['cells']]
            matches=[i for i,t in enumerate(truth['tables']) if (table['rows'],table['columns'])==(t['rows'],t['columns']) and
                len(cells)==len(t['cells']) and set(cells)==set(t['cells']) and all(table['location'].get(k)==v for k,v in t['location'].items())]
            assert len(matches)==1 and matches[0] not in matched;matched.add(matches[0]);tables.append(table)
        assert matched==set(range(len(truth['tables'])))
        original=server.call('POST','/documents/original',{**server.context,'reference':ref}).content;assert original==raw
        keep('restart-states/downloads/'+hashlib.sha256(original).hexdigest(),original)
        if status=='partial':
            assert any(e['page']==2 and '1600万像素' in e['reason'] for e in value['coverage']['errors'])
        if truth['words']:
            query=truth['words'][0].split()[0];body={**server.context,'query':query,'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}
            hits=server.call('POST','/documents/search',body).json()['results'];assert len(hits)==1 and hits[0]['id']==item['id'] and hits[0]['sha256']==value['sha256']
            other=projects[1] if item['project']['id']==projects[0]['id'] else projects[0]
            assert server.call('POST','/documents/search',{**body,'project_id':other['id']}).json()['results']==[]
        else:assert value['text']=='' and value['tables']==[]
        return {'reference':ref,'text':value['text'],'tables':tables,'coverage':value['coverage'],'profile':value['profile'],'sha256':value['sha256']}
    try:
        server.start()
        prefix=[sys.executable,'-B','-m','smm_local.cli','--db',str(server.db),'documents'] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(server.root),'documents']
        command=prefix+['processing-configure','--expected-revision','0','--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng']
        setup=subprocess.run(command,capture_output=True,timeout=30);assert setup.returncode==0,setup.stderr
        assert json.loads(setup.stdout)['ocr']['ready'] is True
        projects=[server.call('POST','/projects',{'name':'state ordinary'}).json(),server.call('POST','/projects/global').json()] if owner=='local' else [server.call('POST','/projects',{**server.context,'name':'state '+kind,'kind':kind}).json() for kind in ('ordinary','global')]
        for group,project in enumerate(projects):
            for status in ('partial','empty-success','replacement'):
                for number in (1,2):
                    key=owner+'state'+str(group)+status.replace('-','')+str(number)
                    if status=='partial':
                        raw,t=partial_pdf(key,FONT);truth={'words':[t['anchor']],'excluded':[],'tables':[]};format='pdf'
                    elif status=='empty-success':raw=blank_original('docx',key);truth={'words':[],'excluded':[],'tables':[]};format='docx'
                    else:
                        raw,truth=native_input('docx',key+'Old');truth['ordered_groups']=[truth['words'][:12]];format='docx'
                    item={'key':key,'project':project,'format':format,'status':status,'raw':raw,'truth':truth}
                    if status=='replacement':
                        item['new_raw'],item['new_truth']=native_input('docx',key+'New');item['new_truth']['ordered_groups']=[item['new_truth']['words'][:12]]
                    keep('restart-states/inputs/'+key,raw);keep('restart-states/truth/'+key+'.json',json.dumps(truth,ensure_ascii=False).encode())
                    receipt=submit(item,raw);item['id']=receipt['document_id'];item['initial_receipt']=receipt;items.append(item)
        current=wait_ready();assert len(current)==12
        for item in items:
            item['initial_attempt']=current[item['id']]['latest_attempt']
            assert item['initial_attempt']['attempt_id']==item['initial_receipt']['attempt_id']
            assert item['initial_attempt']['capture_id']==item['initial_receipt']['capture_id']
            assert item['initial_attempt']['config_revision']==1
            item['old']=snapshot(item)
        check_lists();stopped=server.stop();assert not stopped['forced']
        server.start(pause=True)
        check_attempts('initial')
        for item in items:
            if item['status']=='replacement':item['pending']=submit(item,item['new_raw'],replacement=True)
        before=check_lists()
        for item in items:
            row=before[item['id']]
            if item['status']=='replacement':
                assert row['latest_attempt']['status']=='pending' and row['latest_attempt']['capture_id']==item['pending']['capture_id']
                assert row['latest_attempt']['attempt_id']==item['pending']['attempt_id'] and row['latest_attempt']['config_revision']==1
                assert row['published_snapshot']['capture_id']!=item['pending']['capture_id']
                item['pending_attempt']=row['latest_attempt']
            assert snapshot(item,item['old']['reference'])==item['old']
        check_attempts('pending')
        stopped=server.stop();assert stopped['pause_events'] and stopped['audit']==[]
        paths=[Path(row['path']) for row in before.values()]
        for path in paths:
            assert path.is_relative_to(server.root) and '.document-snapshots' not in path.parts
            path.unlink(missing_ok=True)
        server.start(pause=True,deny=paths)
        check_attempts('pending')
        for item in items:
            row=listed()[item['id']]
            if item['status']=='replacement':assert row['latest_attempt']['status']=='pending'
            assert snapshot(item,item['old']['reference'])==item['old']
        check_lists();stopped=server.stop();assert stopped['pause_events'] and stopped['audit']==[]
        server.start(deny=paths);wait_ready();check_attempts('published')
        for item in items:
            replacement=item['status']=='replacement';item['final']=snapshot(item,new=replacement)
            if replacement:
                reference=item['old']['reference']
                rejected=[('/documents/read',{'reference':reference}),('/documents/read',{'reference':reference,'view':'original-info'}),
                    ('/documents/original',{'reference':reference})]+[('/documents/read',{'reference':reference,'view':'table','table_id':t['table_id']}) for t in item['old']['tables']]
                for route,body in rejected:
                    before_request=business_state()
                    response=server.client.post(server.prefix+route,json={**server.context,**body})
                    assert response.status_code==400 and business_state()==before_request
            else:assert item['final']==item['old']
        check_lists();stopped=server.stop();assert not stopped['forced'] and len([e for e in stopped['audit'] if e['event']=='subprocess.Popen'])==4
        readonly=server.root/'stable-read-only.jsonl'
        with monkeypatch.context() as scoped:
            scoped.setenv('SMM_008_WEB_READ_ONLY',str(readonly))
            server.start(deny=paths)
            check_attempts('published')
            for item in items:assert snapshot(item,item['final']['reference'],new=item['status']=='replacement')==item['final']
            check_lists();assert not readonly.exists()
            control=server.client.post('/__test_processing_probe');assert control.status_code==200
            assert control.json()['blocked']==['processing','subprocess']
            stopped=server.stop();assert not stopped['forced'] and stopped['audit']==[]
        controls=[json.loads(line) for line in readonly.read_text(encoding='utf-8').splitlines()]
        assert len(controls)==2 and {r['event'] for r in controls}=={'processing','subprocess'}
        keep('restart-states/'+owner+'-readonly-controls.jsonl',readonly.read_bytes())
        observe('restart-all-publication-states',{'owner':owner,'targets':[{k:v for k,v in item.items() if k in {'id','key','status','pending','old','final'}} for item in items],'source_paths_deleted':list(map(str,paths))})
    finally:server.stop()

"""Native management cannot bypass bundles or stale-candidate comparisons."""
import base64,hashlib,json,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
import pytest
from document_helpers import observe
from document_formats_fixtures import docx_fixture
from document_formats_upload_fixture import upload_input
from document_formats_managed_empty_fixture import blank_original
from document_formats_partial_fixture import partial_pdf
from test_document_formats_retry import FONT,scan_pdf,keep
from test_document_formats_replace import business_state,transfer_state
from test_hub_documents_contracts import w


def native_input(format,key):
    if format!='docx':return upload_input(format,key)
    raw,truth=docx_fixture(key)
    tables=[{'rows':max(c[0]+c[3]-1 for c in cells),'columns':max(c[1]+c[4]-1 for c in cells),'cells':cells,'location':{'part':'word/document.xml','path':path}} for cells,path in zip(truth['tables'],truth['table_paths'])]
    return raw,{'words':truth['words'],'excluded':truth['excluded'],'tables':tables}


class Creator:
    def __init__(self,w,owner):
        self.w=w;self.owner=owner;self.db=w.pair.local if owner=='local' else w.pair.remote
        self.client=w.local.client if owner=='local' else w.hub;self.prefix='/api' if owner=='local' else '/v1';self.context={} if owner=='local' else w.context()
        self.projects=([w.local.request('POST','/api/projects',{'name':'008 fences'}),w.local.request('POST','/api/projects/global')] if owner=='local' else [w.hub_project('008 fences'),w.hub_project('008 global',kind='global')])
        self.items=[]
    def request(self,method,path,body=None,raw=None,headers=None,reject=False,stale_part=False):
        kwargs={'headers':headers or {}}
        if raw is not None:kwargs['content']=raw
        elif body is not None:kwargs['json']=body
        r=self.client.request(method,self.prefix+path,**kwargs)
        result=r.json() if 'json' in r.headers.get('content-type','') else {'sha256':hashlib.sha256(r.content).hexdigest(),'bytes':len(r.content)}
        recorded=result
        if method=='GET' and path in {'/documents/files','/documents/library'}:
            digest=hashlib.sha256(r.content).hexdigest();evidence='responses/'+digest+'.json'
            keep(evidence,r.content)
            recorded={'evidence_file':evidence,'sha256':digest,'bytes':len(r.content),'encoding':'utf-8 JSON; native lossless gzip may append .gz'}
        observe('native-management-'+self.owner,{'method':method,'path':path,'request':body,'status':r.status_code,'response':recorded,'raw_bytes':len(raw) if raw is not None else None,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None})
        if stale_part:assert r.status_code==200 or 400<=r.status_code<500,r.text
        else:assert (400<=r.status_code<500) if reject else r.status_code==200,r.text
        return r
    def project(self,p):return {**self.context,'project_id':p['id'],'project_key':p['stable_key'] if self.owner=='local' else p['source_key']}
    def entries(self):
        files=self.request('GET','/documents/files').json();library=self.request('GET','/documents/library').json()
        assert len(files)==len({e['id'] for e in files}) and len(library)==len({e['id'] for e in library})
        assert {e['id'] for e in files}=={e['id'] for e in library}
        library={e['id']:e for e in library}
        for e in files:
            for k in ('version','processing_version','published_snapshot','latest_attempt','retry_target'):
                # Legacy TXT predates captured-result metadata.
                if k in e or k in library[e['id']]:assert e.get(k)==library[e['id']].get(k)
        return library
    def comparison(self,e):
        result={'expected_version':e['version'],'expected_revision':e['source_revision'],'expected_processing_version':e['processing_version']}
        latest=e['latest_attempt'];return {**result,'capture_id':latest['capture_id'],'expected_attempt_id':latest['attempt_id']}
    def upload(self,item,raw,comparison=None):
        body={**self.project(item['project']),'name':item['name'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'submission_id':uuid4().hex}
        if comparison is not None:body.update(document_id=item['id'],**comparison)
        begin=self.request('POST','/documents/uploads',body).json();uid=begin['upload_id'];item['last_uploaded_raw']=raw;item['last_block_bytes']=begin['block_bytes']
        for index,offset in enumerate(range(0,len(raw),begin['block_bytes'])):
            part=raw[offset:offset+begin['block_bytes']]
            self.request('PUT','/documents/uploads/'+uid+'/parts/'+str(index),raw=part,headers={'X-Chunk-SHA256':hashlib.sha256(part).hexdigest()})
        receipt=self.request('POST','/documents/uploads/'+uid+'/commit',self.context).json()
        deadline=time.monotonic()+35
        while True:
            entry=self.entries()[receipt['document_id']]
            if entry['latest_attempt']['status'] in {'ready','partial','failed','empty-success'}:break
            assert time.monotonic()<deadline,entry
            time.sleep(.02)
        return uid,receipt,entry
    def add(self,format,key,project,kind='ready'):
        if kind=='blank':raw=blank_original(format,key);truth={'words':[],'excluded':[],'tables':[]};status='empty-success'
        elif kind=='partial':raw,t=partial_pdf(key,FONT);truth={'words':[t['anchor']],'excluded':[],'tables':[]};status='partial'
        elif kind=='failed':raw=scan_pdf(key);truth={'words':[],'excluded':[],'tables':[]};status='failed'
        else:raw,truth=native_input(format,key);status='ready'
        item={'name':key+'.'+format,'format':format,'project':project,'raw':raw,'truth':truth,'status':status}
        keep('inputs/'+item['name'],raw);keep('truth/'+item['name']+'.json',json.dumps(truth,ensure_ascii=False).encode())
        uid,receipt,e=self.upload(item,raw);assert e['latest_attempt']['status']==status
        item.update(id=e['id'],uid=uid,receipt=receipt);self.items.append(item)
        if kind=='failed':assert e['version']==e['processing_version']==0 and e['published_snapshot'] is None and e['retry_target'] is not None
        else:assert e['version']==e['processing_version']==1 and e['published_snapshot']['status']==status
        return item
    def read(self,item):
        e=self.entries()[item['id']];ref=e.get('original_reference')
        if item['status']=='failed':
            assert e['published_snapshot'] is None and ref is None and e['version']==e['processing_version']==0
            return {'entry':e}
        assert isinstance(ref,str) and ref
        if item['truth']['words']:
            hits=self.request('POST','/documents/search',{**self.context,'query':item['truth']['words'][0],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if self.owner=='local' else {})}).json()['results']
            own=[h for h in hits if h['id']==item['id']];assert len(own)==1
            assert own[0]['sha256']==hashlib.sha256(item['raw']).hexdigest() and own[0]['version']==own[0]['processing_version']==1
        if item['status']=='empty-success':
            assert e['text_length']==0 and e['published_snapshot']['status']=='empty-success' and e['latest_attempt']['status']=='empty-success'
            value=None;tables=[]
        else:
            value=self.request('POST','/documents/read',{**self.context,'reference':ref,'start':0,'end':e['text_length']}).json()
            assert value['id']==item['id'] and value['format']==item['format'] and value['version']==value['processing_version']==1
            assert value['sha256']==hashlib.sha256(item['raw']).hexdigest() and value['processing_status']==item['status']
            assert all(word in value['text'] for word in item['truth']['words']) and all(word not in value['text'] for word in item['truth']['excluded'])
            if item['status']=='empty-success':assert value['text']=='' and value['text_length']==0
            if item['status']=='partial':assert value['text']==item['truth']['words'][0] and any(e['page']==2 for e in value['coverage']['errors'])
            tables=[self.request('POST','/documents/read',{**self.context,'reference':ref,'view':'table','table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,'column_start':1,'column_end':t['columns']+1}).json() for t in value['tables']]
            assert len(tables)==len(item['truth']['tables'])
            for expected in item['truth']['tables']:
                own=[t for t in tables if all(t['location'].get(k)==v for k,v in expected['location'].items()) and any(c['text']==expected['cells'][0][2] for c in t['cells'])];assert len(own)==1
                t=own[0];cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in t['cells']]
                assert (t['rows'],t['columns'])==(expected['rows'],expected['columns']) and len(cells)==len(expected['cells']) and set(cells)==set(expected['cells'])
        info=self.request('POST','/documents/read',{**self.context,'reference':ref,'view':'original-info'}).json()
        with self.db.connect() as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        origin={'device_id':self.w.device if self.owner=='local' else self.context['hub_id'],'archive_id':archive,'document_id':item['id']}
        assert info['origin']==origin and info['id']==item['id'] and info['version']==info['processing_version']==1 and info['format']==item['format']
        assert info['sha256']==hashlib.sha256(item['raw']).hexdigest() and info['bytes']==len(item['raw']) and info['available'] is True
        if value is not None:assert value['origin']==origin and value['sha256']==info['sha256']
        raw=self.request('POST','/documents/original',{**self.context,'reference':ref}).content
        keep('downloads/'+hashlib.sha256(raw).hexdigest()+'-'+item['name'],raw);assert raw==item['raw']
        return {'entry':e,'read':value,'tables':tables,'info':info,'raw_sha256':hashlib.sha256(raw).hexdigest()}
    def text_controls(self):
        result=[]
        for number,p in enumerate(self.projects):
            text=self.owner+' legacy control '+str(number)
            e=self.request('POST','/documents/library',{**self.project(p),'name':'control'+str(number)+'.txt','submission_id':uuid4().hex,'content_base64':base64.b64encode(text.encode()).decode()}).json()
            result.append({'id':e['id'],'project':p,'text':text,'entry':e})
        return result
    def assert_text(self,item):
        hits=self.request('POST','/documents/search',{**self.context,'query':item['text'],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if self.owner=='local' else {})}).json()['results']
        own=[h for h in hits if h['id']==item['id']];assert len(own)==1
        value=self.request('POST','/documents/read',{**self.context,'reference':own[0]['reference'],'start':0,'end':own[0]['text_length']}).json();assert value['text']==item['text']
    def frozen(self):
        with self.db.connect() as con:index=[tuple(r) for r in con.execute('SELECT rowid,text FROM document_fts ORDER BY rowid')]
        return business_state(self.db),transfer_state(self.db),index
    def retry_removed(self,item,target):
        argv=([sys.executable,'-B','-m','smm_local.cli','--db',str(self.db.db_path),'documents'] if self.owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(self.db.db_path.parent),'documents'])+['reprocess','--document-id',item['id']]
        for k in ('capture_id','expected_attempt_id','expected_version','expected_processing_version'):argv+=['--'+k.replace('_','-'),str(target[k])]
        r=subprocess.run(argv,cwd=self.w.root,capture_output=True,text=True,encoding='utf-8',timeout=30)
        observe('removed-candidate-cli',{'argv':argv,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode!=0,r.stdout



def test_management_frozen_oracle_detects_fts_only_change(w):
    c=Creator(w,'local');item=c.add('docx','FTSORACLE',c.projects[0]);before=c.frozen()
    assert before[2] and len(before[2])==1
    with c.db.connect() as con:
        changed=con.execute("UPDATE document_fts SET text='index only corruption' WHERE rowid=(SELECT pk FROM documents WHERE id=?)",(item['id'],)).rowcount
    after=c.frozen()
    assert changed==1 and before[0]==after[0] and before[1]==after[1] and before[2]!=after[2] and before!=after
    assert after[2][0][1]=='index only corruption'
    observe('fts-only-state-oracle',{'document_id':item['id'],'business_tables_unchanged':before[0]==after[0],'saved_bytes_unchanged':before[1]==after[1],'fts_only_change_detected':before!=after})

@pytest.mark.parametrize('owner',['local','hub'])
def test_native_documents_reject_small_text_update_bypass(w,owner):
    # TC-008-native-management-fence / native-text-update-fence
    c=Creator(w,owner);items=[c.add(format,'F'+owner[0]+format+str(i),p) for format in ('docx','xlsx','pdf') for i,p in enumerate(c.projects)]
    controls=c.text_controls();baseline={item['id']:c.read(item) for item in items};ids={i['id'] for i in items+controls};assert set(c.entries())==ids
    for item in items:
        e=c.entries()[item['id']];old={**c.project(item['project']),'expected_version':e['version'],'expected_revision':e['source_revision'],'submission_id':uuid4().hex,'content_base64':base64.b64encode(('plain text bypass '+item['name']).encode()).decode()}
        for body in (old,{**old,**c.comparison(e),'submission_id':uuid4().hex}):
            before=c.frozen();c.request('PUT','/documents/library/'+item['id'],body,reject=True);assert c.frozen()==before
        for other in items:assert c.read(other)==baseline[other['id']]
    for item in controls:
        e=c.entries()[item['id']];item['text']+=' updated'
        c.request('PUT','/documents/library/'+item['id'],{**c.project(item['project']),'expected_version':e['version'],'expected_revision':e['source_revision'],'submission_id':uuid4().hex,'content_base64':base64.b64encode(item['text'].encode()).decode()})
        c.assert_text(item)
    assert set(c.entries())==ids
    observe('native-text-fence-complete-'+owner,{'native_ids':[i['id'] for i in items],'legacy_controls':[i['id'] for i in controls]})


@pytest.mark.skipif(not FONT,reason='terminal candidate matrix requires prepared independent scan/partial materials; skipped is not acceptance')
@pytest.mark.parametrize('owner',['local','hub'])
def test_native_terminal_removal_compares_current_publication_and_candidate(w,owner):
    # TC-008-native-management-fence / native-removal-compare
    c=Creator(w,owner);targets=[c.add(f,'D'+owner[0]+f+str(i),p) for f in ('docx','xlsx','pdf') for i,p in enumerate(c.projects)]
    for kind in ('blank','partial'):
        targets += [c.add('docx' if kind=='blank' else 'pdf',kind+owner[0]+str(i),p,kind) for i,p in enumerate(c.projects)]
    targets += [c.add('pdf','FAIL'+owner[0]+str(i),c.projects[0],'failed') for i in range(2)]
    for i,p in enumerate(c.projects):
        item=c.add('pdf','REPL'+owner[0]+str(i),p);old=c.entries()[item['id']]
        raw=scan_pdf('NEW'+owner[0]+str(i));keep('inputs/new-'+item['name'],raw)
        uid,receipt,e=c.upload(item,raw,c.comparison(old));assert e['latest_attempt']['status']=='failed' and e['published_snapshot']==old['published_snapshot']
        assert e['retry_target']['sha256']==hashlib.sha256(raw).hexdigest() and e['retry_target']['capture_id']!=old['latest_attempt']['capture_id']
        item.update(uid=uid,receipt=receipt,prior=old);targets.append(item)
    native_controls=[c.add('docx','STABLE'+owner[0]+str(i),p) for i,p in enumerate(c.projects)];legacy_controls=c.text_controls()
    all_items=targets+native_controls;all_ids={i['id'] for i in all_items+legacy_controls};assert len(targets)==14 and set(c.entries())==all_ids
    baseline={i['id']:c.read(i) for i in all_items}
    for item in targets:
        e=c.entries()[item['id']];cmp=c.comparison(e);current={**c.project(item['project']),**cmp}
        entries=c.entries()
        peers=[p for p in targets+native_controls if p['id']!=item['id'] and p['project']==item['project'] and entries[p['id']]['version']==e['version']]
        assert peers,'must use another still-authorized target in same project and content version'
        peer=c.entries()[peers[0]['id']];other=c.projects[1 if item['project']==c.projects[0] else 0]
        changes=[('expected_version',e['version']+1),('expected_processing_version',e['processing_version']+1),('expected_processing_version',True),('expected_revision',e['source_revision']+1),('project_key',other['stable_key'] if owner=='local' else other['source_key']),('capture_id',peer['latest_attempt']['capture_id']),('expected_attempt_id',peer['latest_attempt']['attempt_id'])]
        if item['status']!='ready' or 'prior' in item:
            old_update={**c.project(item['project']),'expected_version':e['version'],'expected_revision':e['source_revision'],'submission_id':uuid4().hex,'content_base64':base64.b64encode(('blocked terminal text '+item['name']).encode()).decode()}
            for body in (old_update,{**old_update,**cmp,'submission_id':uuid4().hex}):
                before=c.frozen();c.request('PUT','/documents/library/'+item['id'],body,reject=True);assert c.frozen()==before
            for other in all_items:assert c.read(other)==baseline[other['id']]
        bodies=[{**current,k:v} for k,v in changes]
        bodies += [{k:v for k,v in current.items() if k!='expected_processing_version'},{**current,'capture_id':peer['latest_attempt']['capture_id'],'expected_attempt_id':peer['latest_attempt']['attempt_id']}]
        pub=e['published_snapshot'];unpublished=pub is None or pub['capture_id']!=e['latest_attempt']['capture_id']
        if unpublished:
            bodies += [{k:v for k,v in current.items() if k!=field} for field in ('capture_id','expected_attempt_id')]
            bodies += [{k:v for k,v in current.items() if k not in {'capture_id','expected_attempt_id'}}]
        if 'prior' in item:bodies += [{**c.project(item['project']),**c.comparison(item['prior'])}]
        if owner=='hub':bodies += [{**current,'hub_id':'f'*32},{**current,'document_epoch':'f'*32}]
        for bad in bodies:
            before=c.frozen();c.request('DELETE','/documents/library/'+item['id'],bad,reject=True);assert c.frozen()==before
    live={i['id']:i for i in all_items}
    for item in targets:
        e=c.entries()[item['id']];old=baseline[item['id']];target=e['retry_target'];assert target
        answer=c.request('DELETE','/documents/library/'+item['id'],{**c.project(item['project']),**c.comparison(e)}).json();assert answer['removed']==item['id']
        del live[item['id']];all_ids.remove(item['id']);assert set(c.entries())==all_ids
        before=c.frozen();c.retry_removed(item,target);assert c.frozen()==before
        c.request('POST','/documents/uploads/'+item['uid']+'/commit',c.context,reject=True);assert c.frozen()==before
        chunk=item['last_uploaded_raw'][:item['last_block_bytes']]
        c.request('PUT','/documents/uploads/'+item['uid']+'/parts/0',raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()},stale_part=True);assert c.frozen()==before
        c.request('POST','/documents/uploads/'+item['uid']+'/commit',c.context,reject=True);assert c.frozen()==before
        c.request('DELETE','/documents/library/'+item['id'],{**c.project(item['project']),**c.comparison(e)},reject=True);assert c.frozen()==before
        if item['truth']['words']:
            hits=c.request('POST','/documents/search',{**c.context,'query':item['truth']['words'][0],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
            assert all(h['id']!=item['id'] for h in hits)
        if 'read' in old:
            ref=old['entry']['original_reference']
            for view in ('text','original-info'):c.request('POST','/documents/read',{**c.context,'reference':ref,'view':view},reject=True)
            for t in old['tables']:c.request('POST','/documents/read',{**c.context,'reference':ref,'view':'table','table_id':t['table_id']},reject=True)
            c.request('POST','/documents/original',{**c.context,'reference':ref},reject=True)
        assert c.frozen()==before
        for other in live.values():assert c.read(other)==baseline[other['id']]
        for control in legacy_controls:c.assert_text(control)
    assert set(live)=={i['id'] for i in native_controls} and len(all_ids)==4
    observe('native-removal-fence-complete-'+owner,{'removed_ids':[i['id'] for i in targets],'native_controls':[i['id'] for i in native_controls],'text_controls':[i['id'] for i in legacy_controls]})

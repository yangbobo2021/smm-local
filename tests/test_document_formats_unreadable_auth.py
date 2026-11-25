"""Refresh-confirmed unreadable members lose capture authorization; overlapping sources stay valid."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import pytest
from document_helpers import observe,deny_source_reads
from document_formats_fixtures import docx_fixture
from document_formats_partial_fixture import partial_pdf
from test_document_formats_retry import ENGINE,DATA,FONT,keep,child_source_guard
from test_document_formats_replace import business_state
from test_hub_documents_contracts import w

pytestmark=pytest.mark.skipif(os.name=='nt' or not hasattr(os,'getuid') or os.getuid()==0 or not all((ENGINE,DATA,FONT)),reason='requires real nonroot POSIX permission denial and creator assets; skipped is not Windows/service acceptance')


def source_truth(text,tables,item):
    if item['status']=='partial':
        assert text==item['truth']['anchor'] and tables==[]
    else:
        assert all(text.count(word)==1 for word in item['truth']['words'])
        assert all(word not in text for word in item['truth']['excluded'])
        assert len(tables)==len(item['truth']['tables'])==3
        wanted=dict(zip(item['truth']['table_paths'],item['truth']['tables']))
        assert {t['location']['path'] for t in tables}==set(wanted)
        for table in tables:
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in table['cells']]
            expected=wanted[table['location']['path']]
            assert len(cells)==len(expected) and set(cells)==set(expected)
            assert (table['rows'],table['columns'])==((1,2) if '/table[1]' in table['location']['path'] and '/cell[' in table['location']['path'] else (2,2))


def test_unreadable_auth_source_oracle_rejects_wrong_or_missing_target():
    raw,truth=docx_fixture('authcontrol');item={'status':'ready','truth':truth}
    tables=[{'location':{'path':p},'rows':1 if '/cell[' in p else 2,'columns':2,'cells':[dict(zip(('row','column','text','row_span','column_span'),c)) for c in cells]} for p,cells in zip(truth['table_paths'],truth['tables'])]
    text='\n'.join(truth['words']);source_truth(text,tables,item)
    from copy import deepcopy
    for mutate in ('missing-word','missing-table','wrong-cell','wrong-dimension'):
        bad=deepcopy(tables);badtext=text
        if mutate=='missing-word':badtext=badtext.replace(truth['words'][0],'')
        if mutate=='missing-table':bad=bad[:-1]
        if mutate=='wrong-cell':bad[-1]['cells'][0]['text']='OTHER'
        if mutate=='wrong-dimension':bad[-1]['rows']+=1
        with pytest.raises(AssertionError):source_truth(badtext,bad,item)
    observe('unreadable-auth-truth-controls',{'valid_source':True,'wrong_variants_rejected':4,'sha256':hashlib.sha256(raw).hexdigest()})


@pytest.mark.parametrize('owner',['local','hub'])
def test_refresh_unreadable_revokes_only_failed_sources_then_last_capture(w,tmp_path,monkeypatch,owner):
    # TC-008-refresh-unreadable-auth
    db=w.pair.local if owner=='local' else w.pair.remote
    client=w.local.client if owner=='local' else w.hub;prefix='/api' if owner=='local' else '/v1'
    ctx={} if owner=='local' else w.context()
    projects=([w.local.request('POST','/api/projects',{'name':'Missing ordinary'}),w.local.request('POST','/api/projects/global')] if owner=='local' else [w.hub_project('Missing ordinary'),w.hub_project('Missing global',kind='global')])
    other=w.local.request('POST','/api/projects',{'name':'Unassociated control'}) if owner=='local' else w.hub_project('Unassociated control')
    root=tmp_path/('sources-'+owner);root.mkdir();items=[];sources=[]
    command_prefix=([sys.executable,'-B','-m','smm_local.cli','--db',str(db.db_path),'documents'] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(db.db_path.parent),'documents'])
    def cli(*args,reject=False):
        argv=command_prefix+list(map(str,args));result=subprocess.run(argv,cwd=w.root,capture_output=True,text=True,encoding='utf-8',timeout=90)
        observe('unreadable-auth-cli',{'owner':owner,'argv':argv,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'expected_reject':reject})
        assert result.returncode!=0 if reject else result.returncode==0,result.stderr
        return result if reject else json.loads(result.stdout)
    def request(method,path,body=None,reject=False):
        r=client.request(method,prefix+path,json=body) if body is not None else client.request(method,prefix+path)
        value=r.json() if 'json' in r.headers.get('content-type','') else {'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()}
        observe('unreadable-auth-http',{'owner':owner,'method':method,'path':path,'request':body,'status':r.status_code,'response':value,'expected_reject':reject})
        assert 400<=r.status_code<500 if reject else r.status_code==200,r.text
        return r
    def listed():return request('GET','/documents/files').json()
    def members(sid):return {row['id']:row for row in listed() if row['source_id']==sid}
    def search(item,project=None):
        body={**ctx,'query':item['anchor'],'scope':'project','project_id':(project or item['project'])['id'],'limit':50}
        if owner=='local':body['local']=True
        return request('POST','/documents/search',body).json()['results']
    def read_all(item,hit):
        assert hit['id']==item['id'] and hit['sha256']==hashlib.sha256(item['raw']).hexdigest()
        assert hit['origin']==item['origin'] and hit['format']==item['format'] and hit['processing_status']==item['status']
        body={**ctx,'reference':hit['reference']}
        value=request('POST','/documents/read',{**body,'start':0,'end':hit['text_length']}).json()
        tables=[request('POST','/documents/read',{**body,'view':'table','table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,'column_start':1,'column_end':t['columns']+1}).json() for t in value['tables']]
        source_truth(value['text'],tables,item)
        assert value['coverage']['status']==item['status'] if 'status' in value['coverage'] else True
        if item['status']=='partial':assert any(e['page']==2 and '1600万像素' in e['reason'] for e in value['coverage']['errors'])
        info=request('POST','/documents/read',{**body,'view':'original-info'}).json()
        for v in [value,info,*tables]:
            assert v['id']==item['id'] and v['origin']==item['origin'] and v['version']==hit['version'] and v['processing_version']==hit['processing_version'] and v['sha256']==hit['sha256']
        raw=request('POST','/documents/original',body).content
        assert raw==item['raw'] and info['bytes']==len(raw) and info['available'] is True
        keep('downloads/'+hashlib.sha256(raw).hexdigest(),raw)
        return {'text':value['text'],'tables':[{k:v for k,v in t.items() if k in ('table_id','rows','columns','location','cells')} for t in tables],'coverage':value['coverage']}
    def retry(item,target,reject=False):
        args=['reprocess','--document-id',item['id']]
        for key in ('capture_id','expected_attempt_id','expected_version','expected_processing_version'):args+=['--'+key.replace('_','-'),target[key]]
        return cli(*args,reject=reject)
    def reject_refs(item):
        for hit in item['old_hits']:
            body={**ctx,'reference':hit['reference']}
            for view in ('text','original-info'):request('POST','/documents/read',{**body,'view':view},reject=True)
            for t in hit['tables']:request('POST','/documents/read',{**body,'view':'table','table_id':t['table_id']},reject=True)
            request('POST','/documents/original',body,reject=True)
    def disk():
        roots=[db.db_path.parent/'.document-snapshots',db.db_path.parent/'.documents']
        return {str(p.relative_to(db.db_path.parent)):(p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()) for top in roots if top.exists() for p in top.rglob('*') if p.is_file() and not p.name.endswith('.lock')}
    cli('processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    controls=[];control_dir=root/'control';control_dir.mkdir()
    for number in (1,2):
        raw,truth=docx_fixture(owner+'control'+str(number));path=control_dir/('control'+str(number)+'.docx');path.write_bytes(raw)
        item={'path':path,'raw':raw,'truth':truth,'status':'ready','format':'docx','project':other,'anchor':truth['words'][0].split()[0],'old_hits':[]}
        keep('inputs/'+owner+'-'+path.name,raw);controls.append(item)
    control_source=cli('add',control_dir,'--project-id',other['id']);cli('refresh','--source-id',control_source['id'])
    for group,project in enumerate(projects):
        parent=root/('unreadable-'+str(group));nested=parent/'nested';nested.mkdir(parents=True)
        group_items=[]
        for status in ('ready','partial'):
            for number in (1,2):
                label=owner+'unreadable'+str(group)+status+str(number)
                raw,truth=docx_fixture(label) if status=='ready' else partial_pdf(label,FONT)
                fmt='docx' if status=='ready' else 'pdf';path=nested/(label+'.'+fmt);path.write_bytes(raw)
                item={'path':path,'raw':raw,'truth':truth,'status':status,'format':fmt,'project':project,'anchor':truth['words'][0].split()[0] if status=='ready' else truth['anchor'].split()[0],'old_hits':[]}
                keep('inputs/'+path.name,raw);keep('truth/'+path.name+'.json',json.dumps(truth,ensure_ascii=False,default=lambda v:sorted(v) if isinstance(v,set) else str(v)).encode());items.append(item);group_items.append(item)
        primary=cli('add',parent,'--project-id',project['id']);cli('refresh','--source-id',primary['id'])
        secondary=cli('add',nested,'--project-id',project['id']);cli('refresh','--source-id',secondary['id'])
        sources.append((primary,secondary,group_items))
    for item in [*items,*controls]:
        hits=search(item);assert len(hits)==1;hit=hits[0]
        with db.connect() as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        item['id']=hit['id'];item['origin']={'device_id':w.device if owner=='local' else ctx['hub_id'],'archive_id':archive,'document_id':hit['id']}
        assert Path(hit['path'])==item['path']
        item['snapshot']=read_all(item,hit);item['old_hits'].append(hit)
        if item not in controls:assert search(item,other)==[]
    assert len({i['id'] for i in [*items,*controls]})==len(items)+len(controls)
    for primary,secondary,group_items in sources:
        assert set(members(primary['id']))==set(members(secondary['id']))=={i['id'] for i in group_items}
        for item in group_items:
            item['mode']=item['path'].stat().st_mode & 0o777;item['mtime_ns']=item['path'].stat().st_mtime_ns;item['path'].chmod(0)
            with pytest.raises(PermissionError):item['path'].read_bytes()
        cli('refresh','--source-id',primary['id'])
        assert all(row['status']=='failed' for row in members(primary['id']).values())
    with monkeypatch.context() as guard:
        log=child_source_guard(root,[i['path'] for i in [*items,*controls]],guard)
        opened=deny_source_reads(guard,*[i['path'] for i in [*items,*controls]])
        for primary,secondary,group_items in sources:
            for item in group_items:
                row=members(secondary['id'])[item['id']];assert row['retry_target'] is not None
                retry(item,row['retry_target'])
                # A still-valid overlap can support processing; it must never
                # restore a source whose own refresh confirmed this file absent.
                assert members(primary['id'])[item['id']]['status']=='failed'
                assert members(secondary['id'])[item['id']]['status']=='ready'
                hits=search(item);assert len(hits)==1 and hits[0]['source_ids']==[secondary['id']]
                assert read_all(item,hits[0])==item['snapshot'];item['old_hits'].append(hits[0])
                item['last_target']=members(secondary['id'])[item['id']]['retry_target'];assert item['last_target'] is not None
        for primary,secondary,group_items in sources:
            # Explicit refresh may attempt the source; only retry/query are forbidden to reopen it.
            protected=os.environ['SMM_008_PROTECTED_SOURCES'];guard.setenv('SMM_008_PROTECTED_SOURCES','[]')
            try:cli('refresh','--source-id',secondary['id'])
            finally:guard.setenv('SMM_008_PROTECTED_SOURCES',protected)
            rows=members(secondary['id']);assert all(r['status']=='failed' for r in rows.values())
            for item in group_items:
                assert rows[item['id']]['retry_target'] is None
                assert search(item)==[];reject_refs(item)
                before=business_state(db);saved=disk();retry(item,item['last_target'],reject=True)
                assert business_state(db)==before and disk()==saved
        for item in controls:
            hits=search(item);assert len(hits)==1 and read_all(item,hits[0])==item['snapshot']
        assert opened==[] and (not log.exists() or log.read_text()=='')
    for item in items:
        item['path'].chmod(item['mode'])
        assert item['path'].stat().st_mtime_ns==item['mtime_ns'] and item['path'].read_bytes()==item['raw']
    for primary,secondary,group_items in sources:
        cli('refresh','--source-id',primary['id'])
        for item in group_items:
            hits=search(item);assert len(hits)==1 and hits[0]['source_ids']==[primary['id']]
            assert read_all(item,hits[0])==item['snapshot'];reject_refs(item)
    observe('unreadable-auth-all-targets',{'owner':owner,'targets':len(items),'project_target_ids':{str(p['id']):sorted(i['id'] for i in items if i['project']['id']==p['id']) for p in projects},'states':['ready','partial'],'first_source_missing_remains_missing':True,'last_authority_rejects_retry':True,'restored_same_bytes_old_refs_rejected':True})

"""Real Hub CLI text/table/original views over offline captured Word sources."""
import hashlib,json,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from document_helpers import observe,fingerprint
from document_formats_fixtures import docx_fixture
from document_formats_cli_observer import install
from test_document_formats_cli import assert_source_headers,nonzero_reference_source,keep
from test_hub_documents_contracts import w


IDENTITY_FIELDS=('id','path','version','sha256','text_sha256','text_length','captured_at','captured_by_source_id','display_name','format','processing_version','result_sha256','profile','original_available','processing_status','source_ids','archive_scope','origin','origin_kind','device_name')


def assert_read_identity(value,saved,origin,source_id):
    for key in IDENTITY_FIELDS:assert value[key]==saved[key],key
    assert value['origin']==origin and value['archive_scope']==value['origin_kind']=='hub'
    assert value['source_ids']==[source_id] and value['captured_by_source_id']==source_id


def assert_original_info(value,hit,origin,source_id,raw):
    assert value['id']==hit['id'] and value['version']==hit['version'] and value['processing_version']==hit['processing_version']
    assert value['origin']==origin and value['source_ids']==[source_id] and value['archive_scope']=='hub'
    assert value['format']=='docx' and value['available'] is True and value.get('reason') is None
    assert value['sha256']==hashlib.sha256(raw).hexdigest() and value['bytes']==len(raw)


def assert_original_output(value,info,raw):
    assert value['sha256']==hashlib.sha256(raw).hexdigest()==info['sha256'] and value['bytes']==len(raw)==info['bytes']
    assert value['archive_scope']=='hub'
    # Extra identity fields may be omitted by this newly specified response;
    # when present they must still describe the same validated snapshot.
    for key in ('id','version','processing_version','format','origin','source_ids'):
        if key in value:assert value[key]==info[key],key


def saved_state(f):
    with f.db.connect() as con:
        names=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0]=='documents' or r[0].startswith(('document_','hub_document_'))]
        return {name:sorted([dict(row) for row in con.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,sort_keys=True,default=str)) for name in names}


def actual_cli(state,env,*args,rejected=False):
    command=[sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(state),'documents',*map(str,args)]
    result=subprocess.run(command,cwd=state,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
    observe('actual-hub-cli',{'argv':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    if rejected:
        assert result.returncode!=0,result.stdout
        return result
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)


def test_hub_cli_views_and_exact_originals_for_each_document(w,tmp_path):
    # TC-008-reference-hub-cli: format extraction semantics have independent
    # DOCX TDD; this slice tests the CLI's complete forwarding and output path.
    state=w.pair.remote.db_path.parent;f=SimpleNamespace(db=w.pair.remote);project=w.hub_project('Hub CLI saved original views');project_id=project['id'];expected={}
    for key in ('clialpha','clibeta'):
        raw,truth=docx_fixture(key)
        if key=='clialpha':raw=nonzero_reference_source(raw)
        path=tmp_path/'inputs'/(key+'.docx');path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
        expected[path.name]={'raw':raw,'truth':truth,'path':path,'before':fingerprint(path)};keep('inputs/'+path.name,raw)
        keep('truth/'+key+'.json',json.dumps(truth,ensure_ascii=False,default=lambda value:sorted(value) if isinstance(value,set) else str(value)).encode('utf-8'))
    source=actual_cli(state,None,'add',tmp_path/'inputs','--project-id',project_id)
    actual_cli(state,None,'refresh','--source-id',source['id'])
    canonical={}
    for name,item in expected.items():
        own=[h for h in w.search_hub(item['truth']['key'],scope='project',project_id=project_id,limit=50)['results'] if Path(h['path']).name==name];assert len(own)==1
        hit=own[0];read=w.read_hub(hit,start=0,end=hit['text_length'])
        for word in item['truth']['words']:assert read['text'].count(word)==1
        assert len(read['tables'])==len({t['table_id'] for t in read['tables']})==3
        assert {table['location']['path'] for table in read['tables']}==set(item['truth']['table_paths'])
        canonical[name]={'hit':hit,'read':read,'views':{table['table_id']:w.read_hub(hit,view='table',table_id=table['table_id']) for table in read['tables']}}
        assert fingerprint(item['path'])==item['before']
    for item in expected.values():item['path'].unlink()
    with f.db.connect() as con:archive_id=json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    env,log=install(tmp_path,[item['path'] for item in expected.values()]);before=saved_state(f);seen=set()
    for name,item in expected.items():
        hits=actual_cli(state,env,'search',item['truth']['key'],'--scope','project','--project-id',project_id,'--limit',50)['results']
        own=[h for h in hits if Path(h['path']).name==name];assert len(own)==1;hit=own[0];seen.add(hit['id']);reference=hit['reference'];saved=canonical[name]
        assert hit['id']==saved['hit']['id'] and hit['version']==hit['processing_version']==1
        origin={'device_id':w.context()['hub_id'],'archive_id':archive_id,'document_id':hit['id']}
        assert hit['origin']==origin
        if item['truth']['key']=='clialpha':
            assert 0<hit['start']<hit['end']<hit['text_length'] and hit['end']-hit['start']<=2000
        default=actual_cli(state,env,'read','--reference',reference)
        assert_read_identity(default,saved['read'],origin,source['id'])
        assert default['start']==hit['start'] and default['end']==hit['end']
        assert default['text']==saved['read']['text'][hit['start']:hit['end']]
        assert default['start_line']==1+saved['read']['text'].count('\n',0,hit['start']) and default['end_line']==1+saved['read']['text'].count('\n',0,hit['end']-1)
        full=actual_cli(state,env,'read','--reference',reference,'--view','text','--start',0,'--end',hit['text_length'])
        assert full==saved['read'];assert_read_identity(full,saved['read'],origin,source['id'])
        start=full['text'].index('😀')-2;end=start+10
        sliced=actual_cli(state,env,'read','--reference',reference,'--view','text','--start',start,'--end',end)
        assert_read_identity(sliced,saved['read'],origin,source['id'])
        assert sliced['text']==full['text'][start:end] and sliced['start']==start and sliced['end']==end
        assert sliced['start_line']==1+full['text'].count('\n',0,start) and sliced['end_line']==1+full['text'].count('\n',0,end-1)
        for table in saved['read']['tables']:
            number=item['truth']['table_paths'].index(table['location']['path'])
            view=actual_cli(state,env,'read','--reference',reference,'--view','table','--table-id',table['table_id'])
            assert view==saved['views'][table['table_id']];assert_read_identity(view,saved['read'],origin,source['id'])
            assert_source_headers(view,item['truth'],number)
            wanted=item['truth']['tables'][number]
            assert view['rows']==max(r+rs-1 for r,c,t,rs,cs in wanted) and view['columns']==max(c+cs-1 for r,c,t,rs,cs in wanted)
            cells={(c['row'],c['column']):c for c in view['cells']}
            assert len(cells)==len(view['cells'])==len(wanted)
            for row,column,text,row_span,column_span in wanted:
                cell=cells[(row,column)]
                assert (cell['text'],cell['row_span'],cell['column_span'])==(text,row_span,column_span)
            assert view['location']['path']==item['truth']['table_paths'][number]
            narrow=actual_cli(state,env,'read','--reference',reference,'--view','table','--table-id',table['table_id'],'--row-start',1,'--row-end',2,'--column-start',2,'--column-end',3)
            assert_read_identity(narrow,saved['read'],origin,source['id']);assert_source_headers(narrow,item['truth'],number,2,3)
            assert narrow['rows']==view['rows'] and narrow['columns']==view['columns']
            selected=[c for c in view['cells'] if c['row']==1 and c['column']==2]
            assert narrow['cells']==selected and narrow['window']=={'row_start':1,'row_end':2,'column_start':2,'column_end':3}
            assert narrow['header_context']['cells']==[c for c in view['header_context']['cells'] if c['column']==2]
            assert narrow['table_id']==view['table_id'] and narrow['location']==view['location']
            windows=[{'row_start':1,'row_end':view['rows']+1,'column_start':1,'column_end':2}]
            if view['rows']>1:windows.append({'row_start':2,'row_end':3,'column_start':1,'column_end':view['columns']+1})
            for window in windows:
                flags=[arg for key,value in window.items() for arg in ('--'+key.replace('_','-'),value)]
                moved=actual_cli(state,env,'read','--reference',reference,'--view','table','--table-id',table['table_id'],*flags)
                assert_read_identity(moved,saved['read'],origin,source['id'])
                assert_source_headers(moved,item['truth'],number,window['column_start'],window['column_end'])
                assert moved['window']==window and (moved['rows'],moved['columns'])==(view['rows'],view['columns'])
                wanted=[cell for cell in view['cells'] if window['row_start']<=cell['row']<window['row_end'] and window['column_start']<=cell['column']<window['column_end']]
                assert moved['cells']==wanted
                assert moved['header_context']['cells']==[cell for cell in view['header_context']['cells'] if window['column_start']<=cell['column']<window['column_end']]
                assert moved['table_id']==view['table_id'] and moved['location']==view['location']

        info=actual_cli(state,env,'read','--reference',reference,'--view','original-info')
        assert_original_info(info,hit,origin,source['id'],item['raw'])
        assert info['id']==hit['id'] and info['version']==info['processing_version']==1 and info['format']=='docx'
        assert info['available'] is True and info['bytes']==len(item['raw']) and info['sha256']==item['before']['sha256']
        output=tmp_path/('download-'+name)
        metadata=actual_cli(state,env,'read','--reference',reference,'--original-output',output)
        assert output.read_bytes()==item['raw'] and hashlib.sha256(output.read_bytes()).hexdigest()==item['before']['sha256']
        assert_original_output(metadata,info,item['raw'])
        assert metadata['sha256']==info['sha256'] and metadata['bytes']==len(item['raw']) and metadata['archive_scope']=='hub'
        keep('downloads/'+name,output.read_bytes())
        actual_cli(state,env,'read','--reference',reference,'--original-output',output,rejected=True)
        assert output.read_bytes()==item['raw']
        for flags in (['--start',0],['--end',1],['--view','table','--table-id',saved['read']['tables'][0]['table_id']],['--table-id',saved['read']['tables'][0]['table_id']],['--row-start',1],['--row-end',2],['--column-start',1],['--column-end',2]):
            absent=tmp_path/('refused-'+name)
            actual_cli(state,env,'read','--reference',reference,'--original-output',absent,*flags,rejected=True)
            assert not absent.exists()
        assert saved_state(f)==before
    assert len(seen)==2 and saved_state(f)==before
    assert not log.exists() or log.read_text(encoding='utf-8')==''
    assert all(not item['path'].exists() for item in expected.values())
    observe('cli-snapshot-state-before-after',{'before':before,'after':saved_state(f),'source_paths_absent':True,'observer_events':[]})



def test_hub_cli_state_guard_rejects_body_sha_and_version_changes(tmp_path):
    from smm_local.core import Archive
    from smm_local.documents import Documents
    f=SimpleNamespace(db=Archive(tmp_path/'state-control.sqlite3'));Documents(f.db)
    with f.db.connect() as c:
        for number in (1,2):
            c.execute('INSERT INTO documents(id,path_key,path,text,version,sha256) VALUES(?,?,?,?,?,?)',('control'+str(number),'path'+str(number),'path'+str(number),'body'+str(number),number,str(number)*64))
    before=saved_state(f);assert 'documents' in before and len(before['documents'])==2
    for number in (1,2):
        for field,value in (('text','changed'),('sha256','f'*64),('version',10)):
            with f.db.connect() as c:c.execute('UPDATE documents SET '+field+'=? WHERE id=?',(value,'control'+str(number)))
            assert saved_state(f)!=before,(number,field)
            with f.db.connect() as c:c.execute('UPDATE documents SET text=?,version=?,sha256=? WHERE id=?',('body'+str(number),number,str(number)*64,'control'+str(number)))
            assert saved_state(f)==before
    observe('hub-cli-state-guard-controls',{'documents':2,'independent_corruption_checks':6,'restored':True})

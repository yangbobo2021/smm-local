"""Actual Local CLI forwards snapshot views and writes exact captured originals."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import pytest
from document_helpers import Fixture,observe,fingerprint
from document_formats_fixtures import docx_fixture
from document_formats_cli_observer import install


IDENTITY_FIELDS=('id','path','version','sha256','text_sha256','text_length','captured_at','captured_by_source_id','display_name','format','processing_version','result_sha256','profile','original_available','processing_status','source_ids','archive_scope','origin','origin_kind','device_name')


def assert_read_identity(value,saved,origin,source_id):
    for key in IDENTITY_FIELDS:assert value[key]==saved[key],key
    assert value['origin']==origin and value['archive_scope']==value['origin_kind']=='local'
    assert value['source_ids']==[source_id] and value['captured_by_source_id']==source_id


def assert_original_info(value,hit,origin,source_id,raw):
    assert value['id']==hit['id'] and value['version']==hit['version'] and value['processing_version']==hit['processing_version']
    assert value['origin']==origin and value['source_ids']==[source_id] and value['archive_scope']=='local'
    assert value['format']=='docx' and value['available'] is True and value.get('reason') is None
    assert value['sha256']==hashlib.sha256(raw).hexdigest() and value['bytes']==len(raw)


def assert_original_output(value,info,raw):
    assert value['sha256']==hashlib.sha256(raw).hexdigest()==info['sha256'] and value['bytes']==len(raw)==info['bytes']
    assert value['archive_scope']=='local'
    # Extra identity fields may be omitted by this newly specified response;
    # when present they must still describe the same validated snapshot.
    for key in ('id','version','processing_version','format','origin','source_ids'):
        if key in value:assert value[key]==info[key],key


def test_original_views_accept_contract_metadata_without_text_fields():
    raw=b'original bytes';origin={'device_id':'archive','archive_id':'archive','document_id':'document'}
    hit={'id':'document','version':1,'processing_version':2}
    info={**hit,'origin':origin,'source_ids':['source'],'archive_scope':'local','format':'docx','available':True,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    assert_original_info(info,hit,origin,'source',raw)
    output={key:info[key] for key in ('sha256','bytes','archive_scope')};assert_original_output(output,info,raw)
    for key,value in [('id','another'),('version',9),('processing_version',9),('origin',{}),('source_ids',[]),('format','pdf'),('available',False),('sha256','0'*64),('bytes',0)]:
        wrong={**info,key:value}
        with pytest.raises(AssertionError):assert_original_info(wrong,hit,origin,'source',raw)
    for key,value in [('sha256','0'*64),('bytes',0),('archive_scope','hub')]:
        with pytest.raises(AssertionError):assert_original_output({**output,key:value},info,raw)


def assert_source_headers(view,truth,index,column_start=1,column_end=3):
    assert view['header_context']['role']==('explicit_header' if index==0 else 'first_content_row')
    wanted=[cell for cell in truth['tables'][index] if cell[0]==1 and column_start<=cell[1]<column_end]
    cells=view['header_context']['cells'];assert len(cells)==len(wanted)
    actual={(cell['row'],cell['column']):cell for cell in cells};assert len(actual)==len(wanted)
    for row,column,text,row_span,column_span in wanted:
        cell=actual[(row,column)]
        assert (cell['text'],cell['row_span'],cell['column_span'],cell['type'])==(text,row_span,column_span,'string')
        assert cell['location']=={'part':'word/document.xml','path':truth['table_paths'][index]+'/row['+str(row)+']/cell['+str(column)+']'}


def test_cli_identity_and_header_oracles_reject_same_wrong_views():
    import copy
    origin={'device_id':'archive','archive_id':'archive','document_id':'document'}
    saved={name:name for name in IDENTITY_FIELDS};saved.update(origin=origin,source_ids=['source'],captured_by_source_id='source',archive_scope='local',origin_kind='local')
    assert_read_identity(saved,saved,origin,'source')
    for key in IDENTITY_FIELDS:
        wrong=copy.deepcopy(saved);wrong[key]=None
        with pytest.raises(AssertionError):assert_read_identity(wrong,saved,origin,'source')
    truth={'tables':[[(1,1,'A',1,1),(1,2,'B',1,1)]],'table_paths':['body/table[1]']}
    cells=[{'row':1,'column':c,'text':text,'row_span':1,'column_span':1,'type':'string','location':{'part':'word/document.xml','path':'body/table[1]/row[1]/cell['+str(c)+']'}} for c,text in ((1,'A'),(2,'B'))]
    good={'header_context':{'role':'explicit_header','cells':cells}};assert_source_headers(good,truth,0)
    for change in ({'role':'first_content_row'},{'cells':[]}):
        wrong=copy.deepcopy(good);wrong['header_context'].update(change)
        with pytest.raises(AssertionError):assert_source_headers(wrong,truth,0)


def saved_state(f):
    with f.db.connect() as con:
        names=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'document_%'")]
        return {name:sorted([dict(row) for row in con.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,sort_keys=True,default=str)) for name in names}


def actual_cli(f,env,*args,rejected=False):
    command=[sys.executable,'-B','-m','smm_local.cli','--db',str(f.db.db_path),'documents',*map(str,args)]
    result=subprocess.run(command,cwd=f.root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
    observe('actual-cli',{'argv':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
    if rejected:
        assert result.returncode!=0,result.stdout
        return result
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)


def keep(name,raw):
    if output:=os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        path=Path(output)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)



def nonzero_reference_source(raw):
    """Keep both existing documents; pad only alpha around its real query."""
    from io import BytesIO
    from zipfile import ZipFile
    from document_formats_fixtures import package
    with ZipFile(BytesIO(raw)) as archive:parts={name:archive.read(name) for name in archive.namelist()}
    def paragraph(text):return ('<w:p><w:r><w:t xml:space="preserve">'+text+'</w:t></w:r></w:p>').encode()
    prefix=b''.join(paragraph('paddingonly '*100) for _ in range(3))
    suffix=b''.join(paragraph('tailpaddingonly '*100) for _ in range(3))
    body=parts['word/document.xml'];assert body.count(b'<w:body>')==body.count(b'<w:sectPr>')==1
    parts['word/document.xml']=body.replace(b'<w:body>',b'<w:body>'+prefix,1).replace(b'<w:sectPr>',suffix+b'<w:sectPr>',1)
    return package(parts)

def test_local_cli_views_and_exact_originals_for_each_document(tmp_path):
    # TC-008-reference-local-cli: format extraction semantics have independent
    # DOCX TDD; this slice tests the CLI's complete forwarding and output path.
    f=Fixture(tmp_path);project=f.project('CLI saved original views');expected={}
    for key in ('clialpha','clibeta'):
        raw,truth=docx_fixture(key)
        if key=='clialpha':raw=nonzero_reference_source(raw)
        path=f.file(key+'.docx',raw=raw)
        expected[path.name]={'raw':raw,'truth':truth,'path':path,'before':fingerprint(path)};keep('inputs/'+path.name,raw)
        keep('truth/'+key+'.json',json.dumps(truth,ensure_ascii=False,default=lambda value:sorted(value) if isinstance(value,set) else str(value)).encode('utf-8'))
    source=f.add(f.root/'docs',[project]);f.refresh(source)
    canonical={}
    for name,item in expected.items():
        own=[h for h in f.search(item['truth']['key'],scope='project',project_id=project,local=True,limit=50)['results'] if Path(h['path']).name==name];assert len(own)==1
        hit=own[0];read=f.read(hit,start=0,end=hit['text_length'])
        for word in item['truth']['words']:assert read['text'].count(word)==1
        assert len(read['tables'])==len({t['table_id'] for t in read['tables']})==3
        assert {table['location']['path'] for table in read['tables']}==set(item['truth']['table_paths'])
        canonical[name]={'hit':hit,'read':read,'views':{table['table_id']:f.read(hit,view='table',table_id=table['table_id']) for table in read['tables']}}
        assert fingerprint(item['path'])==item['before']
    for item in expected.values():item['path'].unlink()
    with f.db.connect() as con:archive_id=json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    env,log=install(tmp_path,[item['path'] for item in expected.values()]);before=saved_state(f);seen=set()
    for name,item in expected.items():
        hits=actual_cli(f,env,'search',item['truth']['key'],'--scope','project','--project-id',project,'--local','--limit',50)['results']
        own=[h for h in hits if Path(h['path']).name==name];assert len(own)==1;hit=own[0];seen.add(hit['id']);reference=hit['reference'];saved=canonical[name]
        assert hit['id']==saved['hit']['id'] and hit['version']==hit['processing_version']==1
        origin={'device_id':archive_id,'archive_id':archive_id,'document_id':hit['id']}
        assert hit['origin']==origin
        if item['truth']['key']=='clialpha':
            assert 0<hit['start']<hit['end']<hit['text_length'] and hit['end']-hit['start']<=2000
        default=actual_cli(f,env,'read','--reference',reference)
        assert_read_identity(default,saved['read'],origin,source['id'])
        assert default['start']==hit['start'] and default['end']==hit['end']
        assert default['text']==saved['read']['text'][hit['start']:hit['end']]
        assert default['start_line']==1+saved['read']['text'].count('\n',0,hit['start']) and default['end_line']==1+saved['read']['text'].count('\n',0,hit['end']-1)
        full=actual_cli(f,env,'read','--reference',reference,'--view','text','--start',0,'--end',hit['text_length'])
        assert full==saved['read'];assert_read_identity(full,saved['read'],origin,source['id'])
        start=full['text'].index('😀')-2;end=start+10
        sliced=actual_cli(f,env,'read','--reference',reference,'--view','text','--start',start,'--end',end)
        assert_read_identity(sliced,saved['read'],origin,source['id'])
        assert sliced['text']==full['text'][start:end] and sliced['start']==start and sliced['end']==end
        assert sliced['start_line']==1+full['text'].count('\n',0,start) and sliced['end_line']==1+full['text'].count('\n',0,end-1)
        for table in saved['read']['tables']:
            number=item['truth']['table_paths'].index(table['location']['path'])
            view=actual_cli(f,env,'read','--reference',reference,'--view','table','--table-id',table['table_id'])
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
            narrow=actual_cli(f,env,'read','--reference',reference,'--view','table','--table-id',table['table_id'],'--row-start',1,'--row-end',2,'--column-start',2,'--column-end',3)
            assert_read_identity(narrow,saved['read'],origin,source['id']);assert_source_headers(narrow,item['truth'],number,2,3)
            assert narrow['rows']==view['rows'] and narrow['columns']==view['columns']
            selected=[c for c in view['cells'] if c['row']==1 and c['column']==2]
            assert narrow['cells']==selected and narrow['window']=={'row_start':1,'row_end':2,'column_start':2,'column_end':3}
            assert narrow['header_context']['cells']==[c for c in view['header_context']['cells'] if c['column']==2]
            assert narrow['table_id']==view['table_id'] and narrow['location']==view['location']
        info=actual_cli(f,env,'read','--reference',reference,'--view','original-info')
        assert_original_info(info,hit,origin,source['id'],item['raw'])
        assert info['id']==hit['id'] and info['version']==info['processing_version']==1 and info['format']=='docx'
        assert info['available'] is True and info['bytes']==len(item['raw']) and info['sha256']==item['before']['sha256']
        output=tmp_path/('download-'+name)
        metadata=actual_cli(f,env,'read','--reference',reference,'--original-output',output)
        assert output.read_bytes()==item['raw'] and hashlib.sha256(output.read_bytes()).hexdigest()==item['before']['sha256']
        assert_original_output(metadata,info,item['raw'])
        assert metadata['sha256']==info['sha256'] and metadata['bytes']==len(item['raw']) and metadata['archive_scope']=='local'
        keep('downloads/'+name,output.read_bytes())
        actual_cli(f,env,'read','--reference',reference,'--original-output',output,rejected=True)
        assert output.read_bytes()==item['raw']
        for flags in (['--start',0],['--end',1],['--view','table','--table-id',saved['read']['tables'][0]['table_id']],['--table-id',saved['read']['tables'][0]['table_id']]):
            absent=tmp_path/('refused-'+name)
            actual_cli(f,env,'read','--reference',reference,'--original-output',absent,*flags,rejected=True)
            assert not absent.exists()
        assert saved_state(f)==before
    assert len(seen)==2 and saved_state(f)==before
    assert not log.exists() or log.read_text(encoding='utf-8')==''
    assert all(not item['path'].exists() for item in expected.values())
    observe('cli-snapshot-state-before-after',{'before':before,'after':saved_state(f),'source_paths_absent':True,'observer_events':[]})


def test_cli_observer_has_known_controls(tmp_path):
    source=tmp_path/'private-source.docx';source.write_bytes(b'not content to read')
    env,log=install(tmp_path,[source])
    good=subprocess.run([sys.executable,'-c','print("guard-ready")'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert good.returncode==0 and good.stdout.strip()=='guard-ready' and not log.exists()
    ipc_code='''import asyncio,socket
for factory in {socket.socketpair,getattr(socket,'_fallback_socketpair',socket.socketpair)}:
    left,right=factory()
    try:
        left.sendall(b'pair');assert right.recv(4)==b'pair'
    finally:
        left.close();right.close()
asyncio.run(asyncio.sleep(0))
print('ipc-ready')
'''
    ipc=subprocess.run([sys.executable,'-c',ipc_code],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert ipc.returncode==0 and ipc.stdout.strip()=='ipc-ready' and not log.exists()
    observe('cli-observer-ipc-positive',{'code':ipc.returncode,'stdout':ipc.stdout,'stderr':ipc.stderr})
    controls=[('source-open','from pathlib import Path;Path('+repr(str(source))+').read_bytes()'),('content-import','import pdfplumber'),('spawn','import subprocess,sys;subprocess.run([sys.executable,"-c","pass"])'),('network','import socket;socket.create_connection(("127.0.0.1",9))'),('network','import socket;socket.socket().connect(("127.0.0.1",9))')]
    for kind,code in controls:
        result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
        assert result.returncode!=0 and 'CLI read observer forbidden' in result.stderr
        rows=[json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()];assert rows[-1]['kind']==kind
        observe('cli-observer-control-'+kind,{'code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'event':rows[-1]})
    assert [row['kind'] for row in rows]==[kind for kind,code in controls]
    keep('observer/selfcheck.jsonl',log.read_bytes())

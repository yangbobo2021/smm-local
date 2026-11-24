"""Creator-authoritative bytes/results; Hub may only validate and index."""
import builtins,hashlib,json
from pathlib import Path
import pytest
from document_helpers import deny_source_reads,observe
from document_formats_sync_observer import install as install_sync_observer
from test_hub_documents_contracts import w
from test_document_formats_retry import ENGINE,DATA,FONT,keep,cli
from document_formats_fixtures import docx_fixture
from document_formats_xlsx_fixture import xlsx_fixture
from document_formats_pdf_fixture import native_pdf
from document_formats_ocr_fixture import scanned_fixture
from document_formats_partial_fixture import partial_pdf


@pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='full fixture requires explicitly prepared real OCR assets')
def test_creator_results_sync_exactly_without_receiver_processing(w,monkeypatch):
    # TC-008-direct-index. Creator result bytes are the normative transfer value;
    # original parsing correctness is separately tested against source truth.
    from smm_local import federation
    from smm_local.documents import Documents
    from smm_local.document_snapshots import Snapshots
    project=w.project('008 sync allowed');private_project=w.project('008 private')
    items={}
    for key in ('alpha','beta'):
        for format in ('docx','xlsx','native','scan'):
            ident='sync'+format+key
            if format=='docx':raw,truth=docx_fixture(ident);anchor=truth['words'][0];extension='docx'
            elif format=='xlsx':raw,truth=xlsx_fixture(ident);anchor=truth['title'];extension='xlsx'
            elif format=='native':raw,truth=native_pdf(ident);anchor=truth['pages'][0]['heading'];extension='pdf'
            else:raw,truth=scanned_fixture(FONT,key);anchor=truth['pages'][0]['title'];extension='pdf'
            name=ident+'.'+extension;path=w.local.file('shared/'+name,raw=raw)
            items[name]={'path':path,'raw':raw,'anchor':anchor,'expected_status':'ready'};keep('inputs/'+name,raw)
    for key in ('alpha','beta'):
        raw,truth=partial_pdf('syncpartial'+key,FONT);name='partial-'+key+'.pdf';path=w.local.file('shared/'+name,raw=raw)
        items[name]={'path':path,'raw':raw,'anchor':truth['anchor'],'expected_status':'partial'};keep('inputs/'+name,raw)
    status=cli(w.local,'processing-status');cli(w.local,'processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    source=w.local.add(w.local.root/'docs/shared',projects=[project]);w.local.refresh(source)
    files={Path(entry['path']).name:entry for entry in w.local.files(source)}
    assert set(files)==set(items) and all(entry['status']=='ready' for entry in files.values())
    for name,item in items.items():
        entry=files[name];published=entry['published_snapshot'];assert published is not None
        norm_path=w.pair.local.db_path.resolve().parent/'.document-snapshots/results'/published['result_sha256']
        raw_result=norm_path.read_bytes();assert hashlib.sha256(raw_result).hexdigest()==published['result_sha256']
        value=json.loads(raw_result);assert value['raw_sha256']==hashlib.sha256(item['raw']).hexdigest()
        assert item['anchor'] in value['text'] and value['status']==item['expected_status']==published['status']
        if item['expected_status']=='partial':assert any(error['page']==2 and '1600万像素' in error['reason'] for error in value['coverage']['errors'])
        item.update(entry=entry,result=value,result_bytes=raw_result);keep('creator-results/'+name+'.json',raw_result)
    private_raw=docx_fixture('neveruploadsecret')[0];private_path=w.local.file('private/do-not-sync.docx',raw=private_raw)
    private_source=w.local.add(private_path,projects=[private_project]);w.local.refresh(private_source)
    private_entry=w.local.files(private_source)[0]
    assert private_entry['published_snapshot'] is not None
    wire=[];bodies=[]
    def binary(config,route,raw=None,*,method='PUT',payload=None,headers=None):
        kwargs={'headers':headers or {}}
        if payload is not None:kwargs['json']=payload
        elif raw is not None:kwargs['content']=raw
        response=w.hub.request(method,'/v1'+route,**kwargs)
        record={'method':method,'route':route,'payload':payload,'status':response.status_code,'request_bytes':len(raw) if raw is not None else 0,'request_sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'headers':dict(headers or {})}
        wire.append(record)
        if raw is not None:bodies.append(raw);keep('wire/'+str(len(wire))+'.bin',raw)
        observe('processed-binary-'+str(len(wire)),record)
        if response.status_code>=400:
            error=federation.HubUnavailable(response.text);error.status=response.status_code;raise error
        return response.json() if 'json' in response.headers.get('content-type','') else response.content
    monkeypatch.setattr(federation,'_request_binary',binary,raising=False)
    info=w.remote('GET','/info');assert 'processed_documents_v1' in info['capabilities']
    default_calls=len(w.calls);default_wire=len(wire)
    before=w.sync();assert not before['pending']
    for item in items.values():assert w.search_hub(item['anchor'],limit=50)['results']==[]
    assert w.search_hub('neveruploadsecretTitle',limit=50)['results']==[]
    assert w.remote('GET','/documents/files')==[]
    protected=[]
    for name,item in items.items():protected.extend([name,item['anchor'],item['entry']['id'],hashlib.sha256(item['raw']).hexdigest(),item['entry']['published_snapshot']['result_sha256']])
    protected.extend(['do-not-sync.docx','neveruploadsecret',private_entry['id'],hashlib.sha256(private_raw).hexdigest(),private_entry['published_snapshot']['result_sha256']])
    def strings(value):
        if isinstance(value,str):yield value
        elif isinstance(value,dict):
            for key,item in value.items():yield from strings(key);yield from strings(item)
        elif isinstance(value,(list,tuple)):
            for item in value:yield from strings(item)
    sent=list(strings(w.calls[default_calls:]+wire[default_wire:]))
    assert all(not any(token in value for token in protected) for value in sent)
    assert all(item['request_bytes']==0 for item in wire[default_wire:])
    observe('default-off-complete',{'calls':w.calls[default_calls:],'wire':wire[default_wire:],'targets':len(items)+1,'hub_files':[]})
    w.policy(project,True);w.policy(private_project,False)
    attempts=install_sync_observer(monkeypatch)
    source_reads=deny_source_reads(monkeypatch,private_path,*[item['path'] for item in items.values()])
    for item in items.values():item['path'].unlink()
    synced=w.sync();assert not synced['pending'],synced
    def verify_hub(phase):
        project_record=w.hub_project_for(project);observed_ids=set();origin_ids=set();all_ids=set()
        listed=w.remote('GET','/documents/files');assert len(listed)==10 and len({entry['id'] for entry in listed})==10
        listed_by_id={entry['id']:entry for entry in listed}
        for name,item in items.items():
            result=w.search_hub(item['anchor'],scope='project',project_id=project_record['id'],limit=50)
            all_ids.update(hit['id'] for hit in result['results'])
            own=[hit for hit in result['results'] if hit['origin']=={'device_id':w.device,'archive_id':w.archive,'document_id':item['entry']['id']}]
            assert len(own)==1;hit=own[0];observed_ids.add(hit['id']);origin_ids.add(hit['origin']['document_id'])
            assert listed_by_id[hit['id']]['published_snapshot']['status']==item['expected_status']
            assert hit['version']==item['entry']['version'] and hit['processing_version']==item['entry']['processing_version']
            assert hit['sha256']==hashlib.sha256(item['raw']).hexdigest() and hit['result_sha256']==item['entry']['published_snapshot']['result_sha256']
            read=w.read_hub(hit,start=0,end=len(item['result']['text']))
            for field in ('text','locations','coverage','profile'):assert read[field]==item['result'][field],(name,field)
            tables=item['result']['tables'];assert read['tables']==[{key:value for key,value in table.items() if key!='cells'} for table in tables]
            for table in tables:
                view=w.read_hub(hit,view='table',table_id=table['table_id'],row_start=1,row_end=table['rows']+1,column_start=1,column_end=table['columns']+1)
                assert all(view[key]==value for key,value in table.items()),(name,table['table_id'])
            response=w.hub.post('/v1/documents/original',json={**w.context(),'reference':hit['reference']})
            assert response.status_code==200 and response.content==item['raw'];keep('downloads/'+phase+'/'+name,response.content)
            observe('direct-index-'+phase+'-'+name,{'hit':hit,'read':read,'canonical_result_sha256':hit['result_sha256'],'original_sha256':hashlib.sha256(response.content).hexdigest()})
        assert len(observed_ids)==len(origin_ids)==len(items)==10 and all_ids==observed_ids
        listed=w.remote('GET','/documents/files');assert len(listed)==10 and {entry['id'] for entry in listed}==observed_ids
        return sorted(origin_ids)
    origin_ids=verify_hub('first')
    repeated=w.sync();assert not repeated['pending']
    assert verify_hub('repeat')==origin_ids
    assert w.search_hub('neveruploadsecretTitle',limit=50)['results']==[]
    assert all(private_raw not in raw and b'neveruploadsecret' not in raw for raw in bodies)
    private_tokens=['do-not-sync.docx','neveruploadsecret',private_entry['id'],hashlib.sha256(private_raw).hexdigest(),private_entry['published_snapshot']['result_sha256']]
    assert all(not any(token in value for token in private_tokens) for value in strings(w.calls+wire))
    assert attempts==[] and source_reads==[]
    observe('direct-index-final',{'synced':synced,'repeated':repeated,'wire':wire,'processing_attempts':attempts,'source_reads':source_reads,'origin_ids':origin_ids})


def test_sync_observer_known_positive_and_negative_controls(monkeypatch):
    import socket,subprocess,sys
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from smm_local.documents import Documents
    from smm_local.document_snapshots import Snapshots
    attempts=install_sync_observer(monkeypatch)
    assert json.loads('{"ok":true}')=={'ok':True}
    app=FastAPI()
    @app.get('/probe')
    def probe():return {'known':'allowed'}
    with TestClient(app) as client:
        result=client.get('/probe');assert result.status_code==200 and result.json()=={'known':'allowed'}
    assert attempts==[]
    for action in (lambda:Documents._scan(None,{}),lambda:Snapshots.process(None,{},'pdf'),lambda:builtins.__import__('pdfplumber'),lambda:subprocess.Popen([sys.executable,'-c','print(1)']),lambda:socket.create_connection(('127.0.0.1',1))):
        before=len(attempts)
        with pytest.raises(AssertionError):action()
        assert len(attempts)==before+1
    with socket.socket() as channel:
        before=len(attempts)
        with pytest.raises(AssertionError):channel.connect(('127.0.0.1',1))
        assert len(attempts)==before+1
    assert len(attempts)==6
    observe('receiver-observer-selfcheck',{'attempts':attempts,'real_http_positive':True})


@pytest.mark.skipif(not FONT,reason='requires explicitly frozen font')
def test_partial_fixture_has_known_native_and_oversized_ocr_pages():
    import pdfplumber
    from io import BytesIO
    for key in ('alpha','beta'):
        raw,truth=partial_pdf('syncpartial'+key,FONT)
        with pdfplumber.open(BytesIO(raw)) as pdf:
            assert len(pdf.pages)==truth['page_count']==2
            assert pdf.pages[0].extract_text()==truth['anchor'] and not pdf.pages[0].images
            assert not pdf.pages[1].chars and len(pdf.pages[1].images)==1
            assert pdf.pages[1].width==2000 and pdf.pages[1].height==1000
            assert pdf.pages[1].width*pdf.pages[1].height*(300/72)**2>16000000

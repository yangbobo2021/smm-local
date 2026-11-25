"""Files and project libraries provide readable original refs without FTS hits."""
import hashlib,json,time
from pathlib import Path
import pytest
from document_helpers import observe,deny_source_reads
from document_formats_managed_empty_fixture import blank_original
from document_formats_sync_observer import install as no_processing
from test_document_formats_retry import keep
from test_hub_documents_contracts import w


def saved_state(db):
    with db.connect() as c:
        names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0]=='documents' or r[0].startswith(('document_','hub_document_'))]
        return {name:sorted([dict(row) for row in c.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,sort_keys=True,default=str)) for name in names}


def test_managed_empty_inputs_have_no_body_or_table_cells():
    from io import BytesIO
    from zipfile import ZipFile
    import xml.etree.ElementTree as E
    import pypdfium2
    hashes=set()
    for owner in ('local','hub'):
        for key in ('alpha','beta'):
            for format in ('docx','xlsx','pdf'):
                raw=blank_original(format,owner+format+key);digest=hashlib.sha256(raw).hexdigest()
                assert digest not in hashes;hashes.add(digest)
                if format in ('docx','xlsx'):
                    with ZipFile(BytesIO(raw)) as z:
                        assert z.testzip() is None
                        if format=='docx':assert not [n for n in E.fromstring(z.read('word/document.xml')).iter() if n.tag.endswith('}t')]
                        else:
                            sheets=[n for n in z.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml')];assert len(sheets)==1
                            assert all(not [n for n in E.fromstring(z.read(name)).iter() if n.tag.endswith('}c')] for name in sheets)
                else:
                    pdf=pypdfium2.PdfDocument(raw);assert len(pdf)==1
                    page=pdf[0];text=page.get_textpage();assert text.count_chars()==0;text.close();page.close();pdf.close()
    assert len(hashes)==12


@pytest.mark.parametrize('owner',['local','hub'])
def test_each_managed_empty_document_has_files_and_library_original_refs(w,monkeypatch,owner):
    # TC-008-managed-empty-original. Empty input truth precedes all SMM reads.
    client=w.local.client if owner=='local' else w.hub;prefix='/api' if owner=='local' else '/v1'
    context={} if owner=='local' else w.context();db=w.pair.local if owner=='local' else w.pair.remote
    def request(method,path,body=None,raw=None,headers=None):
        args={'headers':headers or {}}
        if body is not None:args['json']=body
        if raw is not None:args['content']=raw
        response=client.request(method,prefix+path,**args)
        value=response.json() if 'json' in response.headers.get('content-type','') else {'bytes':len(response.content),'sha256':hashlib.sha256(response.content).hexdigest()}
        observe('managed-empty-'+owner,{'method':method,'path':path,'body':body,'raw_bytes':len(raw) if raw is not None else None,'status':response.status_code,'response':value})
        assert response.status_code==200,response.text
        return response
    if owner=='local':projects=[request('POST','/projects',{'name':'blank ordinary'}).json(),request('POST','/projects/global').json()]
    else:projects=[w.hub_project('blank ordinary'),w.hub_project('blank global',kind='global')]
    expected={};by_project={p['id']:set() for p in projects}
    for key,project in zip(('alpha','beta'),projects):
        for format in ('docx','xlsx','pdf'):
            label=owner+format+key;raw=blank_original(format,label);digest=hashlib.sha256(raw).hexdigest()
            keep('inputs/'+label+'.'+format,raw)
            start=request('POST','/documents/uploads',{**context,'project_id':project['id'],'project_key':project['stable_key'] if owner=='local' else project['source_key'],'submission_id':'blank-'+label,'name':'blank.'+format,'sha256':digest,'bytes':len(raw)}).json()
            size=start['block_bytes'];assert size>0
            for index,offset in enumerate(range(0,len(raw),size)):
                chunk=raw[offset:offset+size];request('PUT','/documents/uploads/'+start['upload_id']+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
            receipt=request('POST','/documents/uploads/'+start['upload_id']+'/commit',context).json();ident=receipt['document_id'];assert ident not in expected
            expected[ident]={'raw':raw,'sha256':digest,'format':format,'project_id':project['id'],'label':label,'receipt':receipt};by_project[project['id']].add(ident)
    deadline=time.monotonic()+60
    while True:
        listed=request('GET','/documents/files').json()
        if len(listed)==6 and all((row.get('latest_attempt') or {}).get('status') in {'ready','partial','failed','empty-success'} for row in listed):break
        assert time.monotonic()<deadline,listed
        time.sleep(.05)
    assert len(listed)==len({r['id'] for r in listed})==6 and {r['id'] for r in listed}==set(expected)
    with db.connect() as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    for row in listed:
        item=expected[row['id']];item['source_id']=row['source_id'];item['path']=Path(row['path'])
        assert row['version']==row['processing_version']==1 and row['text_length']==0 and row['sha256']==item['sha256']
        assert row['status']=='ready' and row['published_snapshot']['status']=='empty-success' and row['latest_attempt']['status']=='empty-success'
        assert row['latest_attempt']['capture_id']==item['receipt']['capture_id'] and row['latest_attempt']['attempt_id']==item['receipt']['attempt_id']
        item['path'].unlink()
    attempts=no_processing(monkeypatch);opens=deny_source_reads(monkeypatch,*[item['path'] for item in expected.values()]);before=saved_state(db)
    def verify_rows(rows,expected_ids,entrypoint):
        assert len(rows)==len({row['id'] for row in rows})==len(expected_ids) and {row['id'] for row in rows}==expected_ids
        for row in rows:
            ident=row['id'];item=expected[ident];reference=row.get('original_reference')
            assert isinstance(reference,str) and reference,{'entrypoint':entrypoint,'id':ident,'reason':'qualified blank original requires a readable reference'}
            assert row['version']==row['processing_version']==1 and row['sha256']==item['sha256']
            if 'original_available' in row:assert row['original_available'] is True
            info=request('POST','/documents/read',{**context,'reference':reference,'view':'original-info'}).json()
            origin={'device_id':w.device if owner=='local' else context['hub_id'],'archive_id':archive,'document_id':ident}
            assert info['id']==ident and info['origin']==origin and info['archive_scope']==owner and info['source_ids']==[item['source_id']]
            assert info['version']==info['processing_version']==1 and info['format']==item['format']
            assert info['available'] is True and info.get('reason') is None and info['bytes']==len(item['raw']) and info['sha256']==item['sha256']
            response=request('POST','/documents/original',{**context,'reference':reference})
            keep('downloads/'+entrypoint+'-'+item['label']+'.'+item['format'],response.content);assert response.content==item['raw']
            assert saved_state(db)==before
    verify_rows(request('GET','/documents/files').json(),set(expected),'files')
    for project in projects:
        verify_rows(request('GET','/documents/library?project_id='+str(project['id'])).json(),by_project[project['id']],'library')
        result=request('POST','/documents/search',{**context,'query':'neverpresentbody987654','scope':'project','project_id':project['id'],**({'local':True} if owner=='local' else {})}).json()
        assert result['results']==[]
    assert saved_state(db)==before and attempts==[] and opens==[] and all(not item['path'].exists() for item in expected.values())
    observe('managed-empty-complete',{'owner':owner,'ids':sorted(expected),'project_ids':{str(k):sorted(v) for k,v in by_project.items()},'archive':archive,'source_reads':opens,'processing_external_attempts':attempts,'full_state_unchanged':True})

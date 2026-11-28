"""Creator-owned binary upload HTTP contracts; E/H/browser paths are separate."""
import hashlib,json,time
from pathlib import Path
import pytest
from document_helpers import observe
from document_formats_upload_fixture import upload_input
from test_document_formats_retry import keep
from test_hub_documents_contracts import w


def test_upload_sources_are_complete_and_distinct():
    from io import BytesIO
    from zipfile import ZipFile
    import pypdfium2
    hashes=set()
    for owner in ('local','hub'):
        for format in ('docx','xlsx','pdf'):
            for key in ('alpha','beta'):
                raw,truth=upload_input(format,owner+format+key)
                assert len(truth['words'])==len(set(truth['words'])) and truth['tables']
                if format=='docx':assert 1024*1024<len(raw)<20*1024*1024
                if format in ('docx','xlsx'):
                    with ZipFile(BytesIO(raw)) as source:assert source.testzip() is None
                else:
                    pdf=pypdfium2.PdfDocument(raw);assert len(pdf)==2;pdf.close()
                digest=hashlib.sha256(raw).hexdigest();assert digest not in hashes;hashes.add(digest)
    assert len(hashes)==12


def test_managed_native_uploads_are_searchable_on_each_creator(w):
    # TC-008-managed-native-upload: two independent inputs per format/creator.
    ordinary=w.local.request('POST','/api/projects',{'name':'008 upload ordinary'})
    global_project=w.local.request('POST','/api/projects/global')
    locals=[ordinary,global_project]
    assert [p['kind'] for p in locals]==['ordinary','global']
    hubs=[w.hub_project('008 upload ordinary'),w.hub_project('008 upload global',kind='global')]
    assert [p['project_kind'] for p in hubs]==['ordinary','global']
    all_ids={};expected_ids={'local':set(),'hub':set()}
    for owner,projects in (('local',locals),('hub',hubs)):
        client=w.local.client if owner=='local' else w.hub
        prefix='/api' if owner=='local' else '/v1'
        context={} if owner=='local' else w.context()
        verified=[]
        def request(method,path,body=None,raw=None,headers=None,reject=False):
            kwargs={'headers':headers or {}}
            if raw is not None:kwargs['content']=raw
            elif body is not None:kwargs['json']=body
            reply=client.request(method,prefix+path,**kwargs)
            value=reply.json() if 'json' in reply.headers.get('content-type','') else {'bytes':len(reply.content),'sha256':hashlib.sha256(reply.content).hexdigest()}
            observe('managed-'+owner,{'method':method,'path':path,'request':body,'headers':headers,'raw_bytes':len(raw) if raw is not None else None,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'status':reply.status_code,'response':value})
            if reject:assert 400<=reply.status_code<500,reply.text
            else:assert reply.status_code==200,reply.text
            return reply
        def search(query,project):
            return request('POST','/documents/search',{**context,'query':query,'scope':'project','project_id':project['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
        for format in ('docx','xlsx','pdf'):
            for key,project,other in (('alpha',projects[0],projects[1]),('beta',projects[1],projects[0])):
                label=owner+format+key;raw,truth=upload_input(format,label);anchor=truth['words'][0].split()[0]
                keep('inputs/'+label+'.'+format,raw);keep('truth/'+label+'.json',json.dumps(truth,ensure_ascii=False).encode())
                assert search(anchor,project)==[]
                before_files=request('GET','/documents/files').json()
                before_library=request('GET','/documents/library').json()
                def unpublished():
                    listed=request('GET','/documents/files').json();library=request('GET','/documents/library').json()
                    prior_refs={row.get('original_reference') for row in before_files+before_library if row.get('original_reference')}
                    exposed={row.get('original_reference') for row in listed+library if row.get('original_reference')} - prior_refs
                    for reference in exposed:
                        for view in ('text','original-info'):
                            request('POST','/documents/read',{**context,'reference':reference,'view':view},reject=True)
                        request('POST','/documents/original',{**context,'reference':reference},reject=True)
                    # B7: an uncommitted upload must not register a new material
                    # or grant any existing material a new snapshot/reference.
                    assert listed==before_files and library==before_library
                    assert search(anchor,project)==[]
                    observe('unpublished-'+label,{'upload_id':upload,'files_unchanged':True,'library_unchanged':True,'unexpected_references':sorted(exposed)})
                begin={**context,'project_id':project['id'],'project_key':project['stable_key'] if owner=='local' else project['source_key'],'submission_id':'008-'+label,'name':'same-name.'+format,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
                started=request('POST','/documents/uploads',begin).json()
                upload=started['upload_id'];size=started['block_bytes'];assert type(size) is int and 0<size<=1024*1024
                assert started['received_parts']==[]
                unpublished()
                chunks=[raw[offset:offset+size] for offset in range(0,len(raw),size)]
                if format=='docx':assert len(chunks)>=2
                for index,chunk in enumerate(chunks):
                    if index==len(chunks)-1 and len(chunks)>1:
                        request('POST','/documents/uploads/'+upload+'/commit',context,reject=True)
                        unpublished()
                    part=request('PUT','/documents/uploads/'+upload+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()}).json()
                    assert index in part['received_parts']
                    unpublished()
                committed=request('POST','/documents/uploads/'+upload+'/commit',context).json()
                ident=committed['document_id'];assert ident not in all_ids
                assert committed['capture_id'] and committed['attempt_id'] and committed['status'] in {'pending','processing','ready','partial','failed'}
                deadline=time.monotonic()+30
                while True:
                    files=request('GET','/documents/files').json();own=[entry for entry in files if entry['id']==ident]
                    if own and (own[0].get('latest_attempt') or {}).get('status') in {'ready','partial','failed'}:break
                    assert time.monotonic()<deadline,files
                    time.sleep(.02)
                entry=own[0];published=entry['published_snapshot']
                assert published is not None and published['status']=='ready'
                assert entry['version']==entry['processing_version']==1 and entry['sha256']==begin['sha256']
                assert entry['latest_attempt']['attempt_id']==committed['attempt_id'] and entry['latest_attempt']['capture_id']==committed['capture_id']
                library=request('GET','/documents/library?project_id='+str(project['id'])).json()
                assert len([row for row in library if row['id']==ident])==1
                hits=search(anchor,project);assert len(hits)==1 and hits[0]['id']==ident
                assert search(anchor,other)==[]
                hit=hits[0];assert hit['format']==format and hit['version']==hit['processing_version']==1
                assert hit['sha256']==begin['sha256']
                read=request('POST','/documents/read',{**context,'reference':hit['reference'],'start':0,'end':hit['text_length']}).json()
                assert read['id']==ident and read['version']==read['processing_version']==1
                assert all(word in read['text'] for word in truth['words'])
                assert all(word not in read['text'] for word in truth['excluded'])
                assert len(read['tables'])==len(truth['tables'])
                tables=[];complete_tables=[]
                for expected in truth['tables']:
                    candidates=[table for table in read['tables'] if all(table['location'].get(k)==v for k,v in expected['location'].items())]
                    # Same-page PDF tables are selected by source-defined first cell.
                    actual=[]
                    for table in candidates:
                        view=request('POST','/documents/read',{**context,'reference':hit['reference'],'view':'table','table_id':table['table_id'],'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1}).json()
                        if any(cell['text']==expected['cells'][0][2] for cell in view['cells']):actual.append(view)
                    assert len(actual)==1;view=actual[0];tables.append(view['table_id']);complete_tables.append(view)
                    assert (view['rows'],view['columns'])==(expected['rows'],expected['columns'])
                    cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
                    assert len(cells)==len(set((c[0],c[1]) for c in cells))==len(expected['cells']) and set(cells)==set(expected['cells'])
                assert len(set(tables))==len(truth['tables'])
                info=request('POST','/documents/read',{**context,'reference':hit['reference'],'view':'original-info'}).json()
                assert info['id']==ident and info['version']==info['processing_version']==1 and info['format']==format
                assert info['sha256']==begin['sha256'] and info['bytes']==len(raw) and info['available'] is True
                response=request('POST','/documents/original',{**context,'reference':hit['reference']})
                keep('downloads/'+label+'.'+format,response.content);assert response.content==raw
                verified.append({'id':ident,'label':label,'raw':raw,'truth':truth,'anchor':anchor,'project':project,'other':other,'hit':hit,'read':read,'tables':complete_tables,'info':info,'entry':entry})
                all_ids[ident]=label;expected_ids[owner].add(ident)
        final_files=request('GET','/documents/files').json()
        assert {entry['id'] for entry in final_files}==expected_ids[owner]
        for saved in verified:
            # Later uploads of the same display name must preserve every prior
            # document, including its original blob, complete result and refs.
            ident=saved['id'];raw=saved['raw'];old=saved['entry']
            current=next(entry for entry in final_files if entry['id']==ident)
            assert current==old
            found=search(saved['anchor'],saved['project'])
            assert len(found)==1 and found[0]['id']==ident and found[0]['sha256']==hashlib.sha256(raw).hexdigest()
            assert search(saved['anchor'],saved['other'])==[]
            reference=saved['hit']['reference']
            value=request('POST','/documents/read',{**context,'reference':reference,'start':0,'end':saved['hit']['text_length']}).json()
            assert value==saved['read'] and all(word in value['text'] for word in saved['truth']['words'])
            for table in saved['tables']:
                value=request('POST','/documents/read',{**context,'reference':reference,'view':'table','table_id':table['table_id'],'row_start':1,'row_end':table['rows']+1,'column_start':1,'column_end':table['columns']+1}).json()
                assert value==table
            info=request('POST','/documents/read',{**context,'reference':reference,'view':'original-info'}).json()
            assert info==saved['info'] and info['id']==ident and info['sha256']==hashlib.sha256(raw).hexdigest() and info['bytes']==len(raw)
            response=request('POST','/documents/original',{**context,'reference':reference})
            keep('downloads/final-'+saved['label']+'.'+saved['hit']['format'],response.content)
            assert response.content==raw
            observe('same-name-preserved-'+saved['label'],{'id':ident,'sha256':hashlib.sha256(response.content).hexdigest(),'version':current['version'],'processing_version':current['processing_version'],'complete_tables':[table['table_id'] for table in saved['tables']]})
    status=w.status()
    for p in locals:
        state=next(row for row in status['projects'] if row['project_id']==p['id']);assert state['enabled'] is False
    assert len(all_ids)==12 and len(expected_ids['local'])==len(expected_ids['hub'])==6
    observe('creator-upload-complete',{'document_ids':all_ids,'local_ids':sorted(expected_ids['local']),'hub_ids':sorted(expected_ids['hub']),'status':status})

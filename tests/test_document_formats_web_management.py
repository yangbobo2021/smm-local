"""Actual ready document update/remove UI, separate from retained initial-upload gaps."""
import hashlib,json,os,re,sqlite3,time
from pathlib import Path
import pytest
from document_helpers import observe
from test_document_formats_management import native_input
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server
from document_formats_web_helpers import Browser

BROWSER=pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'),reason='requires frozen actual Chromium; skipped is not Web/platform evidence')


def business(server):
    with sqlite3.connect(server.db) as c:
        names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%') ORDER BY name")]
        return {name:hashlib.sha256(json.dumps(sorted([list(r) for r in c.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,default=str)),ensure_ascii=False,default=str).encode()).hexdigest() for name in names}


def current(server,item):
    return next(e for e in server.call('GET','/documents/library').json() if e['id']==item['id'])


def wait_ready(server,item,version,page=None):
    until=time.monotonic()+35
    while True:
        value=current(server,item)
        with sqlite3.connect(server.db) as c:pending=c.execute("SELECT count(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0]
        if value['version']==value['processing_version']==version and value['latest_attempt']['status']=='ready' and not pending:return value
        assert value['latest_attempt']['status']!='failed',value
        assert time.monotonic()<until,value
        if page:page.wait_for_timeout(50)
        else:time.sleep(.05)


def prepare(server):
    server.start()
    p=server.call('POST','/projects',{'name':'UI ordinary'} if server.owner=='local' else {**server.context,'name':'UI ordinary','kind':'ordinary'}).json()
    g=server.call('POST','/projects/global').json() if server.owner=='local' else server.call('POST','/projects',{**server.context,'name':'UI global','kind':'global'}).json()
    items=[]
    for key,project in (('ordinary',p),('global',g)):
        for format in ('docx','xlsx','pdf'):
            label=server.owner+key+format
            materials={v:native_input(format,label+'v'+str(v)) for v in (1,2)}
            item={'label':label,'name':'shared.'+format,'format':format,'materials':materials,'project':project,'other':g if project['id']==p['id'] else p,'version':1}
            for v,(raw,truth) in materials.items():
                keep('inputs/'+label+str(v)+'.'+format,raw);keep('truth/'+label+str(v)+'.json',json.dumps(truth,ensure_ascii=False).encode())
            raw,truth=materials[1]
            body={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if server.owner=='local' else project['source_key'],'submission_id':label+'initial','name':item['name'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            start=server.call('POST','/documents/uploads',body).json()
            for n,offset in enumerate(range(0,len(raw),start['block_bytes'])):
                chunk=raw[offset:offset+start['block_bytes']];server.call('PUT','/documents/uploads/'+start['upload_id']+'/parts/'+str(n),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
            receipt=server.call('POST','/documents/uploads/'+start['upload_id']+'/commit',server.context).json();item['id']=receipt['document_id']
            item['entry']=wait_ready(server,item,1);assert item['entry']['latest_attempt']['capture_id']==receipt['capture_id'] and item['entry']['latest_attempt']['attempt_id']==receipt['attempt_id']
            items.append(item)
    rows=server.call('GET','/documents/library').json();assert {e['id'] for e in rows}=={i['id'] for i in items}
    for project in (p,g):assert len([i for i in items if i['project']['id']==project['id']])==3
    return items


def assert_metadata(value,server,item):
    with sqlite3.connect(server.db) as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    assert value['id']==item['id'] and value['version']==value['processing_version']==item['version']
    assert value['origin']=={'device_id':archive if server.owner=='local' else server.context['hub_id'],'archive_id':archive,'document_id':item['id']}
    assert value['format']==item['format'] and value['sha256']==hashlib.sha256(item['materials'][item['version']][0]).hexdigest()


def same_source_table(view,expected):
    cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
    return (view['rows'],view['columns'])==(expected['rows'],expected['columns']) and len(cells)==len(set(cells))==len(expected['cells']) and set(cells)==set(expected['cells'])


def verify(server,item):
    raw,truth=item['materials'][item['version']];anchor=truth['words'][0].split()[0]
    body={**server.context,'query':anchor,'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if server.owner=='local' else {})}
    hits=server.call('POST','/documents/search',body).json()['results'];assert [h['id'] for h in hits]==[item['id']]
    hit=hits[0];assert_metadata(hit,server,item)
    assert server.call('POST','/documents/search',{**body,'project_id':item['other']['id']}).json()['results']==[]
    value=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'start':0,'end':hit['text_length']}).json();assert_metadata(value,server,item)
    assert all(word in value['text'] for word in truth['words']) and all(word not in value['text'] for word in truth['excluded'])
    assert len(value['tables'])==len({t['table_id'] for t in value['tables']})==len(truth['tables'])
    used=set()
    for expected in truth['tables']:
        # PDF truth can name a page containing multiple tables. Distinguish
        # them with the complete independent source cells, never list order.
        tables=[t for t in value['tables'] if (t['rows'],t['columns'])==(expected['rows'],expected['columns']) and all(t['location'].get(k)==v for k,v in expected['location'].items())]
        matched=[]
        for table in tables:
            view=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'view':'table','table_id':table['table_id'],'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1}).json();assert_metadata(view,server,item)
            if same_source_table(view,expected):matched.append(table['table_id'])
        assert len(matched)==1 and matched[0] not in used
        used.add(matched[0])
    assert used=={t['table_id'] for t in value['tables']}
    downloaded=server.call('POST','/documents/original',{**server.context,'reference':hit['reference']}).content;assert downloaded==raw
    keep('verified-originals/'+hashlib.sha256(downloaded).hexdigest()+'.'+item['format'],downloaded)
    return hit


def reject_reference(server,item,reference,phase):
    before=business(server);events=server.events()
    for endpoint in ('/documents/read','/documents/original'):
        denied=server.client.post(server.prefix+endpoint,json={**server.context,'reference':reference})
        observe('web-management-reference-rejected',{'owner':server.owner,'id':item['id'],'phase':phase,'endpoint':endpoint,'status':denied.status_code,'response':denied.json()})
        assert 400<=denied.status_code<500
    assert business(server)==before and server.events()==events


def row(browser,item):
    return browser.page.locator('#doc-library-list .result' if browser.owner=='local' else '#hub-library-list .result').filter(has_text='文档 '+item['id'])


def assert_compare(body,server,item,entry,*,update=False):
    p=item['project']
    expected={**server.context,'project_id':p['id'],'project_key':p['stable_key'] if server.owner=='local' else p['source_key'],'expected_version':entry['version'],'expected_processing_version':entry['processing_version'],'expected_revision':entry['source_revision']}
    latest=entry['latest_attempt'];published=entry.get('published_snapshot') or {}
    # Ready published rows may omit the optional candidate pair. If included,
    # both fields must match; an unpublished candidate requires the pair.
    if latest['capture_id']!=published.get('capture_id') or {'capture_id','expected_attempt_id'}.intersection(body):
        expected.update(capture_id=latest['capture_id'],expected_attempt_id=latest['attempt_id'])
    if update:expected['document_id']=item['id']
    for key,value in expected.items():assert type(body.get(key)) is type(value) and body[key]==value,key


@pytest.mark.parametrize('owner',['local','hub'])
def test_ready_comparison_oracle_allows_optional_pair_and_rejects_wrong_values(owner):
    from types import SimpleNamespace
    server=SimpleNamespace(owner=owner,context={} if owner=='local' else {'hub_id':'hub','document_epoch':4})
    item={'id':'doc','project':{'id':7,'stable_key':'local-key','source_key':'hub-key'}}
    entry={'version':1,'processing_version':1,'source_revision':3,'published_snapshot':{'capture_id':'saved'},'latest_attempt':{'capture_id':'saved','attempt_id':'attempt','status':'ready'}}
    base={**server.context,'project_id':7,'project_key':'local-key' if owner=='local' else 'hub-key','expected_version':1,'expected_processing_version':1,'expected_revision':3,'document_id':'doc'}
    assert_compare(base,server,item,entry,update=True)
    full={**base,'capture_id':'saved','expected_attempt_id':'attempt'};assert_compare(full,server,item,entry,update=True)
    rejected=[]
    for key in full:
        wrong={**full,key:None}
        with pytest.raises(AssertionError):assert_compare(wrong,server,item,entry,update=True)
        rejected.append(key)
    with pytest.raises(AssertionError):assert_compare({**base,'expected_version':True},server,item,entry,update=True)
    for partial in ({**base,'capture_id':'saved'},{**base,'expected_attempt_id':'attempt'}):
        with pytest.raises(AssertionError):assert_compare(partial,server,item,entry,update=True)
    observe('web-ready-compare-known-controls',{'owner':owner,'minimal_ready_pair_optional':True,'full_ready_pair_valid':True,'wrong_fields_rejected':rejected,'bool_version_rejected':True,'half_pair_rejected':2})

def test_full_source_table_oracle_rejects_same_page_other_table_and_bad_cells():
    from copy import deepcopy
    expected={'rows':1,'columns':1,'cells':[(1,1,'second table source',1,1)]}
    good={'rows':1,'columns':1,'cells':[{'row':1,'column':1,'text':'second table source','row_span':1,'column_span':1}]}
    first=deepcopy(good);first['cells'][0]['text']='first table source'
    assert same_source_table(good,expected) and not same_source_table(first,expected)
    rejected=[]
    for field,value in (('row',2),('column',2),('text','wrong'),('row_span',2),('column_span',2)):
        bad=deepcopy(good);bad['cells'][0][field]=value;assert not same_source_table(bad,expected);rejected.append(field)
    for change in ({'rows':2},{'columns':2},{'cells':[]},{'cells':good['cells']*2}):
        assert not same_source_table({**good,**change},expected)
    observe('web-management-table-known-controls',{'other_same_page_table_rejected':True,'wrong_cell_fields_rejected':rejected,'bad_dimensions_empty_duplicates_rejected':4})



@BROWSER
def test_real_browser_file_chooser_preserves_selected_original_bytes():
    from playwright.sync_api import sync_playwright
    raw=b'known selected file bytes'
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page();page.set_content('<input id=sample type=file accept=".docx">')
            with page.expect_file_chooser() as chosen:page.locator('#sample').click()
            chosen.value.set_files({'name':'probe.docx','mimeType':'application/octet-stream','buffer':raw})
            value=page.locator('#sample').evaluate('async e=>{const f=e.files[0];return {name:f.name,type:f.type,bytes:Array.from(new Uint8Array(await f.arrayBuffer()))}}')
            assert value=={'name':'probe.docx','type':'application/octet-stream','bytes':list(raw)}
            observe('web-management-browser-file-control',{'browser_version':browser.version,'selected_file':value,'actual_chooser_event':True})
        finally:browser.close()


@BROWSER
@pytest.mark.parametrize('owner',['local','hub'])
def test_ready_native_documents_update_and_remove_through_actual_web(tmp_path,owner):
    # TC-008-web-ready-management: existing-data management, never initial upload acceptance.
    from playwright.sync_api import expect
    server=Server(tmp_path/owner,owner);evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',tmp_path/'evidence'));evidence.mkdir(parents=True,exist_ok=True)
    try:
        items=prepare(server);expected_ids={i['id'] for i in items};assert len(expected_ids)==6
        for item in items:
            item['v1_reference']=verify(server,item)['reference']
            item['preserved']={k:item['entry'][k] for k in ('display_name','path','project_ids')}
            assert item['preserved']['display_name']==item['name'] and item['preserved']['project_ids']==[item['project']['id']]
        with Browser(server,evidence) as browser:
            for item in items:
                browser.project(item['project'],library=True);target=row(browser,item);expect(target).to_have_count(1)
                entry=current(server,item);assert entry['version']==entry['processing_version']==1
                control=target.get_by_label('更新文档 '+item['name'],exact=True);expect(control).to_be_visible()
                raw,truth=item['materials'][2]
                selected_name='replacement-'+item['label']+'.'+item['format']
                with browser.page.expect_response(lambda r:(r.request.method=='PUT' and r.url==browser.base+server.prefix+'/documents/library/'+item['id']) or (r.request.method=='POST' and r.url.startswith(browser.base+server.prefix+'/documents/uploads/') and r.url.endswith('/commit'))) as committed:
                    with browser.page.expect_file_chooser() as chosen:control.click()
                    chosen.value.set_files({'name':selected_name,'mimeType':'application/octet-stream','buffer':raw})
                response=committed.value;browser.page.wait_for_timeout(50)
                observe('web-management-actual-update-result',{'owner':owner,'id':item['id'],'method':response.request.method,'path':response.url[len(browser.base):],'status':response.status,'response':response.json(),'selected_name':selected_name})
                assert response.status==200,response.text()
                assert response.request.method=='POST' and response.url.endswith('/commit')
                receipt=response.json();assert receipt['document_id']==item['id'] and receipt['capture_id']!=entry['latest_attempt']['capture_id'] and receipt['attempt_id']!=entry['latest_attempt']['attempt_id']
                begin=next(e for e in reversed(browser.events) if e['method']=='POST' and e['path']==server.prefix+'/documents/uploads' and e['request'].get('document_id')==item['id'])
                assert_compare(begin['request'],server,item,entry,update=True)
                assert begin['request']['sha256']==hashlib.sha256(raw).hexdigest() and begin['request']['bytes']==len(raw) and begin['request']['name']==selected_name
                assert not any(e['method']=='PUT' and e['path']==server.prefix+'/documents/library/'+item['id'] for e in browser.events)
                item['entry']=wait_ready(server,item,2,browser.page);item['version']=2
                assert {k:item['entry'][k] for k in item['preserved']}==item['preserved']
                reject_reference(server,item,item['v1_reference'],'after-successful-update')
                target=row(browser,item)
                header=target.locator(':scope > p').first;expect(header).to_be_visible();expect(header).to_contain_text(item['name'])
                status=target.locator(':scope > p').filter(has_text='格式 '+item['format'].upper());expect(status).to_have_count(1);expect(status).to_be_visible()
                expect(status).to_contain_text(re.compile(r'(?<!处理)版本\s*2(?!\d)'));expect(status).to_contain_text(re.compile(r'处理版本\s*2(?!\d)'));expect(status).to_contain_text(re.compile(r'\bready\b'))
                browser.screenshot(item['label']+'-updated-ready')
                for other in items:verify(server,other)
                assert {e['id'] for e in server.call('GET','/documents/library').json()}==expected_ids
                found=browser.search(item['project'],truth['words'][0].split()[0]);assert [h['id'] for h in found['results']]==[item['id']];assert_metadata(found['results'][0],server,item)
                value=browser.read();assert_metadata(value,server,item)
                text=browser.page.locator('#doc-reader-text' if owner=='local' else '#hub-read-text');assert text.text_content()==value['text'] and truth['words'][0].split()[0] in text.text_content()
                info=browser.info();assert_metadata(info,server,item);assert info['available'] is True and info['bytes']==len(raw)
                reference=browser.download(browser.page.locator('#'+browser.prefix+'-original-download'),{'id':item['id'],'raw':raw,'sha256':hashlib.sha256(raw).hexdigest(),'format':item['format']})
                item['reference']=reference;browser.screenshot(item['label']+'-updated-original')
            assert len(browser.downloads)==6
            for item in items:
                browser.project(item['project'],library=True);target=row(browser,item);expect(target).to_have_count(1)
                entry=current(server,item);assert entry['version']==entry['processing_version']==2
                browser.page.once('dialog',lambda dialog:dialog.accept())
                with browser.page.expect_response(lambda r:r.request.method=='DELETE' and r.url==browser.base+server.prefix+'/documents/library/'+item['id']) as removed:target.get_by_role('button',name=re.compile(r'^移除文档(?:\s|$)')).click()
                response=removed.value;assert response.status==200,response.text()
                assert_compare(response.request.post_data_json,server,item,entry)
                expect(row(browser,item)).to_have_count(0);expected_ids.remove(item['id'])
                assert {e['id'] for e in server.call('GET','/documents/library').json()}==expected_ids
                reject_reference(server,item,item['reference'],'after-remove')
                anchor=item['materials'][2][1]['words'][0].split()[0]
                assert server.call('POST','/documents/search',{**server.context,'query':anchor,'scope':'project','project_id':item['project']['id'],**({'local':True} if owner=='local' else {})}).json()['results']==[]
                for other in items:
                    if other['id'] in expected_ids:verify(server,other)
                browser.screenshot(item['label']+'-removed')
            assert not expected_ids
            observe('web-ready-management-complete',{'owner':owner,'document_ids':[i['id'] for i in items],'updated':6,'removed':6,'actual_browser_downloads':len(browser.downloads)})
    finally:
        stopped=server.stop()
        if stopped is not None:assert stopped['forced'] is False

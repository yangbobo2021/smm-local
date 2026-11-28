"""Actual creator browser selection/drop; search/read UI are separate cases."""
import base64,hashlib,json,os,re,time
from pathlib import Path
from urllib.parse import urlsplit
import pytest,sqlite3
from document_formats_upload_fixture import upload_input
from document_helpers import observe
from test_document_formats_management import native_input
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server

pytestmark=pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'),reason='requires explicitly prepared Chromium; skipped is not browser/platform acceptance')


def assert_metadata(value,item,origin,status=True):
    assert value['id']==item['entry']['id'] and value['origin']==origin
    assert value['version']==value['processing_version']==1 and value['format']==item['format'] and value['sha256']==item['sha256']
    if status:assert value['processing_status']=='ready'


def verify_original(server,item,project):
    body={**server.context,'scope':'project','project_id':project['id'],'query':item['truth']['words'][0].split()[0],'limit':50,**({'local':True} if server.owner=='local' else {})}
    hits=server.call('POST','/documents/search',body).json()['results']
    assert [h['id'] for h in hits]==[item['entry']['id']]
    own=hits
    with sqlite3.connect(server.db) as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    origin={'device_id':archive if server.owner=='local' else server.context['hub_id'],'archive_id':archive,'document_id':item['entry']['id']}
    assert_metadata(own[0],item,origin)
    assert server.call('POST','/documents/search',{**body,'project_id':item['other']['id']}).json()['results']==[]
    hit=own[0];assert hit['format']==item['format'] and hit['version']==hit['processing_version']==1 and hit['sha256']==item['sha256']
    value=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'start':0,'end':hit['text_length']}).json()
    assert_metadata(value,item,origin)
    assert all(w in value['text'] for w in item['truth']['words']) and all(w not in value['text'] for w in item['truth']['excluded'])
    assert len(value['tables'])==len(item['truth']['tables'])
    used=set()
    for expected in item['truth']['tables']:
        matched=[]
        for t in value['tables']:
            if not all(t['location'].get(k)==v for k,v in expected['location'].items()):continue
            view=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'view':'table','table_id':t['table_id'],'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1}).json()
            assert_metadata(view,item,origin)
            assert view['table_id']==t['table_id'] and view['location']==t['location']
            if not any(c['text']==expected['cells'][0][2] for c in view['cells']):continue
            assert (view['rows'],view['columns'])==(expected['rows'],expected['columns'])
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
            assert len(cells)==len(expected['cells']) and set(cells)==set(expected['cells']);matched.append(t['table_id'])
        assert len(matched)==1 and matched[0] not in used;used.add(matched[0])
    info=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'view':'original-info'}).json()
    assert_metadata(info,item,origin,False);assert info['available'] is True and info['bytes']==len(item['raw'])
    raw=server.call('POST','/documents/original',{**server.context,'reference':hit['reference']}).content
    assert raw==item['raw'];keep('downloads/'+item['sha256']+'.'+item['format'],raw)


def upload_receipt(item,events,responses):
    starts=[e for e in events if e['method']=='POST' and e['path'].endswith('/documents/uploads') and (e.get('request_json') or {}).get('sha256')==item['sha256']]
    assert len(starts)==1
    uid=json.loads(responses[starts[0]['sha256']])['upload_id']
    commits=[e for e in events if e['method']=='POST' and e['path'].endswith('/documents/uploads/'+uid+'/commit')]
    assert len(commits)==1 and commits[0]['status']==200
    return json.loads(responses[commits[0]['sha256']])


def assert_upload_events(items,events,responses,project,context,owner):
    assert not any(e['method']=='POST' and e['path'].endswith('/documents/library') for e in events)
    for item in items:
        starts=[(n,e) for n,e in enumerate(events) if e['method']=='POST' and e['path'].endswith('/documents/uploads') and (e.get('request_json') or {}).get('sha256')==item['sha256']]
        assert len(starts)==1
        begin_index,event=starts[0];body=event['request_json'];assert event['status']==200
        key=project['stable_key'] if owner=='local' else project['source_key']
        assert body['project_id']==project['id'] and body['project_key']==key and body['name']==item['name'] and body['bytes']==len(item['raw'])
        assert body.get('submission_id') and 'document_id' not in body
        if owner=='hub':assert all(body[k]==v for k,v in context.items())
        receipt=json.loads(responses[event['sha256']]);size=receipt['block_bytes'];uid=receipt['upload_id']
        assert type(size) is int and 0<size<=1024*1024 and receipt['received_parts']==[]
        parts=[(n,e) for n,e in enumerate(events) if e['method']=='PUT' and '/documents/uploads/'+uid+'/parts/' in e['path']]
        chunks=[item['raw'][offset:offset+size] for offset in range(0,len(item['raw']),size)]
        assert len(parts)==len(chunks)
        for index,((n,part),chunk) in enumerate(zip(parts,chunks)):
            digest=hashlib.sha256(chunk).hexdigest()
            assert n>begin_index and part['path'].endswith('/parts/'+str(index)) and part['status']==200
            assert part['request_bytes']==len(chunk) and part['request_sha256']==part['chunk_sha256']==digest
        commits=[(n,e) for n,e in enumerate(events) if e['method']=='POST' and e['path'].endswith('/documents/uploads/'+uid+'/commit')]
        assert len(commits)==1 and commits[0][0]>parts[-1][0] and commits[0][1]['status']==200
        assert commits[0][1]['request_json']==context
        committed=json.loads(responses[commits[0][1]['sha256']]);assert committed['document_id']==item['entry']['id']
        assert committed['capture_id']==item['entry']['latest_attempt']['capture_id'] and committed['attempt_id']==item['entry']['latest_attempt']['attempt_id']


def assert_ui_snapshot(page,owner,entry,format):
    from playwright.sync_api import expect
    row=page.locator('#doc-library-list .result' if owner=='local' else '#hub-library-list .result').filter(has_text=entry['id'])
    deadline=time.monotonic()+20
    while True:
        expect(row).to_have_count(1)
        if row.locator('details').get_attribute('open') is None:row.locator('summary').click()
        # Polling can replace the row after the click. Take visibility, label
        # and all three JSON panels in one browser turn; reopen only if this
        # generation is closed/detached, never retry incorrect panel values.
        snapshot=row.evaluate('''row=>({connected:row.isConnected,open:row.querySelector('details')?.open,
            text:row.innerText,fields:Object.fromEntries([...row.querySelectorAll('[data-native-detail]')]
                .map(node=>[node.dataset.nativeDetail,node.textContent]))})''')
        if snapshot['connected'] and snapshot['open']:break
        assert time.monotonic()<deadline,snapshot
        page.wait_for_timeout(50)
    text=snapshot['text'];assert entry['display_name'] in text
    assert re.search(r'格式\s*'+format.upper()+r'(?![A-Z])',text)
    assert re.search(r'(?<!处理)版本\s*'+str(entry['version'])+r'(?!\d)',text)
    assert re.search(r'处理版本\s*'+str(entry['processing_version'])+r'(?!\d)',text)
    assert entry['latest_attempt']['status'] in text
    for field in ('published_snapshot','latest_attempt','retry_target'):
        expected=entry[field]
        if field=='latest_attempt':expected={k:expected[k] for k in ('capture_id','attempt_id','status','config_revision','error')}
        actual=json.loads(snapshot['fields'][field])
        assert actual==expected
    observe('web-visible-row-snapshot',{'owner':owner,'document_id':entry['id'],'snapshot':snapshot})
    return row


def test_web_row_observer_reopens_replaced_details_and_rejects_wrong_values():
    from copy import deepcopy
    from html import escape
    from playwright.sync_api import sync_playwright
    entry={'id':'observer-self-control','display_name':'same.docx','version':1,'processing_version':1,
        'published_snapshot':{'capture_id':'capture'},'latest_attempt':{'capture_id':'capture','attempt_id':'attempt','status':'ready','config_revision':1,'error':None},
        'retry_target':{'capture_id':'capture'}}
    def markup(value):
        fields=''.join('<pre data-native-detail="'+k+'">'+escape(json.dumps(value[k]))+'</pre>' for k in ('published_snapshot','latest_attempt','retry_target'))
        return '<div class="result"><p>same.docx · 文档 observer-self-control · 格式 DOCX · 版本 1 · 处理版本 1 · ready</p><details><summary>详情</summary>'+fields+'</details></div>'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            for owner,box in (('local','doc-library-list'),('hub','hub-library-list')):
                page.set_content('<div id="'+box+'">'+markup(entry)+'</div>')
                page.evaluate('''({box,html})=>{document.querySelector('#'+box+' summary').addEventListener('click',()=>{
                    document.getElementById(box).innerHTML=html;window.replaced=true;},{once:true})}''',{'box':box,'html':markup(entry)})
                assert_ui_snapshot(page,owner,entry,'docx');assert page.evaluate('window.replaced') is True
                for field in ('published_snapshot','latest_attempt','retry_target'):
                    wrong=deepcopy(entry);wrong[field]['capture_id']='foreign'
                    page.set_content('<div id="'+box+'">'+markup(wrong)+'</div>')
                    with pytest.raises(AssertionError):assert_ui_snapshot(page,owner,entry,'docx')
                observe('web-row-observer-controls',{'owner':owner,'actual_replacement_reopened':True,'wrong_capture_panels_rejected':3})
        finally:browser.close()


def assert_ui_ids(page,owner,expected,stage,*,timeout=20):
    """Read every rendered row, including duplicates and foreign-project rows."""
    expected=sorted(expected);assert len(expected)==len(set(expected))
    selector='#doc-library-list .result' if owner=='local' else '#hub-library-list .result'
    deadline=time.monotonic()+timeout
    while True:
        labels=page.locator(selector).evaluate_all('(rows)=>rows.map(row=>row.querySelector(":scope > p")?.textContent)')
        matches=[re.fullmatch(r'.* · 文档 (\S+) · 版本 \d+ / 来源 \d+',label or '') for label in labels]
        actual=sorted(match[1] for match in matches if match is not None)
        if len(actual)==len(labels) and actual==expected:break
        assert time.monotonic()<deadline,{'stage':stage,'expected':expected,'labels':labels,'actual':actual}
        page.wait_for_timeout(50)
    observe('web-library-ui-id-set',{'owner':owner,'stage':stage,'expected':expected,'actual':actual,'labels':labels})


def test_web_library_id_observer_rejects_incomplete_duplicate_and_foreign_rows():
    from playwright.sync_api import sync_playwright
    # Synthetic DOM only exercises the observer; product paths run below.
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            page=browser.new_page()
            for owner,box in (('local','doc-library-list'),('hub','hub-library-list')):
                def rows(ids):
                    page.set_content('<div id="'+box+'">'+''.join('<div class="result"><p>same.docx · 文档 '+id+' · 版本 1 / 来源 1</p></div>' for id in ids)+'</div>')
                rows(['beta','alpha']);assert_ui_ids(page,owner,['alpha','beta'],'positive',timeout=0)
                rejected=0
                for ids in (['alpha'],['beta'],['alpha','alpha'],['alpha','beta','foreign'],['alpha','foreign'],['alpha','beta','beta']):
                    rows(ids)
                    with pytest.raises(AssertionError):assert_ui_ids(page,owner,['alpha','beta'],'negative',timeout=0)
                    rejected+=1
                rows(['alpha'])
                with pytest.raises(AssertionError):assert_ui_ids(page,owner,[],'stale-project',timeout=0)
                page.set_content('<div id="'+box+'"><div class="result"><p>invalid</p></div></div>')
                with pytest.raises(AssertionError):assert_ui_ids(page,owner,[],'unparseable-row',timeout=0)
                rows([]);assert_ui_ids(page,owner,[],'empty-positive',timeout=0)
                observe('web-library-id-observer-controls',{'owner':owner,'positive':2,'rejected':rejected+2})
        finally:browser.close()


@pytest.mark.parametrize('owner',['local','hub'])
def test_web_creators_select_and_drop_each_native_format(tmp_path,owner,monkeypatch):
    # TC-008-web-native-upload: real app, ordinary chooser/global drag, two inputs per format.
    from playwright.sync_api import sync_playwright,expect
    server=Server(tmp_path/owner,owner);events=[];errors=[];all_items=[];context=None;browser=None;pw=None;responses={}
    gate=tmp_path/'processing-release';monkeypatch.setenv('SMM_008_WEB_PROCESSING_GATE',str(gate))
    evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',tmp_path/'evidence'));evidence.mkdir(parents=True,exist_ok=True)
    try:
        server.start();base='http://127.0.0.1:'+str(server.port)
        pw=sync_playwright().start()
        browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1280,'height':900})
        context.tracing.start(screenshots=True,snapshots=True,sources=True)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        def response_seen(response):
            request=response.request
            if not response.url.startswith(base):return
            raw=response.body();digest=hashlib.sha256(raw).hexdigest();responses[digest]=raw;name='browser-responses/'+digest+'.bin';keep(name,raw)
            payload=request.post_data_buffer
            events.append({'method':request.method,'path':request.url[len(base):],'status':response.status,'response_file':name,'sha256':digest,'bytes':len(raw),'request_bytes':len(payload) if payload else 0,'request_sha256':hashlib.sha256(payload).hexdigest() if payload else None,'authenticated':bool(request.headers.get('authorization')),'chunk_sha256':request.headers.get('x-chunk-sha256'),'request_json':json.loads(payload) if payload and request.headers.get('content-type','').startswith('application/json') else None})
        page.on('response',response_seen)
        page.goto(base,wait_until='networkidle')
        if owner=='hub':
            page.locator('#credential').set_input_files({'name':'synthetic-hub-token.txt','mimeType':'text/plain','buffer':server.token.encode()})
            expect(page.locator('#workspace')).to_be_visible()
        else:page.locator('nav [data-tab=documents]').click()
        prefix='doc' if owner=='local' else 'hub'
        page.locator('#'+prefix+'-project-name').fill('008 browser ordinary')
        with page.expect_response(lambda r:r.request.method=='POST' and r.url==base+server.prefix+'/projects') as created:page.locator('#'+prefix+'-project-create').click()
        ordinary=created.value.json()
        expect(page.locator('#notice')).to_contain_text('#'+str(ordinary['id']))
        page.wait_for_load_state('networkidle')
        if owner=='local':
            page.locator('nav [data-tab=projects]').click()
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/projects/global')) as global_created:page.locator('#ensure-global').click()
            global_project=global_created.value.json()
            expect(page.locator('#notice')).to_contain_text('全局项目已就绪')
            page.wait_for_load_state('networkidle');page.locator('nav [data-tab=documents]').click()
        else:
            with page.expect_response(lambda r:r.request.method=='POST' and r.url==base+'/v1/projects') as global_created:page.locator('#hub-global').click()
            global_project=global_created.value.json()
            expect(page.locator('#hub-project')).to_have_value(str(global_project['id']))
            page.wait_for_load_state('networkidle')
        assert ordinary['id']!=global_project['id']
        kind='kind' if owner=='local' else 'project_kind'
        assert ordinary[kind]=='ordinary' and global_project[kind]=='global'
        for variant,project,other in (('chooser',ordinary,global_project),('drop',global_project,ordinary)):
            selector='#doc-library-project' if owner=='local' else '#hub-project'
            page.wait_for_load_state('networkidle')
            page.locator(selector).select_option(str(project['id']))
            expect(page.locator(selector)).to_have_value(str(project['id']))
            page.wait_for_load_state('networkidle')
            expect(page.locator(selector)).to_have_value(str(project['id']))
            project_items=[]
            assert_ui_ids(page,owner,[],variant+'-project-selected-empty')
            for wave in (1,2):
                gate.unlink(missing_ok=True);items=[];event_start=len(events)
                for format in ('docx','xlsx','pdf'):
                    key=owner+variant+str(wave)+format;raw,truth=(upload_input(format,key) if wave==1 and format=='docx' else native_input(format,key));digest=hashlib.sha256(raw).hexdigest();file=tmp_path/(key+'.'+format);file.write_bytes(raw)
                    keep('inputs/'+key+'.'+format,raw);keep('truth/'+key+'.json',json.dumps(truth,ensure_ascii=False).encode())
                    items.append({'format':format,'raw':raw,'truth':truth,'sha256':digest,'file':file,'name':'same.'+format,'project':project,'other':other})
                files=[{'name':i['name'],'mimeType':'application/octet-stream','buffer':i['raw']} for i in items]
                if variant=='chooser':
                    with page.expect_file_chooser() as chosen:page.locator('#'+prefix+'-upload-files').click()
                    chosen.value.set_files(files)
                else:
                    transfer=page.evaluate_handle('''files=>{const dt=new DataTransfer();for(const f of files){dt.items.add(new File([Uint8Array.from(atob(f.base64),c=>c.charCodeAt(0))],f.name,{type:'application/octet-stream'}));}return dt}''',[{'name':i['name'],'base64':base64.b64encode(i['raw']).decode()} for i in items])
                    page.locator('#doc-upload-drop' if owner=='local' else '#hub-drop').dispatch_event('drop',{'dataTransfer':transfer});transfer.dispose()
                expect(page.locator('#'+prefix+'-upload-results li')).to_have_count(3,timeout=45000)
                deadline=time.monotonic()+45
                while True:
                    pending=server.call('GET','/documents/library?project_id='+str(project['id'])).json()
                    assert not any('失败' in s for s in page.locator('#'+prefix+'-upload-results li').all_text_contents()),events
                    if len(pending)==3*wave:break
                    assert time.monotonic()<deadline,pending;page.wait_for_timeout(100)
                for item in items:
                    receipt=upload_receipt(item,events[event_start:],responses)
                    entry=next(e for e in pending if e['id']==receipt['document_id']);item['entry']=entry
                    assert entry['latest_attempt']['capture_id']==receipt['capture_id'] and entry['latest_attempt']['attempt_id']==receipt['attempt_id']
                    assert entry['published_snapshot'] is None and entry['version']==entry['processing_version']==0 and entry['original_reference'] is None
                    assert entry['project_ids']==[project['id']] and entry['latest_attempt']['status'] in {'pending','processing'}
                    row=assert_ui_snapshot(page,owner,entry,item['format'])
                    assert not re.search(r'\bready\b|已可检索|可立即.*检索',row.inner_text()+' '+page.locator('#notice').inner_text()+' '+page.locator('#'+prefix+'-upload-results').inner_text())
                    assert server.call('POST','/documents/search',{**server.context,'query':item['truth']['words'][0].split()[0],'scope':'project','project_id':project['id'],**({'local':True} if owner=='local' else {})}).json()['results']==[]
                assert_ui_ids(page,owner,[i['entry']['id'] for i in project_items+items],variant+'-'+str(wave)+'-pending')
                for retained in project_items:
                    current=next(e for e in pending if e['id']==retained['entry']['id'])
                    assert current==retained['entry']
                    assert_ui_snapshot(page,owner,retained['entry'],retained['format'])
                    verify_original(server,retained,project)
                assert_upload_events(items,events[event_start:],responses,project,server.context,owner)
                page.screenshot(path=str(evidence/(owner+'-'+variant+'-'+str(wave)+'-pending.png')),full_page=True)
                gate.touch()
                deadline=time.monotonic()+45
                while True:
                    listing=server.call('GET','/documents/library?project_id='+str(project['id'])).json()
                    assert all((e.get('latest_attempt') or {}).get('status')!='failed' for e in listing),listing
                    if len(listing)==3*wave and all(
                        (e.get('latest_attempt') or {}).get('status')=='ready' and
                        e.get('published_snapshot') and not e['publication_pending'] and
                        e['published_snapshot']['capture_id']==e['latest_attempt']['capture_id']
                        for e in listing):break
                    assert not any('失败' in s for s in page.locator('#'+prefix+'-upload-results li').all_text_contents()),events
                    assert time.monotonic()<deadline,listing;page.wait_for_timeout(100)
                assert {e['sha256'] for e in listing}=={i['sha256'] for i in project_items+items}
                for item in items:
                    entry=next(e for e in listing if e['sha256']==item['sha256']);item['entry']=entry
                    assert entry['published_snapshot']['status']==entry['latest_attempt']['status']=='ready' and entry['version']==entry['processing_version']==1
                    assert entry['project_ids']==[project['id']];verify_original(server,item,project)
                    assert_ui_snapshot(page,owner,entry,item['format'])
                for retained in project_items:
                    assert_ui_snapshot(page,owner,retained['entry'],retained['format'])
                assert_ui_ids(page,owner,[i['entry']['id'] for i in project_items+items],variant+'-'+str(wave)+'-ready')
                page.screenshot(path=str(evidence/(owner+'-'+variant+'-'+str(wave)+'.png')),full_page=True);all_items.extend(items);project_items.extend(items)
                for old in all_items:
                    current=next(e for e in server.call('GET','/documents/library').json() if e['id']==old['entry']['id'])
                    assert current==old['entry'];verify_original(server,old,old['project'])
                until=time.monotonic()+20
                while True:
                    gates=[json.loads(line) for line in Path(str(gate)+'.events').read_text().splitlines()]
                    if sum(e['event']=='enter' for e in gates)==sum(e['event']=='exit' for e in gates):break
                    assert time.monotonic()<until,gates;page.wait_for_timeout(50)
                assert not errors,errors
        assert len({i['entry']['id'] for i in all_items})==12
        for project in (ordinary,global_project):
            page.locator(selector).select_option(str(project['id']))
            expect(page.locator(selector)).to_have_value(str(project['id']))
            page.wait_for_load_state('networkidle')
            assert_ui_ids(page,owner,[i['entry']['id'] for i in all_items if i['project']['id']==project['id']],'final-switch-'+str(project['id']))
        assert {e['id'] for e in server.call('GET','/documents/files').json()}=={i['entry']['id'] for i in all_items}
        for item in all_items:verify_original(server,item,item['project'])
        assert all(urlsplit(base+e['path']).hostname=='127.0.0.1' and 'token=' not in e['path'] for e in events)
        if owner=='hub':assert all(e['authenticated'] for e in events if e['path'].startswith('/v1/'))
        if owner=='local':
            status=server.call('GET','/documents/sync-status').json()
            assert {p['project_id'] for p in status['projects']}=={ordinary['id'],global_project['id']}
            assert all(not p['enabled'] for p in status['projects'])
        observe('web-native-upload-complete',{'owner':owner,'document_ids':[i['entry']['id'] for i in all_items],'browser_version':browser.version,'requests':events,'page_errors':errors})
        context.tracing.stop(path=str(evidence/(owner+'-trace.zip')));context.close();context=None;browser.close();browser=None
    finally:
        cleanup_errors=[]
        if context is not None:
            try:
                if context.pages:context.pages[-1].screenshot(path=str(evidence/(owner+'-failed.png')),full_page=True)
                context.tracing.stop(path=str(evidence/(owner+'-failed-trace.zip')))
            except Exception as exc:cleanup_errors.append(str(exc))
            try:context.close()
            except Exception as exc:cleanup_errors.append(str(exc))
        if browser is not None:
            try:browser.close()
            except Exception as exc:cleanup_errors.append(str(exc))
        if pw is not None:pw.stop()
        observe('web-native-browser-events',{'owner':owner,'requests':events,'page_errors':errors,'cleanup_errors':cleanup_errors})
        gate.touch();server.stop()
        assert not cleanup_errors,cleanup_errors

def test_web_observers_reject_changed_identity_and_chunks():
    from copy import deepcopy
    raw=b'a'*(1024*1024)+b'b'*9;digest=hashlib.sha256(raw).hexdigest();project={'id':1,'stable_key':'synthetic-key'}
    item={'raw':raw,'sha256':digest,'name':'same.docx','format':'docx','entry':{'id':'doc','latest_attempt':{'capture_id':'capture','attempt_id':'attempt'}}}
    responses={'begin':json.dumps({'upload_id':'upload','block_bytes':1024*1024,'received_parts':[]}).encode(),'commit':json.dumps({'document_id':'doc','capture_id':'capture','attempt_id':'attempt'}).encode()}
    events=[{'method':'POST','path':'/api/documents/uploads','status':200,'sha256':'begin','request_json':{'project_id':1,'project_key':'synthetic-key','name':'same.docx','bytes':len(raw),'sha256':digest,'submission_id':'submission'}}]
    for index,chunk in enumerate((raw[:1024*1024],raw[1024*1024:])):
        h=hashlib.sha256(chunk).hexdigest();events.append({'method':'PUT','path':'/api/documents/uploads/upload/parts/'+str(index),'status':200,'request_bytes':len(chunk),'request_sha256':h,'chunk_sha256':h})
    events.append({'method':'POST','path':'/api/documents/uploads/upload/commit','status':200,'sha256':'commit','request_json':{}})
    assert_upload_events([item],events,responses,project,{},'local')
    rejected=0
    for field,bad in [('project_id',2),('project_key','other'),('name','other.docx'),('bytes',1),('sha256','0'*64),('document_id','old')]:
        changed=deepcopy(events);changed[0]['request_json'][field]=bad
        with pytest.raises(AssertionError):assert_upload_events([item],changed,responses,project,{},'local')
        rejected+=1
    for field,bad in [('request_bytes',1),('request_sha256','0'*64),('chunk_sha256','0'*64),('path','/api/documents/uploads/upload/parts/9')]:
        changed=deepcopy(events);changed[2][field]=bad
        with pytest.raises(AssertionError):assert_upload_events([item],changed,responses,project,{},'local')
        rejected+=1
    for changed in (events[:-1],events[:2]+events[3:],events+[{'method':'POST','path':'/api/documents/library'}]):
        with pytest.raises(AssertionError):assert_upload_events([item],changed,responses,project,{},'local')
        rejected+=1
    origin={'device_id':'device','archive_id':'archive','document_id':'doc'}
    value={'id':'doc','origin':origin,'version':1,'processing_version':1,'format':'docx','sha256':digest,'processing_status':'ready'}
    assert_metadata(value,item,origin)
    for field,bad in [('id','other'),('origin',{**origin,'archive_id':'other'}),('version',2),('processing_version',2),('format','pdf'),('sha256','0'*64),('processing_status','failed')]:
        with pytest.raises(AssertionError):assert_metadata({**value,field:bad},item,origin)
        rejected+=1
    observe('web-observer-controls',{'valid_chunk_and_metadata_controls':True,'rejected_changes':rejected})


@pytest.mark.parametrize('owner',['local','hub'])
def test_web_processing_gate_has_real_pending_and_release(tmp_path,owner,monkeypatch):
    gate=tmp_path/'release';monkeypatch.setenv('SMM_008_WEB_PROCESSING_GATE',str(gate));server=Server(tmp_path/owner,owner)
    try:
        server.start()
        p=server.call('POST','/projects',{'name':'gate probe'} if owner=='local' else {**server.context,'name':'gate probe','kind':'ordinary'}).json()
        raw,truth=native_input('docx','gate'+owner);body={**server.context,'project_id':p['id'],'project_key':p['stable_key'] if owner=='local' else p['source_key'],'submission_id':'gate-probe','name':'probe.docx','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        begin=server.call('POST','/documents/uploads',body).json()
        for index,offset in enumerate(range(0,len(raw),begin['block_bytes'])):
            chunk=raw[offset:offset+begin['block_bytes']];server.call('PUT','/documents/uploads/'+begin['upload_id']+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
        receipt=server.call('POST','/documents/uploads/'+begin['upload_id']+'/commit',server.context).json()
        for _ in range(2):
            row=next(e for e in server.call('GET','/documents/library').json() if e['id']==receipt['document_id'])
            assert row['published_snapshot'] is None and row['latest_attempt']['status']=='pending' and row['version']==row['processing_version']==0
            time.sleep(.1)
        gate.touch();until=time.monotonic()+30
        while True:
            row=next(e for e in server.call('GET','/documents/library').json() if e['id']==receipt['document_id'])
            if row['latest_attempt']['status']=='ready':break
            assert time.monotonic()<until,row;time.sleep(.1)
        assert row['version']==row['processing_version']==1 and row['published_snapshot']['status']=='ready'
        other=server.call('POST','/projects/global').json() if owner=='local' else server.call('POST','/projects',{**server.context,'name':'other','kind':'global'}).json()
        item={'entry':row,'raw':raw,'truth':truth,'format':'docx','sha256':hashlib.sha256(raw).hexdigest(),'other':other}
        verify_original(server,item,p)
        observe('web-gate-real-control',{'owner':owner,'document_id':row['id'],'pending_held':True,'released_ready':True,'events':[json.loads(line) for line in Path(str(gate)+'.events').read_text().splitlines()]})
    finally:gate.touch();server.stop()

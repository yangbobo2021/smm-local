"""Actual Web text/table/original views; upload acceptance remains separate."""
import base64,hashlib,json,os,sqlite3,time,platform,sys,psutil,re
from pathlib import Path
import pytest
from document_helpers import observe
from document_formats_web_fixture import web_original,TRAP,source_key
from document_formats_managed_empty_fixture import blank_original
from document_formats_web_helpers import Browser
from test_document_formats_upload_restart import Server
from test_document_formats_retry import keep
from test_document_formats_table_context import assert_window,assert_location

BROWSER=pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'),reason='requires frozen actual Chromium; skipped is not platform evidence')


def critical_state(server):
    names=['documents','document_sources','document_source_projects','document_memberships','document_library','document_captures','document_capture_authorizations','document_processing_attempts','document_processing_config','document_snapshot_state','document_upload_jobs','document_fts','document_meta']
    with sqlite3.connect(server.db) as c:
        existing={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")};result={}
        for name in names:
            if name not in existing:continue
            rows=sorted([list(r) for r in c.execute('SELECT * FROM "'+name+'"')],key=lambda r:json.dumps(r,default=str))
            raw=json.dumps(rows,ensure_ascii=False,separators=(',',':'),default=str).encode();result[name]={'rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}
    return result


def origin(server,item):
    with sqlite3.connect(server.db) as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    return {'device_id':archive if server.owner=='local' else server.context['hub_id'],'archive_id':archive,'document_id':item['id']}


def metadata(value,server,item,*,status=True):
    assert value['id']==item['id'] and value['origin']==origin(server,item)
    assert value['version']==value['processing_version']==1 and value['format']==item['format'] and value['sha256']==item['sha256']
    if status:assert value['processing_status']==item['status']


def prepare(server,monkeypatch,*,empty=False):
    monkeypatch.delenv('SMM_008_WEB_READ_ONLY',raising=False);server.start();items=[];legacy=[]
    p=server.call('POST','/projects',{'name':'read ordinary'} if server.owner=='local' else {**server.context,'name':'read ordinary','kind':'ordinary'}).json()
    g=server.call('POST','/projects/global').json() if server.owner=='local' else server.call('POST','/projects',{**server.context,'name':'read global','kind':'global'}).json()
    other=server.call('POST','/projects',{'name':'unassociated'} if server.owner=='local' else {**server.context,'name':'unassociated','kind':'ordinary'}).json()
    for key,project in (('alpha',p),('beta',g)):
        for fmt in ('docx','xlsx','pdf'):
            label=server.owner+key+fmt;raw=blank_original(fmt,label) if empty else None
            if not empty:raw,truth=web_original(fmt,source_key(server.owner,key,fmt))
            else:truth={'text':'','query':label,'cells':[]}
            sha=hashlib.sha256(raw).hexdigest();name=label+'.'+fmt
            keep('inputs/'+name,raw);keep('truth/'+name+'.json',json.dumps(truth,ensure_ascii=False).encode())
            binding={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if server.owner=='local' else project['source_key'],'name':name,'submission_id':label,'bytes':len(raw),'sha256':sha}
            started=server.call('POST','/documents/uploads',binding).json()
            for index,offset in enumerate(range(0,len(raw),started['block_bytes'])):
                chunk=raw[offset:offset+started['block_bytes']];server.call('PUT','/documents/uploads/'+started['upload_id']+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
            receipt=server.call('POST','/documents/uploads/'+started['upload_id']+'/commit',server.context).json();until=time.monotonic()+35
            while True:
                entry=next(e for e in server.call('GET','/documents/library').json() if e['id']==receipt['document_id'])
                if entry['latest_attempt']['status'] in {'ready','partial','failed','empty-success'}:break
                assert time.monotonic()<until,entry;time.sleep(.05)
            status='empty-success' if empty else 'ready'
            assert entry['latest_attempt']['status']==entry['published_snapshot']['status']==status
            assert entry['version']==entry['processing_version']==1 and entry['sha256']==sha
            items.append({'id':entry['id'],'name':name,'raw':raw,'sha256':sha,'truth':truth,'format':fmt,'project':project,'other':other,'entry':entry,'status':status})
        if empty:
            text=server.owner+key+'legacy 原文 Ω😀\nline two';name=server.owner+key+'legacy.txt'
            body={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if server.owner=='local' else project['source_key'],'submission_id':name,'name':name,'content_base64':base64.b64encode(text.encode()).decode()}
            entry=server.call('POST','/documents/library',body).json();legacy.append({'id':entry['id'],'name':name,'text':text,'query':server.owner+key+'legacy','project':project})
    until=time.monotonic()+10
    while True:
        with sqlite3.connect(server.db) as c:pending=c.execute("SELECT count(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0]
        if not pending:break
        assert time.monotonic()<until;time.sleep(.05)
    entries=server.call('GET','/documents/library').json();assert {e['id'] for e in entries}=={i['id'] for i in items+legacy}
    paths=[Path(e['path']) for e in entries];assert all(p.resolve().is_relative_to(server.root.resolve()) for p in paths)
    stopped=server.stop();assert stopped['forced'] is False
    for path in paths:path.unlink()
    log=server.root/'readonly.jsonl';log.write_text('');monkeypatch.setenv('SMM_008_WEB_READ_ONLY',str(log));server.start(deny=paths)
    control=server.client.post('/__test_processing_probe');assert control.status_code==200 and control.json()=={'blocked':['processing','subprocess'],'pid':server.process.pid}
    events=[json.loads(l) for l in log.read_text().splitlines()];assert [e['event'] for e in events]==['processing','subprocess'] and all(e['pid']==server.process.pid for e in events)
    observe('web-readonly-known-control',{'owner':server.owner,'response':control.json(),'events':events});log.write_text('')
    actor=psutil.Process(server.process.pid)
    observe('web-read-runtime-identity',{'owner':server.owner,'os':platform.platform(),'python':sys.version,'server_pid':actor.pid,'created':actor.create_time(),'executable':actor.exe(),'argv':actor.cmdline(),'cwd':actor.cwd(),'username':actor.username(),'effective_uid':actor.uids().effective if hasattr(actor,'uids') else None,'controller_uid':os.getuid() if hasattr(os,'getuid') else None})
    return items,legacy,log


def assert_text(value,item):
    text=item['truth']['text'];assert value['text']==text[value['start']:value['end']]
    assert value['start_line']==text[:value['start']].count('\n')+1
    assert value['end_line']==text[:value['end']-1].count('\n')+1


def detail_json(browser,selector):
    from playwright.sync_api import expect
    details=browser.page.locator('#'+browser.prefix+'-extraction-details')
    if details.get_attribute('open') is None:details.locator('summary').click()
    node=browser.page.locator('#'+browser.prefix+'-'+selector);expect(node).to_be_visible()
    return json.loads(node.inner_text())


def assert_visible_text(browser,value,item,*,target=False):
    from playwright.sync_api import expect
    meta=browser.page.locator('#doc-reader-meta' if browser.owner=='local' else '#hub-read-meta')
    for token in (item['id'],item['sha256'],*origin(browser.server,item).values()):expect(meta).to_contain_text(token)
    expect(meta).to_contain_text(re.compile(r'(?<!处理)版本\s*1(?!\d)'))
    expect(meta).to_contain_text(re.compile(r'处理版本\s*1(?!\d)'))
    for token in ('格式 '+item['format'].upper(),item['status'],'提取文本'):expect(meta).to_contain_text(token)
    assert '.documents' not in meta.inner_text()
    coverage=detail_json(browser,'read-coverage');assert coverage==value['coverage']
    assert coverage['errors']==[] and coverage['units'] and all(u['method']=='native' and u['status']=='ready' for u in coverage['units'])
    if item['format']=='docx':assert coverage['parts']==['word/document.xml']
    elif item['format']=='xlsx':assert {u['sheet'] for u in coverage['units']}=={'Overview','Hidden Details'}
    else:assert {u['page'] for u in coverage['units']}=={1,2}
    expected=[l for l in value['locations'] if l['start']<value['end'] and l['end']>value['start']]
    visible=detail_json(browser,'read-locations');assert visible==expected and visible
    for loc in visible:
        assert 0<=loc['start']<loc['end']<=len(item['truth']['text'])
        if item['format']=='docx':assert loc['part']=='word/document.xml' and loc['path'].startswith('body/')
        elif item['format']=='xlsx':assert loc['part'] in {'xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml'} and re.fullmatch('[A-Z]+[1-9][0-9]*',loc['coordinate'])
        else:assert loc['page'] in (1,2) and loc['method']=='native' and len(loc['bbox'])==4 and all(0<=n<=1 for n in loc['bbox'])
    if target:
        truth=item['truth'];expected_cell=next(c for c in truth['cells'] if [c['row'],c['column']]==truth['target'])
        matches=[l for l in visible if item['truth']['text'][l['start']:l['end']]==expected_cell['text']]
        assert len(matches)==1
        if item['format']=='docx':assert_location(matches[0],{**truth['location'],'path':truth['location']['path']+'/row[243]/cell[11]/paragraph[1]'})
        elif item['format']=='xlsx':assert_location(matches[0],{**truth['location'],'coordinate':'K243'})
        else:assert_location(matches[0],{'page':2,'bbox':expected_cell['bbox'],'method':'native','page_width':truth['page_width'],'page_height':truth['page_height']})


def assert_table_dom(browser,view,truth):
    from playwright.sync_api import expect
    prefix=browser.prefix;body=browser.page.locator('#'+prefix+'-table-cells [data-row][data-column]')
    expect(body).to_have_count(len(view['cells']))
    for cell in view['cells']:
        node=browser.page.locator('#'+prefix+'-table-cells [data-row="'+str(cell['row'])+'"][data-column="'+str(cell['column'])+'"]')
        expect(node).to_have_count(1);expect(node.locator('[data-cell-text]')).to_be_visible();assert node.locator('[data-cell-text]').text_content()==cell['text']
        assert node.evaluate('(e)=>[e.rowSpan,e.colSpan]')==[cell['row_span'],cell['column_span']]
    headers=browser.page.locator('#'+prefix+'-table-header [data-row][data-column]');expect(headers).to_have_count(len(view['header_context']['cells']))
    for cell in view['header_context']['cells']:
        node=browser.page.locator('#'+prefix+'-table-header [data-row="'+str(cell['row'])+'"][data-column="'+str(cell['column'])+'"]')
        expect(node.locator('[data-cell-text]')).to_have_text(cell['text'])
    expect(browser.page.locator('#'+prefix+'-table-meta')).to_contain_text('显式表头' if view['header_context']['role']=='explicit_header' else '首内容行')
    expect(browser.page.locator('#'+prefix+'-table-meta')).to_contain_text('native')
    panel=browser.page.locator('#'+prefix+'-table-location');expect(panel).to_be_visible();assert json.loads(panel.inner_text())==view['location']
    for field,key,adjust in (('row-start','row_start',0),('row-end','row_end',-1),('column-start','column_start',0),('column-end','column_end',-1)):
        expect(browser.page.locator('#'+prefix+'-table-'+field)).to_have_value(str(view['window'][key]+adjust))
    target=next(c for c in view['cells'] if [c['row'],c['column']]==truth['target'])
    node=browser.page.locator('#'+prefix+'-table-cells [data-row="'+str(target['row'])+'"][data-column="'+str(target['column'])+'"]')
    node.locator('[data-cell-text]').click()
    detail=browser.page.locator('#'+prefix+'-cell-details');expect(detail).to_be_visible()
    shown=json.loads(detail.inner_text())
    fields=('row','column','row_span','column_span','type','location','sheet_state','row_hidden','column_hidden')
    assert shown=={k:target[k] for k in fields if k in target}
    if truth['format']=='xlsx':
        assert shown['sheet_state']=='hidden' and shown['row_hidden'] and shown['column_hidden']
        for label in ('隐藏工作表','隐藏行','隐藏列'):expect(browser.page.locator('#'+prefix+'-cell-label')).to_contain_text(label)
    assert browser.page.evaluate('window.__smmDocumentExecuted === true') is False


@BROWSER
@pytest.mark.parametrize('owner',['local','hub'])
def test_web_reads_text_deep_tables_and_exact_originals(tmp_path,owner,monkeypatch):
    # TC-008-reference-web; HTTP fixture setup is not Web-upload evidence.
    from playwright.sync_api import expect
    server=Server(tmp_path/owner,owner);evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',tmp_path/'evidence'));evidence.mkdir(parents=True,exist_ok=True)
    try:
        items,_,log=prepare(server,monkeypatch)
        with Browser(server,evidence) as browser:
            before=critical_state(server)
            for item in items:
                truth=item['truth'];result=browser.search(item['project'],truth['query'])
                assert [h['id'] for h in result['results']]==[item['id']];hit=result['results'][0];metadata(hit,server,item)
                assert hit['project_ids']==[item['project']['id']] and truth['query'] in hit['text']
                value=browser.read();metadata(value,server,item);assert_text(value,item)
                assert (value['start'],value['end'])==(hit['start'],hit['end'])
                text=browser.page.locator('#doc-reader-text' if owner=='local' else '#hub-read-text');expect(text).to_be_visible();assert text.text_content()==value['text']
                assert_visible_text(browser,value,item,target=True);browser.screenshot(item['name']+'-text')
                table_id=hit['table_context']['table_id'];expect(browser.page.locator('#'+browser.prefix+'-table-select')).to_have_value(table_id)
                table=browser.table(table_id);metadata(table,server,item);assert table['table_id']==table_id
                assert_window(table,truth,target=truth['target']);assert_table_dom(browser,table,truth)
                browser.screenshot(item['name']+'-table')
                r,c=truth['target'];last_column=min(truth['columns'],c+1)
                table=browser.table_range((r,r,c,last_column));metadata(table,server,item)
                bounds={'row_start':r,'row_end':r+1,'column_start':c,'column_end':last_column+1}
                assert_window(table,truth,window=bounds);assert table['window_origin']=='explicit';assert_table_dom(browser,table,truth)
                actual_request=next(e['request'] for e in reversed(browser.events) if e['path']==server.prefix+'/documents/read' and e['request'].get('view')=='table')
                assert all(actual_request[k]==v for k,v in bounds.items())
                expect(browser.page.locator('#notice.error')).to_have_count(0)
                stable=browser.page.locator('#'+browser.prefix+'-table-cells').text_content()
                browser.page.locator('#'+browser.prefix+'-table-row-end').fill(str(truth['rows']+1));browser.page.locator('#'+browser.prefix+'-table-read-range').click()
                expect(browser.page.locator('#notice.error')).to_be_visible()
                assert browser.page.locator('#'+browser.prefix+'-table-cells').text_content()==stable
                if item['format']=='docx':
                    # Legal bounds exercise each independent quota, never merely out-of-range.
                    union=[c for c in truth['cells'] if c['row']<=67]
                    assert len(union)==1005 and sum(len(c['text']) for c in union)<=16000
                    for kind,ident,bounds in (
                        ('cells',table_id,(1,67,1,15)),
                        ('characters',next(t['table_id'] for t in value['tables'] if t['location']==truth['quota_table']['location']),(1,1,1,2))):
                        if kind=='characters':assert len(truth['quota_table']['cells'])<1000 and sum(len(c['text']) for c in truth['quota_table']['cells'])>16000
                        browser.page.locator('#'+browser.prefix+'-table-select').select_option(ident)
                        for field,number in zip(('row-start','row-end','column-start','column-end'),bounds):browser.page.locator('#'+browser.prefix+'-table-'+field).fill(str(number))
                        with browser.page.expect_response(lambda r:r.url==browser.base+server.prefix+'/documents/read' and r.request.method=='POST') as failed:browser.page.locator('#'+browser.prefix+'-table-read-range').click()
                        response=failed.value;assert response.status_code==400
                        expect(browser.page.locator('#notice.error')).to_be_visible()
                        message=browser.page.locator('#notice').inner_text();assert '1000' in message and '16000' in message and '原件' in message
                        assert browser.page.locator('#'+browser.prefix+'-table-cells').text_content()==stable
                        observe('web-table-legal-quota-rejected',{'owner':owner,'id':item['id'],'kind':kind,'bounds_inclusive':bounds,'response':response.json(),'visible_message':message})
                    browser.page.locator('#'+browser.prefix+'-table-select').select_option(table_id)
                value=browser.text_range(0,min(900,len(truth['text'])));metadata(value,server,item);assert_text(value,item)
                assert value['start']==0 and value['end']==min(900,len(truth['text'])) and text.text_content()==value['text']
                assert_visible_text(browser,value,item)
                if item['format']=='docx':assert TRAP in text.text_content()
                browser.screenshot(item['name']+'-explicit-text')
                assert browser.page.evaluate('window.__smmDocumentExecuted === true') is False
                info=browser.info();metadata(info,server,item,status=False);assert info['available'] is True and info['bytes']==len(item['raw'])
                panel=browser.page.locator('#'+browser.prefix+'-original-info');expect(panel).to_contain_text(item['sha256']);expect(panel).to_contain_text(str(len(item['raw'])))
                reference=browser.download(browser.page.locator('#'+browser.prefix+'-original-download'),item)
                actual_info=server.call('POST','/documents/read',{**server.context,'reference':reference,'view':'original-info'}).json();metadata(actual_info,server,item,status=False)
                browser.screenshot(item['name']+'-original')
                negative=browser.search(item['other'],truth['query']);assert negative['results']==[]
                expect(browser.page.locator('#doc-results .result' if owner=='local' else '#hub-results .result')).to_have_count(0)
            assert len(browser.downloads)==6
            assert critical_state(server)==before
            assert log.read_text()=='' and server.events()==[]
            observe('web-read-all-materials-complete',{'owner':owner,'document_ids':[i['id'] for i in items],'critical_state_before':before,'critical_state_after':critical_state(server),'source_reads':server.events(),'processing_observer':log.read_text()})
    finally:
        stopped=server.stop()
        if stopped is not None:assert stopped['forced'] is False


def test_web_view_materials_have_independent_source_truth():
    from io import BytesIO
    from zipfile import ZipFile
    import xml.etree.ElementTree as E
    import pypdfium2
    hashes=set()
    for owner in ('local','hub'):
        for key in ('alpha','beta'):
            for format in ('docx','xlsx','pdf'):
                raw,t=web_original(format,source_key(owner,key,format));digest=hashlib.sha256(raw).hexdigest();assert digest not in hashes;hashes.add(digest)
                assert any((c['row'],c['column'])==tuple(t['target']) and c['text']==t['query'] for c in t['cells'])
                if format=='pdf':
                    pdf=pypdfium2.PdfDocument(raw)
                    try:
                        assert len(pdf)==2;texts=[]
                        for index in range(len(pdf)):
                            page=pdf[index];textpage=page.get_textpage()
                            try:texts.append(textpage.get_text_range())
                            finally:textpage.close();page.close()
                        assert t['query'] in ''.join(texts)
                    finally:pdf.close()
                else:
                    with ZipFile(BytesIO(raw)) as z:
                        assert z.testzip() is None
                        member='word/document.xml' if format=='docx' else 'xl/worksheets/sheet2.xml'
                        root=E.fromstring(z.read(member));texts=''.join(root.itertext());assert TRAP in texts and t['query'] in texts
                        if format=='docx':
                            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                            assert '\n'.join(n.text or '' for n in root.findall('.//w:t',ns))==t['text']
                            first=root.findall('./w:body/w:tbl',ns)[0].findall('.//w:t',ns)
                            assert [n.text for n in first]==[c['text'] for c in t['quota_table']['cells']]
                            assert len(first)==2 and sum(len(n.text) for n in first)>16000
                            union=[c for c in t['cells'] if c['row']<=67]
                            assert len(union)==1005 and sum(len(c['text']) for c in union)<=16000
                assert t['text'].count(t['query'])==1
    assert len(hashes)==12
    observe('web-source-truth-controls',{'originals':12,'all_distinct':True,'zip_xml_pdf_opened':True,'trap_is_literal_source_text':True})


@BROWSER
def test_browser_plaintext_probe_has_real_bad_and_good_controls():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            bad=browser.new_page();bad.set_content('<div>'+TRAP+'</div>');bad.wait_for_function('window.__smmDocumentExecuted === true')
            assert bad.evaluate('window.__smmDocumentExecuted === true') is True;bad.close()
            good=browser.new_page();good.set_content('<pre id="literal"></pre>');good.locator('#literal').evaluate('(node,text)=>node.textContent=text',TRAP)
            assert good.locator('#literal').text_content()==TRAP and good.locator('img').count()==0 and good.evaluate('window.__smmDocumentExecuted === true') is False
            good.close();observe('web-plaintext-known-controls',{'bad_markup_executed':True,'literal_text_did_not_execute':True,'browser_version':browser.version})
        finally:browser.close()


@BROWSER
@pytest.mark.parametrize('owner',['local','hub'])
def test_web_readonly_probe_blocks_real_processing_and_subprocess(tmp_path,owner,monkeypatch):
    log=tmp_path/'readonly.jsonl';log.write_text('');monkeypatch.setenv('SMM_008_WEB_READ_ONLY',str(log));server=Server(tmp_path/owner,owner)
    try:
        server.start();r=server.client.post('/__test_processing_probe')
        assert r.status_code==200 and r.json()=={'blocked':['processing','subprocess'],'pid':server.process.pid}
        events=[json.loads(l) for l in log.read_text().splitlines()];assert [e['event'] for e in events]==['processing','subprocess'] and all(e['pid']==server.process.pid for e in events)
        observe('web-server-readonly-known-control',{'owner':owner,'response':r.json(),'events':events})
    finally:server.stop()


@BROWSER
@pytest.mark.parametrize('owner',['local','hub'])
def test_web_blank_library_downloads_and_legacy_original_absence(tmp_path,owner,monkeypatch):
    # TC-008-web-empty-original; prepared before the browser opens.
    from playwright.sync_api import expect
    server=Server(tmp_path/owner,owner);evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',tmp_path/'evidence'));evidence.mkdir(parents=True,exist_ok=True)
    try:
        items,legacy,log=prepare(server,monkeypatch,empty=True)
        with Browser(server,evidence) as browser:
            before=critical_state(server)
            for project in (items[0]['project'],items[-1]['project']):
                browser.project(project,library=True)
                own=[i for i in items+legacy if i['project']['id']==project['id']]
                rows=browser.page.locator('#doc-library-list .result' if owner=='local' else '#hub-library-list .result');expect(rows).to_have_count(len(own))
                for item in own:expect(rows.filter(has_text='文档 '+item['id'])).to_have_count(1)
                for item in [i for i in items if i['project']['id']==project['id']]:
                    row=rows.filter(has_text='文档 '+item['id']);expect(row).to_contain_text('empty-success')
                    expect(row).to_contain_text(re.compile(r'(?<!处理)版本\s*1(?!\d)'));expect(row).to_contain_text(re.compile(r'处理版本\s*1(?!\d)'))
                    button=row.get_by_role('button',name='下载采集原件',exact=True);expect(button).to_have_count(1);expect(button).to_be_enabled()
                    reference=browser.download(button,item)
                    info=server.call('POST','/documents/read',{**server.context,'reference':reference,'view':'original-info'}).json()
                    metadata(info,server,item,status=False);assert info['available'] is True and info['bytes']==len(item['raw'])
                    row.screenshot(path=str(evidence/(owner+'-'+item['name']+'-library.png')))
                    result=browser.search(project,item['truth']['query']);assert result['results']==[]
                for item in [i for i in legacy if i['project']['id']==project['id']]:
                    row=rows.filter(has_text='文档 '+item['id']);expect(row).to_have_count(1)
                    control=row.get_by_role('button',name='下载采集原件',exact=True)
                    if control.count():expect(control).to_be_disabled()
                    row.screenshot(path=str(evidence/(owner+'-'+item['name']+'-legacy-library.png')))
                    found=browser.search(project,item['query']);assert [h['id'] for h in found['results']]==[item['id']]
                    value=browser.read();assert value['id']==item['id'] and value['version']==1 and value['text']==item['text']
                    rendered=browser.page.locator('#doc-reader-text' if owner=='local' else '#hub-read-text');assert rendered.text_content()==item['text']
                    downloads_before=len(browser.downloads)
                    count=len([e for e in browser.events if e['path']==server.prefix+'/documents/original'])
                    info=browser.info();assert info['id']==item['id'] and info['available'] is False and info['reason']=='legacy_original_not_captured'
                    panel=browser.page.locator('#'+browser.prefix+'-original-info');expect(panel).to_contain_text('未保存')
                    button=browser.page.locator('#'+browser.prefix+'-original-download')
                    if button.count():expect(button).to_be_disabled()
                    browser.page.wait_for_timeout(100)
                    assert len(browser.downloads)==downloads_before
                    assert len([e for e in browser.events if e['path']==server.prefix+'/documents/original'])==count
                    browser.screenshot(item['name']+'-legacy')
            assert critical_state(server)==before and log.read_text()=='' and server.events()==[]
            observe('web-empty-original-complete',{'owner':owner,'blank_ids':[i['id'] for i in items],'legacy_ids':[i['id'] for i in legacy],'critical_state_before':before,'critical_state_after':critical_state(server),'source_reads':server.events(),'processing_observer':log.read_text()})
    finally:
        stopped=server.stop()
        if stopped is not None:assert stopped['forced'] is False

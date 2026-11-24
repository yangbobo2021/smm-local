"""PR39 review regressions; browser+TestClient is not E1 network evidence."""
from contextlib import contextmanager
import json
import hashlib
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

import pytest
from test_hub_documents_contracts import w
from document_helpers import observe,deny_source_reads
from hub_document_helpers import assert_text
from smm_local import references


# @case-id: TC-007-cli-scan-boundary
def test_cli_scan_boundary(w,tmp_path,monkeypatch):
    hp=w.hub_project('CLI sources')
    paths=[];sources=[]
    def cli(*args):
        p=subprocess.run([sys.executable,'-m','smm_hub.cli','hub','--state-dir',str(w.pair.remote.db_path.parent),'documents',*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        observe('scan-cli',{'args':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        assert p.returncode==0,p.stderr
        return json.loads(p.stdout)
    for n in [1,2]:
        path=tmp_path/('external-'+str(n)+'.txt');path.write_text('scanboundarynonce independent '+str(n));paths.append(path)
        source=cli('add',path,'--project-id',hp['id']);assert source['status']=='pending';sources.append(source)
    before=w.snapshot();context=w.context()
    with monkeypatch.context() as guarded:
        attempts=deny_source_reads(guarded,*paths)
        for path in paths:
            reply=w.hub.post('/v1/documents/sources',json={**context,'path':str(path),'project_ids':[hp['id']]})
            observe('remote-add-denial',{'status':reply.status_code,'response':reply.json()})
            assert reply.status_code in {403,404,405},'remote callers cannot register an external Hub path'
            assert w.snapshot()==before
        for source in [*sources,None]:
            reply=w.hub.post('/v1/documents/refresh',json={**context,**({'source_id':source['id']} if source else {})})
            observe('remote-refresh-denial',{'status':reply.status_code,'response':reply.json()})
            assert reply.status_code in {403,404,405},'service cannot scan one or all external sources'
            assert w.snapshot()==before
        assert w.search_hub(query='scanboundarynonce')['results']==[]
    assert attempts==[]
    for source in sources:cli('refresh','--source-id',source['id'])
    result=w.search_hub(query='scanboundarynonce',limit=50)
    assert set(w.docs(result,True).values())=={'scanboundarynonce independent 1','scanboundarynonce independent 2'}


@contextmanager
def actual_browser(w,role):
    pw=pytest.importorskip('playwright.sync_api')
    primary=w.local.client if role=='local' else w.hub
    with pw.sync_playwright() as engine:
        chrome=os.environ.get('CHROME_BINARY','/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        browser=engine.chromium.launch(headless=True,**({'executable_path':chrome} if Path(chrome).is_file() else {}))
        context=browser.new_context(viewport={'width':1280,'height':1000});page=context.new_page();requests=[]
        evidence=os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
        if evidence:context.tracing.start(screenshots=True,snapshots=True,sources=True)
        def route_handler(route):
            request=route.request;url=urlsplit(request.url)
            client=w.hub if url.port==18770 else primary
            assert url.port in {18765,18770}
            requests.append({'url':request.url,'method':request.method,'authenticated':bool(request.headers.get('authorization'))})
            response=client.request(request.method,url.path+('?' +url.query if url.query else ''),headers=request.headers,content=request.post_data_buffer)
            observe('browser-request',{'role':role,'method':request.method,'path':url.path,'status':response.status_code,'response':response.text if 'json' in response.headers.get('content-type','') else '<actual HTML preserved in browser trace>'})
            route.fulfill(status=response.status_code,body=response.content,headers={'content-type':response.headers.get('content-type','application/json')})
        context.route('http://localhost:*/**',route_handler)
        try:yield page,requests
        finally:
            if evidence:
                page.screenshot(path=str(Path(evidence)/(role+'-web-review.png')),full_page=True)
                context.tracing.stop(path=str(Path(evidence)/(role+'-web-review-trace.zip')))
            context.close();browser.close()


# @case-id: TC-007-web-review-feedback
@pytest.mark.parametrize('role',['local','hub'])
def test_web_review_feedback(w,role):
    pw=pytest.importorskip('playwright.sync_api');expect=pw.expect
    local_project=w.project('Web feedback')
    with actual_browser(w,role) as (page,requests):
        page.goto('http://localhost:18765/')
        if role=='local':
            page.locator('nav button[data-tab=documents]').click();page.locator('#doc-library-project').select_option(str(local_project))
        else:
            page.locator('#credential').set_input_files(str(w.pair.token_file));expect(page.locator('#workspace')).to_be_visible();page.locator('#hub-project-name').fill('Web feedback');page.locator('#hub-project-create').click();expect(page.locator('#notice')).to_contain_text('已创建')
        prefix='doc' if role=='local' else 'hub'
        client=w.local.client if role=='local' else w.hub;endpoint='/api' if role=='local' else '/v1'
        with page.expect_response(lambda r:r.url.endswith('/documents/library') and r.request.method=='POST' and r.request.post_data_json.get('name')=='B.txt'):
            page.locator('#'+prefix+'-upload-files').set_input_files([{'name':'A.txt','mimeType':'text/plain','buffer':b'batchfeedbacknonce independent A'},{'name':'B.txt','mimeType':'text/plain','buffer':b'\xff'},{'name':'C.txt','mimeType':'text/plain','buffer':b'batchfeedbacknonce independent C'}])
        observe('mixed-batch-before-report',{'role':role,'library':client.get(endpoint+'/documents/library').json(),'notice':page.locator('#notice').inner_text()})
        report=page.locator('#'+prefix+'-upload-results')
        expect(report).to_be_visible(timeout=5000);expect(report).to_contain_text('A.txt',timeout=5000);expect(report).to_contain_text('B.txt');expect(report).to_contain_text('C.txt')
        library=client.get(endpoint+'/documents/library').json();names={d['display_name'] for d in library}
        assert names<={'A.txt','C.txt'} and 'A.txt' in names and len(names)==len(library)
        for name,status in [('A.txt','成功'),('B.txt','失败'),('C.txt','成功' if 'C.txt' in names else '未处理')]:
            row=report.locator('li').filter(has_text=re.compile('^'+re.escape(name)+'：'))
            expect(row).to_have_count(1);expect(row).to_be_visible();visible_text=row.inner_text();assert name+'：' in visible_text and status in visible_text
            if name=='B.txt':assert 'UTF-8' in visible_text
        visible=page.locator('#'+prefix+'-library-list .result');expect(visible).to_have_count(len(library))
        for asset in library:
            row=visible.filter(has_text=asset['id']);expect(row).to_have_count(1);expect(row).to_be_visible();visible_text=row.inner_text();assert asset['id'] in visible_text and asset['display_name'] in visible_text
        found=client.post(endpoint+'/documents/search',json={**(w.context() if role=='hub' else {}),'query':'batchfeedbacknonce','limit':50}).json()['results']
        assert {h['id'] for h in found}=={d['id'] for d in library} and len(found)==len(library)
        library_by_id={d['id']:d for d in library}
        for hit in found:
            expected_name=library_by_id[hit['id']]['display_name'];assert hit['display_name']==expected_name
            expected_text='batchfeedbacknonce independent '+('A' if expected_name=='A.txt' else 'C')
            expected_sha=hashlib.sha256(expected_text.encode()).hexdigest();assert hit['sha256']==expected_sha
            value=client.post(endpoint+'/documents/read',json={**(w.context() if role=='hub' else {}),'reference':hit['reference']}).json()
            assert value['id']==hit['id'] and value['text']==expected_text and value['sha256']==expected_sha
        last='C.txt' if 'C.txt' in names else 'B.txt'
        with page.expect_response(lambda r:r.url.endswith('/documents/library') and r.request.method=='POST' and r.request.post_data_json.get('name')==last):page.locator('#'+prefix+'-upload-files').dispatch_event('change')
        assert {d['id'] for d in client.get(endpoint+'/documents/library').json()}=={d['id'] for d in library}
        if role=='local':
            link=page.locator('#doc-hub-manage');expect(link).to_be_visible();expect(link).to_have_attribute('href',w.config['address']);expect(page.locator('#doc-hub-management')).to_be_visible();management=page.locator('#doc-hub-management').inner_text();assert re.search(r'(创建端|只在Hub).*管理',management,re.S) and re.search(r'(维护者|管理员).*凭据',management,re.S)
            assert not urlsplit(link.get_attribute('href')).query and not urlsplit(link.get_attribute('href')).username
            with page.expect_popup() as pending:link.click()
            popup=pending.value;popup.wait_for_load_state();assert popup.url.rstrip('/')==w.config['address']
            expect(popup.locator('#credential')).to_be_visible();expect(popup.locator('#workspace')).to_be_hidden()
            assert not any(r['authenticated'] for r in requests if r['url'].startswith(w.config['address']))
            if os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):popup.screenshot(path=str(Path(os.environ['ACCEPTANCE_EVIDENCE_DIR'])/'hub-management-empty-shell.png'),full_page=True)
            popup.close()
            path,source=w.source('origin.txt','provenancefeedbacknonce local shared',[local_project]);w.policy(local_project);w.sync()
            hp=w.hub_project('Native origin');w.upload(hp,'native.txt','provenancefeedbacknonce native original',hub=True)
            page.locator('#doc-archive-mode').select_option('combined');page.locator('#doc-limit').select_option('50');page.locator('#doc-query').fill('provenancefeedbacknonce');page.locator('#doc-search-form').evaluate('(f)=>f.requestSubmit()')
            expect(page.locator('#doc-results .result')).to_have_count(2)
            native=page.locator('#doc-results .result').filter(has=page.locator('h3').filter(has_text='native.txt'))
            expect(native).to_be_visible();native_text=native.inner_text();assert 'Hub自有' in native_text and w.context()['hub_id'] in native_text and references.material(w.pair.remote)[0] in native_text and '项目 #'+str(hp['id']) in native_text
            def read_visible(row,provider,text,device,archive):
                with page.expect_response(lambda r:r.url.endswith('/documents/read') and r.request.method=='POST') as response:row.get_by_role('button',name='读取原文',exact=True).click()
                value=response.value.json();assert value['archive_scope']==provider and value['text']==text
                expect(page.locator('#doc-reader-meta')).to_be_visible()
                prefix=r'^(实际读取端[：:]\s*)?'+(r'(Hub|汇总端)' if provider=='hub' else r'(本机|本地)')
                expect(page.locator('#doc-reader-meta')).to_have_text(re.compile(prefix))
                metadata=page.locator('#doc-reader-meta').inner_text();assert device in metadata and archive in metadata
                expect(page.locator('#doc-reader-text')).to_be_visible();expect(page.locator('#doc-reader-text')).to_have_text(text)
                return value
            read_visible(native,'hub','provenancefeedbacknonce native original',w.context()['hub_id'],references.material(w.pair.remote)[0])
            shared=page.locator('#doc-results .result').filter(has=page.locator('h3').filter(has_text='origin.txt'))
            expect(shared).to_be_visible();shared_text=shared.inner_text();assert w.device in shared_text and w.archive in shared_text and w.config['device_name'] in shared_text and '项目 #'+str(w.hub_project_for(local_project)['id']) in shared_text
            read_visible(shared,'local','provenancefeedbacknonce local shared',w.device,w.archive)
            if os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):page.screenshot(path=str(Path(os.environ['ACCEPTANCE_EVIDENCE_DIR'])/'local-original-provider.png'),full_page=True)
            w.local.remove(source)
            read_visible(shared,'hub','provenancefeedbacknonce local shared',w.device,w.archive)
            assert w.config['device_name'] in page.locator('#doc-reader-meta').inner_text()
        observe('web-feedback-complete',{'role':role,'batch_report':report.inner_text(),'library_ids':[d['id'] for d in library]})

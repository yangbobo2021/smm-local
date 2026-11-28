"""Actual browser must not finish while a new result is awaiting publication."""
import hashlib,json,os,re,sqlite3,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
import psutil,pytest
from document_helpers import ROOT,observe
from document_formats_platform import utf8_environment,spawn_identity,process_tree,terminate_verified,preserve_diagnostics
from document_formats_web_helpers import Browser
from document_formats_partial_fixture import partial_pdf
from test_document_formats_management import native_input
from test_document_formats_installed_minimum import assert_complete_source_text
from test_document_formats_retry import ENGINE,DATA,FONT,keep
from test_document_formats_upload_restart import Server


def save(name,value):keep(name,json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8'))


def assert_finished_notice(page, timeout=10000):
    from playwright.sync_api import expect
    notice = page.locator('#notice')
    expect(notice).not_to_contain_text(re.compile(r'正在.*处理|处理中|待发布|等待.*发布|处理完成后'), timeout=timeout)
    expect(notice).to_contain_text(re.compile(r'已|成功|完成|检索'), timeout=timeout)
    text = notice.inner_text()
    assert not re.search(r'正在.*处理|处理中|待发布|等待.*发布|处理完成后', text)
    assert re.search(r'已|成功|完成|检索', text)
    return text


def capture_target_row(target, path):
    from playwright.sync_api import Error
    deadline = time.monotonic() + 10
    rejected = 0
    geometry = """node=>{const b=node.getBoundingClientRect();return {
        connected:node.isConnected,text:node.innerText,x:b.x+scrollX,y:b.y+scrollY,
        width:b.width,height:b.height}}"""
    while True:
        assert time.monotonic() < deadline, 'target row never remained stable for a screenshot'
        handle = target.element_handle(timeout=max(1, int((deadline-time.monotonic())*1000)))
        assert handle is not None
        try:
            before = handle.evaluate(geometry)
            if not before['connected']:
                continue
            try:
                handle.screenshot(path=str(path), timeout=max(1, int((deadline-time.monotonic())*1000)))
            except Error:
                # Error wording varies when an element is replaced during font
                # or stability waits. Only this same handle's actual detachment
                # may retry. A genuinely hidden/invalid live node still fails.
                if handle.evaluate('node=>node.isConnected'):
                    raise
                continue
            after = handle.evaluate(geometry)
            stable = after['connected'] and all(abs(before[k]-after[k]) <= .5 for k in ('x','y','width','height'))
            if stable:
                return after
            rejected += 1
            rejected_path = path.with_name(path.stem + '.rejected-' + str(rejected) + path.suffix)
            path.replace(rejected_path)
            observe('publication-rejected-capture', {'before':before,'after':after,
                'path':rejected_path.name,'sha256':hashlib.sha256(rejected_path.read_bytes()).hexdigest(),
                'reason':'same captured handle detached or changed document geometry; original PNG retained'})
        finally:
            handle.dispose()


@pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'), reason='requires prepared browser for screenshot observer control')
def test_publication_row_capture_keeps_offscreen_target_pixels(tmp_path):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width': 800, 'height': 600})
            page.set_content('<div style="height:2400px">unrelated controls</div><div id="target" style="width:400px;height:120px;background:rgb(17,29,43);color:white">independent target</div>')
            path = tmp_path / 'actual-target.png'
            observed = capture_target_row(page.locator('#target'), path)
            assert observed['connected'] and observed['text'] == 'independent target'
            with Image.open(path) as image:
                assert image.size == (400, 120)
                assert image.convert('RGB').getpixel((200, 100)) == (17, 29, 43)
            keep('publication-screenshot-observer-target.png', path.read_bytes())
            observe('publication-row-capture-observer-control', {'purpose': 'synthetic DOM only; screenshot bytes from real offscreen target', 'geometry': observed})
        finally:
            browser.close()


@pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'), reason='requires prepared actual Chromium')
def test_publication_capture_rejects_replaced_handle_after_actual_screenshot(tmp_path, monkeypatch):
    from playwright.sync_api import ElementHandle, sync_playwright
    from PIL import Image
    actual = ElementHandle.screenshot
    replaced = []
    def screenshot(handle, **options):
        raw = actual(handle, **options)
        if not replaced:
            handle.evaluate("node=>{const next=node.cloneNode(true);next.style.background='rgb(17,29,43)';next.textContent='replacement target';node.replaceWith(next)}")
            replaced.append(True)
        return raw
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('<div id="target" style="width:400px;height:120px;background:rgb(71,17,29);color:white">old target</div>')
            monkeypatch.setattr(ElementHandle, 'screenshot', screenshot)
            path = tmp_path / 'target.png'
            observed = capture_target_row(page.locator('#target'), path)
            assert observed['connected'] and observed['text'] == 'replacement target'
            rejected = path.with_name('target.rejected-1.png')
            for saved, expected in ((rejected, (71,17,29)), (path, (17,29,43))):
                with Image.open(saved) as image:
                    assert image.size == (400,120) and image.convert('RGB').getpixel((200,100)) == expected
                keep('observer-' + saved.name, saved.read_bytes())
            observe('publication-same-handle-observer-control', {'actual_replacement_after_real_screenshot':True,
                'old_red_image_rejected_and_retained':True,'actual_new_blue_image_accepted':True})
        finally:
            browser.close()


@pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'), reason='requires prepared real browser for observer controls')
def test_publication_notice_observer_waits_for_async_finish_and_rejects_stuck_or_wrong_notice():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('<p id="notice">原件已接收，正在本端处理；处理完成后再按项目检索。</p>')
            page.evaluate("setTimeout(()=>document.querySelector('#notice').textContent='已保存，可在项目检索',300)")
            assert assert_finished_notice(page) == '已保存，可在项目检索'
            for wrong in ('原件已接收，正在本端处理；处理完成后再按项目检索。', '发生错误'):
                page.locator('#notice').evaluate('(node,value)=>node.textContent=value', wrong)
                with pytest.raises(AssertionError):
                    assert_finished_notice(page, timeout=150)
            observe('publication-notice-observer-controls', {'purpose': 'synthetic DOM observer only, separate from real product flows',
                    'async_final': True, 'stuck_processing_rejected': True, 'wrong_final_rejected': True})
        finally:
            browser.close()


class PublicationBrowser(Browser):
    def open(self):
        super().open();self.context.tracing.stop()
        self.context.tracing.start(screenshots=False,snapshots=True,sources=True)
        return self
    def record(self,response):
        super().record(response)
        self.events[-1]['at']=time.monotonic()
    def screenshot(self,name):
        self.page.screenshot(path=str(self.evidence/(self.owner+'-'+name+'.png')),full_page=False)


@pytest.mark.skipif(not all((ENGINE,DATA,FONT,os.environ.get('PLAYWRIGHT_BROWSERS_PATH'))),reason='requires explicitly prepared real creator assets/browser; not E/H evidence when skipped')
@pytest.mark.parametrize('owner',['local','hub'])
def test_browser_waits_for_actual_publication_of_each_new_attempt(tmp_path,owner,monkeypatch):
    # TC-008-publication-visible-state; no source-removal/cancellation claim.
    from playwright.sync_api import expect
    server=Server(tmp_path/owner,owner)
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    gate=server.root/'postprocess-gate';gate.mkdir();monkeypatch.setenv('SMM_008_PUBLICATION_GATE',str(gate))
    monkeypatch.delenv('SMM_008_WEB_PROCESSING_GATE',raising=False);monkeypatch.delenv('SMM_008_WEB_READ_ONLY',raising=False)
    (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\nfrom document_formats_publication_hook import install\ninstall()\n',encoding='utf-8')
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(server.hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_RESTART_AUDIT=str(server.root/'cli-audit.jsonl'))
    cli_prefix=[sys.executable,'-B','-m','smm_local.cli','--db',str(server.db),'documents'] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(server.root),'documents']
    children=[];items=[];seen=set();evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'evidence')));evidence.mkdir(exist_ok=True,parents=True)
    def cli(*args):
        r=subprocess.run(cli_prefix+list(map(str,args)),cwd=server.root,env=env,capture_output=True,timeout=35);tag=uuid4().hex;keep('cli/'+tag+'.stdout',r.stdout);keep('cli/'+tag+'.stderr',r.stderr);assert r.returncode==0,r.stderr
        return json.loads(r.stdout)
    def library():
        r=server.client.get(server.prefix+'/documents/library');assert r.status_code==200,r.text
        digest=hashlib.sha256(r.content).hexdigest();keep('library/'+digest+'.json',r.content);return r.json()
    def entry(item):return next(e for e in library() if e['id']==item['id'])
    def material(status,key):
        if status=='ready':return native_input('docx',key)
        raw,t=partial_pdf(key,FONT);return raw,{'words':[t['anchor']],'excluded':[],'tables':[],'partial_reason':t['known_failure']}
    def prepare_item(group,status,index):
        key=owner+'publication'+str(group)+status+str(index);format='docx' if status=='ready' else 'pdf';versions={}
        for v in (1,2):
            raw,truth=material(status,key+'v'+str(v));versions[v]=(raw,truth);keep('inputs/'+key+'v'+str(v)+'.'+format,raw);save('truth/'+key+'v'+str(v)+'.json',truth)
        return {'key':key,'name':key+'.'+format,'format':format,'status':status,'group':group,'project':projects[group],'materials':versions,'v':1,'p':1}
    def wait_gate(item,sha,attempt=None):
        until=time.monotonic()+20
        while time.monotonic()<until:
            for path in gate.glob('*.json'):
                value=json.loads(path.read_bytes())
                if value['attempt_id'] not in seen and value['raw_sha256']==sha and (attempt is None or value['attempt_id']==attempt):
                    seen.add(value['attempt_id']);save('gates/'+value['attempt_id']+'.json',value);return value
            time.sleep(.02)
        raise AssertionError('real processing did not reach postprocessing publication gate')
    def full(item,reference=None):
        e=entry(item);raw,truth=item['materials'][item['v']];ref=reference or e['original_reference'];body={**server.context,'reference':ref}
        value=server.call('POST','/documents/read',{**body,'start':0,'end':e['text_length']}).json()
        assert value['id']==item['id'] and value['sha256']==hashlib.sha256(raw).hexdigest() and value['version']==item['v'] and value['processing_version']==item['p'] and value['processing_status']==item['status']
        assert_complete_source_text(value['text'],truth);assert all(w not in value['text'] for w in truth['excluded'])
        if item['status']=='partial':assert any(v['page']==2 and truth['partial_reason']['reason_contains'] in v['reason'] for v in value['coverage']['errors'])
        tables=[];used=set();assert len(value['tables'])==len(truth['tables'])
        for t in value['tables']:
            view=server.call('POST','/documents/read',{**body,'view':'table','table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,'column_start':1,'column_end':t['columns']+1}).json();tables.append(view)
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
            matches=[i for i,expected in enumerate(truth['tables']) if (view['rows'],view['columns'])==(expected['rows'],expected['columns']) and len(cells)==len(expected['cells']) and set(cells)==set(expected['cells']) and all(view['location'].get(k)==v for k,v in expected['location'].items())]
            assert len(matches)==1 and matches[0] not in used;used.add(matches[0])
        assert used==set(range(len(truth['tables'])))
        actual=server.call('POST','/documents/original',body).content;assert actual==raw;keep('downloads/'+hashlib.sha256(raw).hexdigest(),actual)
        hits=server.call('POST','/documents/search',{**server.context,'query':truth['words'][0].split()[0],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results'];assert [h['id'] for h in hits]==[item['id']]
        return {'ref':ref,'text':value['text'],'tables':tables,'sha256':value['sha256']}
    def wait_published(item,marker,version,processing):
        until=time.monotonic()+25
        while time.monotonic()<until:
            e=entry(item);published=e['published_snapshot'];latest=e['latest_attempt']
            if published and latest['attempt_id']==marker['attempt_id'] and latest['status']==item['status'] and published['capture_id']==marker['capture_id'] and published['result_sha256']==marker['result_sha256'] and (e['version'],e['processing_version'])==(version,processing):return e
            time.sleep(.03)
        raise AssertionError({'phase':'expected actual publication','entry':e,'marker':marker})
    def row(browser,item):
        target=browser.page.locator('#'+browser.prefix+'-library-list .result').filter(has_text='文档 '+item['id']);expect(target).to_have_count(1);return target
    def future_reference(item,marker):
        from smm_local.archive_protocol import sign
        result=json.loads((server.root/'.document-snapshots/results'/marker['result_sha256']).read_bytes())
        assert result['raw_sha256']==marker['raw_sha256'] and result['profile']==marker['profile']
        with sqlite3.connect(server.db) as c:
            archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
            key=c.execute('SELECT signing_key FROM archive_reference_material WHERE singleton=1').fetchone()[0]
            members=c.execute('SELECT m.source_id,s.revision,m.qualification,m.status FROM document_memberships m JOIN documents d ON d.pk=m.document_pk JOIN document_sources s ON s.id=m.source_id WHERE d.id=? ORDER BY m.source_id',(item['id'],)).fetchall()
        stamps=[{'id':sid,'revision':revision,'qualification':qualification+int(status!='ready')} for sid,revision,qualification,status in members]
        assert stamps
        metadata={'version':1,'sha256':marker['raw_sha256'],'text_sha256':hashlib.sha256(result['text'].encode('utf-8')).hexdigest(),'text_length':len(result['text']),'processing_version':1,'result_sha256':marker['result_sha256']}
        payload={'format':1,'kind':'document','archive_id':archive,'document_id':item['id'],'version':1,'sources':stamps,'start':0,'end':min(2000,len(result['text'])),'processing_version':1,'result_sha256':marker['result_sha256'],'raw_sha256':marker['raw_sha256']}
        reference=sign(payload,key)
        if owner=='hub':reference=sign({'format':1,'kind':'hub_document','archive_id':archive,**server.context,'origin':{'device_id':server.context['hub_id'],'archive_id':archive,'document_id':item['id']},'reference':reference,**metadata},key)
        # Never serialize the task archive's signing key.
        save('future-probe/'+item['key']+'.json',{'payload':payload,'outer_metadata':metadata,'table_ids':[t['table_id'] for t in result['tables']]})
        return reference,result
    def capture(browser,item,name):
        # Resolve and scroll in one page task; never retain a replaceable row's
        # ElementHandle across font loading / screenshot stability checks.
        visible=browser.page.wait_for_function("""({prefix,id})=>{
            const rows=[...document.querySelectorAll('#'+prefix+'-library-list .result')].filter(node=>node.textContent.includes('文档 '+id));
            if(rows.length!==1)return false;
            rows[0].scrollIntoView({block:'center'});
            const box=rows[0].getBoundingClientRect();
            return {text:rows[0].innerText,top:box.top,bottom:box.bottom,height:innerHeight};
        }""",arg={'prefix':browser.prefix,'id':item['id']},timeout=10000)
        try:observed=visible.json_value()
        finally:visible.dispose()
        assert '文档 '+item['id'] in observed['text'] and observed['bottom']>0 and observed['top']<observed['height']
        path=evidence/(owner+'-'+item['key']+'-'+name+'.png')
        captured=capture_target_row(row(browser,item),path)
        assert captured['connected'] and '文档 '+item['id'] in captured['text']
        observe('publication-viewport-capture',{'owner':owner,'document_id':item['id'],'name':name,'visible_dom':observed,'captured_row':captured,'path':path.name,'method':'actual locator screenshot, no image alteration'})
    def pending(browser,item,marker,phase,event_start):
        e=entry(item);assert e['latest_attempt']['attempt_id']==marker['attempt_id'] and e['latest_attempt']['capture_id']==marker['capture_id']
        assert marker['result_status']==item['status'] and marker['profile']['config_revision']==marker['config_revision']
        with sqlite3.connect(server.db) as c:
            actual=c.execute('SELECT capture_id,state,result_sha256,config_revision FROM document_processing_attempts WHERE id=?',(marker['attempt_id'],)).fetchone()
        assert actual==(marker['capture_id'],item['status'],marker['result_sha256'],marker['config_revision'])
        if phase=='first':
            assert e['published_snapshot'] is None and e['version']==e['processing_version']==0 and not e['original_available']
            raw,truth=item['materials'][1]
            hits=server.call('POST','/documents/search',{**server.context,'query':truth['words'][0].split()[0],'scope':'project','project_id':item['project']['id'],**({'local':True} if owner=='local' else {})}).json()['results'];assert hits==[]
            reference,result=future_reference(item,marker);item['future_probe_reference']=reference
            requests=[('/documents/read',{'view':'text'}),('/documents/read',{'view':'original-info'}),('/documents/original',{})]+[('/documents/read',{'view':'table','table_id':t['table_id']}) for t in result['tables']]
            for path,fields in requests:
                response=server.client.post(server.prefix+path,json={**server.context,'reference':reference,**fields})
                observe('publication-unpublished-rejected',{'owner':owner,'id':item['id'],'path':path,'view':fields,'status':response.status_code,'response':response.json()})
                assert response.status_code==400,response.text
        else:assert e['published_snapshot']['result_sha256']!=marker['result_sha256'] and full(item,item['snapshot']['ref'])['sha256']==item['snapshot']['sha256']
        waiting=r'\bpending\b|\bprocessing\b|处理中|正在.*处理|等待.*发布|待发布|尚未.*发布|尚不可检索'
        # Two observations are a test sampling strategy, not a prescribed poll rate.
        for observation in range(2):
            browser.page.wait_for_timeout(300)
            if phase=='cache':
                browser.project(projects[1-item['group']],library=True);browser.project(item['project'],library=True)
            target=row(browser,item);label=target.locator(':scope > p').filter(has_text='格式 '+item['format'].upper());expect(label).to_have_count(1)
            shown=label.inner_text();row_text=target.inner_text();outcome=browser.page.locator('#'+browser.prefix+'-upload-results').inner_text();notice=browser.page.locator('#notice').inner_text()
            if observation==1:capture(browser,item,phase+'-pending')
            observe('publication-before-release',{'owner':owner,'phase':phase,'observation':observation,'marker':marker,'visible_label':shown,'row_text':row_text,'upload_outcome':outcome,'notice':notice,'entry':e})
            if phase!='cache':
                # A completed extraction may truthfully be ready, but this operation
                # cannot be called published/searchable success before publication.
                for surface,text in [('upload outcome',outcome),('notice',notice)]:
                    assert not re.search(r'：成功|：部分完成|：空内容成功|可立即.*检索|已可检索',text),{'surface':surface,'text':text}
                    assert re.search(waiting,text),{'surface':surface,'text':text}
            assert re.search(waiting,row_text),row_text
    try:
        server.start();configured=cli('processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng');assert configured['ocr']['ready'] is True
        projects=[server.call('POST','/projects',{'name':'publication ordinary'} if owner=='local' else {**server.context,'name':'publication ordinary','kind':'ordinary'}).json(),server.call('POST','/projects/global').json() if owner=='local' else server.call('POST','/projects',{**server.context,'name':'publication global','kind':'global'}).json()]
        items=[prepare_item(g,s,i) for g in (0,1) for s in ('ready','partial') for i in (1,2)]
        # A real unarmed input publishes without entering the gate.
        control_raw,control_truth=native_input('docx',owner+'publicationcontrol');project=projects[0];binding={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if owner=='local' else project['source_key'],'submission_id':uuid4().hex,'name':'control.docx','sha256':hashlib.sha256(control_raw).hexdigest(),'bytes':len(control_raw)}
        start=server.call('POST','/documents/uploads',binding).json();server.call('PUT','/documents/uploads/'+start['upload_id']+'/parts/0',raw=control_raw,headers={'X-Chunk-SHA256':binding['sha256']});receipt=server.call('POST','/documents/uploads/'+start['upload_id']+'/commit',server.context).json();until=time.monotonic()+20
        while True:
            e=next(v for v in library() if v['id']==receipt['document_id'])
            if e['published_snapshot'] is not None and e['version']==e['processing_version']==1:break
            assert time.monotonic()<until,e
            time.sleep(.02)
        assert not list(gate.glob('*.json'));observe('publication-unarmed-control',{'entry':e,'gate_entries':0})
        with PublicationBrowser(server,evidence) as browser:
            for phase in ('first','cache','replacement'):
                if phase=='cache':
                    status=cli('processing-status');configured=cli('processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','eng+chi_sim');assert configured['config']['revision']==2
                for item in items:
                    browser.project(item['project'],library=True);raw,truth=item['materials'][2 if phase=='replacement' else 1];sha=hashlib.sha256(raw).hexdigest();(gate/'armed').write_text(sha,encoding='utf-8');event_start=len(browser.events);child=None
                    if phase=='cache':
                        target=entry(item)['retry_target'];argv=cli_prefix+['reprocess','--document-id',item['id']]+[v for k in ('capture_id','expected_attempt_id','expected_version','expected_processing_version') for v in ('--'+k.replace('_','-'),str(target[k]))];out=server.root/(item['key']+'.stdout');err=server.root/(item['key']+'.stderr')
                        with out.open('wb') as stdout,err.open('wb') as stderr:child=subprocess.Popen(argv,cwd=server.root,env=env,stdout=stdout,stderr=stderr,start_new_session=os.name!='nt')
                        children.append((child,spawn_identity(psutil.Process(child.pid))))
                    else:
                        control=browser.page.locator('#'+browser.prefix+'-upload-files') if phase=='first' else row(browser,item).get_by_label('更新文档 '+item['name'],exact=True)
                        with browser.page.expect_response(lambda r:r.request.method=='POST' and r.url.startswith(browser.base+server.prefix+'/documents/uploads/') and r.url.endswith('/commit')) as committed:
                            with browser.page.expect_file_chooser() as chosen:control.click()
                            chosen.value.set_files({'name':item['name'],'mimeType':'application/octet-stream','buffer':raw})
                        assert committed.value.status==200;receipt=committed.value.json()
                        if phase=='first':item['id']=receipt['document_id']
                        else:assert receipt['document_id']==item['id'] and receipt['capture_id']!=item['capture_id']
                    marker=wait_gate(item,sha);assert marker['config_revision']==(1 if phase=='first' else 2)
                    if phase=='cache':assert marker['capture_id']==item['capture_id'] and marker['attempt_id']!=target['expected_attempt_id']
                    else:assert marker['capture_id']==receipt['capture_id'] and marker['attempt_id']==receipt['attempt_id'] and marker['pid']==server.serving_pid
                    pending(browser,item,marker,phase,event_start)
                    (gate/(marker['attempt_id']+'.release')).touch();(gate/'armed').unlink();version=2 if phase=='replacement' else 1;processing={'first':1,'cache':2,'replacement':3}[phase];published=wait_published(item,marker,version,processing)
                    if child is not None:
                        child.wait(timeout=30);keep('cli/'+item['key']+'.stdout',out.read_bytes());keep('cli/'+item['key']+'.stderr',err.read_bytes());assert child.returncode==0,err.read_text(encoding='utf-8')
                    if phase!='first':
                        stale=item['snapshot']['ref'];requests=[('/documents/read',{'view':'text'}),('/documents/read',{'view':'original-info'}),('/documents/original',{})]+[('/documents/read',{'view':'table','table_id':t['table_id']}) for t in item['snapshot']['tables']]
                        for path,fields in requests:assert server.client.post(server.prefix+path,json={**server.context,'reference':stale,**fields}).status_code==400

                    item.update(v=version,p=processing,capture_id=marker['capture_id']);item['snapshot']=full(item)
                    if phase=='first':
                        assert full(item,item['future_probe_reference'])['sha256']==item['snapshot']['sha256']
                        info=server.call('POST','/documents/read',{**server.context,'reference':item['future_probe_reference'],'view':'original-info'}).json();assert info['available'] is True and info['bytes']==len(raw)
                    browser.page.wait_for_timeout(500)
                    if phase=='cache':browser.project(projects[1-item['group']],library=True);browser.project(item['project'],library=True)
                    if phase!='cache':
                        outcome=browser.page.locator('#'+browser.prefix+'-upload-results li').filter(has_text=item['name']);expect(outcome).to_contain_text('：'+('成功' if item['status']=='ready' else '部分完成'))
                        notice=assert_finished_notice(browser.page)
                    label=row(browser,item).locator(':scope > p').filter(has_text='格式 '+item['format'].upper());expect(label).to_contain_text(item['status']);shown=label.inner_text();assert re.search(r'(?<!处理)版本\s*'+str(version)+r'(?!\d)',shown) and re.search(r'处理版本\s*'+str(processing)+r'(?!\d)',shown);capture(browser,item,phase+'-published')
                    observe('publication-after-release',{'owner':owner,'phase':phase,'marker':marker,'published':published,'label':label.inner_text(),'version':version,'processing_version':processing})
    finally:
        original=sys.exception();errors=[];(gate/'abort').touch()
        for child,stamp in children:
            try:
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:terminate_verified(process_tree(stamp),owner=child)
            except Exception as error:errors.append(str(error))
        try:server.stop()
        except Exception as error:errors.append(str(error))
        try:
            for p in gate.glob('*.json'):keep('gate-finally/'+owner+'/'+p.name,p.read_bytes())
            preserve_diagnostics(server.root,'publication-finally');save('cleanup/'+owner+'.json',{'errors':errors,'original_error':str(original) if original else None})
        except Exception as error:errors.append(str(error))
        if errors:
            if original is not None:original.add_note('cleanup errors: '+str(errors))
            else:raise AssertionError(errors)

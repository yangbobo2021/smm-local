"""Real browser observations; no application responses are mocked."""
import hashlib,json,os
from pathlib import Path
from urllib.parse import urlsplit
from document_helpers import observe
from test_document_formats_retry import keep


def json_body(request):
    try:return request.post_data_json or {}
    except Exception:return {}


class Browser:
    def __init__(self,server,evidence):
        self.server=server;self.owner=server.owner;self.evidence=evidence;self.events=[];self.responses={};self.downloads=[];self.errors=[];self.unexpected=[]
        self.base='http://127.0.0.1:'+str(server.port);self.prefix='doc' if self.owner=='local' else 'hub'
        self.pw=None;self.browser=None;self.context=None;self.page=None
    def open(self):
        from playwright.sync_api import sync_playwright,expect
        self.pw=sync_playwright().start();self.browser=self.pw.chromium.launch(headless=True)
        self.context=self.browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
        self.version=self.browser.version
        self.context.tracing.start(screenshots=True,snapshots=True,sources=True)
        self.context.route('**/*',self.guard)
        self.page=self.context.new_page();self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('response',self.record)
        self.page.on('download',lambda d:self.downloads.append({'url':d.url,'suggested_filename':d.suggested_filename}))
        self.page.goto(self.base,wait_until='networkidle')
        if self.owner=='hub':
            self.page.locator('#credential').set_input_files({'name':'synthetic-token.txt','mimeType':'text/plain','buffer':self.server.token.encode()})
            expect(self.page.locator('#workspace')).to_be_visible();self.page.wait_for_load_state('networkidle')
        else:self.page.locator('nav [data-tab=documents]').click()
        return self
    def __enter__(self):
        try:return self.open()
        except BaseException as exc:
            self.__exit__(type(exc),exc,exc.__traceback__);raise
    def guard(self,route):
        url=urlsplit(route.request.url);base=urlsplit(self.base)
        if url.scheme in {'blob','data'} or (url.scheme,url.netloc)==(base.scheme,base.netloc):route.continue_()
        else:self.unexpected.append(route.request.url);route.abort()
    def record(self,response):
        request=response.request
        if (urlsplit(response.url).scheme,urlsplit(response.url).netloc)!=(urlsplit(self.base).scheme,urlsplit(self.base).netloc):raise AssertionError('browser response outside isolated service: '+response.url)
        raw=response.body();digest=hashlib.sha256(raw).hexdigest();name='browser-responses/'+digest+'.bin';keep(name,raw);self.responses[digest]=raw
        self.events.append({'method':request.method,'path':response.url[len(self.base):],'status':response.status,'request':json_body(request),'authenticated':bool(request.headers.get('authorization')),'response_file':name,'sha256':digest,'bytes':len(raw)})
    def action(self,view,action,path='/documents/read'):
        url=self.base+self.server.prefix+path
        with self.page.expect_response(lambda r:r.url==url and r.request.method=='POST' and (view is None or json_body(r.request).get('view','text')==view)) as response:action()
        r=response.value;data=r.json();observe('web-actual-action',{'owner':self.owner,'view':view,'path':path,'status':r.status,'request':json_body(r.request),'response':data})
        assert r.status==200,data
        return data
    def project(self,project,library=False):
        from playwright.sync_api import expect
        selector=('#doc-library-project' if library else '#doc-search-project') if self.owner=='local' else '#hub-project'
        self.page.wait_for_load_state('networkidle');self.page.locator(selector).select_option(str(project['id']))
        expect(self.page.locator(selector)).to_have_value(str(project['id']));self.page.wait_for_load_state('networkidle')
        expect(self.page.locator(selector)).to_have_value(str(project['id']))
    def search(self,project,query):
        if self.owner=='local':
            self.page.locator('#doc-archive-mode').select_option('local');self.page.locator('#doc-scope').select_option('project')
        else:self.page.locator('#hub-scope').select_option('project')
        self.project(project);self.page.locator('#'+self.prefix+'-query').fill(query)
        button=self.page.locator('#doc-search-submit' if self.owner=='local' else '#hub-search-form button')
        return self.action(None,button.click,'/documents/search')
    def read(self):
        box=self.page.locator('#doc-results' if self.owner=='local' else '#hub-results')
        return self.action('text',box.get_by_role('button',name='读取原文',exact=True).click)
    def text_range(self,start,end):
        self.page.locator('#'+self.prefix+'-read-start').fill(str(start));self.page.locator('#'+self.prefix+'-read-end').fill(str(end))
        return self.action('text',self.page.locator('#'+self.prefix+'-read-range').click)
    def table(self,table_id):
        self.page.locator('#'+self.prefix+'-table-select').select_option(table_id)
        return self.action('table',self.page.locator('#'+self.prefix+'-table-default').click)
    def table_range(self,bounds):
        for field,value in zip(('row-start','row-end','column-start','column-end'),bounds):self.page.locator('#'+self.prefix+'-table-'+field).fill(str(value))
        return self.action('table',self.page.locator('#'+self.prefix+'-table-read-range').click)
    def info(self):return self.action('original-info',self.page.locator('#'+self.prefix+'-original-info-load').click)
    def screenshot(self,name):self.page.screenshot(path=str(self.evidence/(self.owner+'-'+name+'.png')),full_page=True)
    def download(self,button,item):
        # A download event can precede the response observer finishing its body.
        # Bind to this click's response rather than the last previous download.
        url=self.base+self.server.prefix+'/documents/original'
        with self.page.expect_response(lambda r:r.url==url and r.request.method=='POST') as response:
            with self.page.expect_download() as happened:button.click()
        original=response.value
        download=happened.value;assert download.failure() is None
        raw=Path(download.path()).read_bytes();assert raw==item['raw']
        assert hashlib.sha256(raw).hexdigest()==item['sha256'];keep('downloads/'+item['sha256']+'.'+item['format'],raw)
        assert download.suggested_filename and '/' not in download.suggested_filename and chr(92) not in download.suggested_filename
        response_raw=original.body()
        assert original.status==200 and response_raw==raw and hashlib.sha256(response_raw).hexdigest()==item['sha256']
        req={'status':original.status,'bytes':len(response_raw),'sha256':hashlib.sha256(response_raw).hexdigest(),'request':json_body(original.request)}
        observe('web-real-download',{'owner':self.owner,'document_id':item['id'],'sha256':item['sha256'],'bytes':len(raw),'suggested_filename':download.suggested_filename,'request_reference':req['request']['reference']})
        return req['request']['reference']
    def __exit__(self,kind,error,tb):
        cleanup=[]
        if self.context is not None:
            try:
                if error is not None:self.screenshot('failure')
                self.context.tracing.stop(path=str(self.evidence/(self.owner+'-trace.zip')))
            except Exception as exc:cleanup.append(str(exc))
            try:self.context.close()
            except Exception as exc:cleanup.append(str(exc))
        if self.browser is not None:
            try:self.browser.close()
            except Exception as exc:cleanup.append(str(exc))
        if self.pw is not None:
            try:self.pw.stop()
            except Exception as exc:cleanup.append(str(exc))
        observe('web-browser-final',{'owner':self.owner,'browser_version':getattr(self,'version',None),'browser_events':self.events,'downloads':self.downloads,'page_errors':self.errors,'cleanup_errors':cleanup,'unexpected_requests':self.unexpected})
        assert not cleanup,cleanup
        assert not self.unexpected,self.unexpected
        assert not self.errors,self.errors
        assert all('token=' not in e['path'] for e in self.events)
        if self.owner=='hub':assert all(e['authenticated'] for e in self.events if e['path'].startswith('/v1/'))

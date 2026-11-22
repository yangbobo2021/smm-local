"""Opt-in E1: fresh installed Local CLI, real Web and stdio MCP, ordinary user."""
import argparse
import asyncio
import base64
import ctypes
from concurrent.futures import ThreadPoolExecutor
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone

from local_documents_checks import hit, identity, normalized, paths, self_check, text_range, read_matches, sources, rejection, evidence_available


def now():return datetime.now(timezone.utc).isoformat()


class Probe:
    def __init__(self,config,out):
        assert not out.exists(),'use a new output directory'
        out.mkdir(parents=True);self.out=out;self.config=config;self.python=config['local_python'];self.db=out/'archive.sqlite3'
        if config.get('playwright_node'):os.environ['PLAYWRIGHT_NODEJS_PATH']=config['playwright_node']
        self.docs=out/'资料 空格';self.docs.mkdir();self.empty=out/'empty-agent';self.empty.mkdir()
        self.calls=[];self.process=None;self.service_log=None;self.services=[];self.web=[];self.collectors={}
        self.audit=out/'source-opens.jsonl';self.phase='initial';self.expected={};self.edits=[]
        self.started=now()
        source_dir=out/'runner-sources';source_dir.mkdir()
        versions={}
        for name in ['local_documents_platform.py','local_documents_checks.py','local_documents_mcp_worker.py','local_documents_windows.py']:
            raw=Path(__file__).with_name(name).read_bytes();(source_dir/name).write_bytes(raw);versions[name]=hashlib.sha256(raw).hexdigest()
        self.save('runner-bindings',versions)
        self.bootstrap="""import sys,os,json,runpy,time
roots=json.loads(os.environ['SMM_DOC_PROBE_ROOTS']); logfile=os.environ['SMM_DOC_PROBE_AUDIT'];phasefile=os.environ['SMM_DOC_PROBE_PHASE_FILE']
identity={'pid':os.getpid(),'platform':sys.platform,'python':sys.executable,'argv':sys.argv[1:],'time':time.time()}
if sys.platform=='win32':
 import ctypes
 sid=ctypes.c_ulong();assert ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(sid))
 identity.update(is_admin=bool(ctypes.windll.shell32.IsUserAnAdmin()),session_id=sid.value)
else:identity['uid']=os.getuid()
with open(os.environ['SMM_DOC_PROBE_IDENTITIES'],'a',encoding='utf-8') as f:f.write(json.dumps(identity)+'\\n')
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes)):
  p=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
  if any(p==r or p.startswith(r+os.sep) for r in roots):
   with open(phasefile,encoding='utf-8') as f:phase=f.read()
   with open(logfile,'a',encoding='utf-8') as f:f.write(json.dumps({'time':time.time(),'pid':os.getpid(),'phase':phase,'path':p,'mode':args[1],'flags':args[2]})+'\\n')
sys.addaudithook(audit)
module=sys.argv[1];sys.argv=sys.argv[1:];runpy.run_module(module,run_name='__main__')
"""

    def save(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

    @property
    def phase(self):return self._phase

    @phase.setter
    def phase(self,value):
        self._phase=value;(self.out/'phase.txt').write_text(value,encoding='utf-8')

    def env(self):
        return dict(os.environ,PYTHONUTF8='1',SMM_DOC_PROBE_ROOTS=json.dumps([os.path.normcase(str(self.docs.resolve())),os.path.normcase(str((self.out/'outside').absolute())),os.path.normcase(str(self.out/'other.txt'))]),SMM_DOC_PROBE_AUDIT=str(self.audit),SMM_DOC_PROBE_PHASE_FILE=str(self.out/'phase.txt'),SMM_DOC_PROBE_IDENTITIES=str(self.out/'product-processes.jsonl'))

    def argv(self,module,*args):return [self.python,'-I','-B','-X','utf8','-c',self.bootstrap,module,*map(str,args)]

    def run(self,args,code=0):
        start=now();p=subprocess.run(list(map(str,args)),capture_output=True,env=self.env(),timeout=120)
        stdout=p.stdout.decode('utf-8',errors='replace');stderr=p.stderr.decode('utf-8',errors='replace')
        self.calls.append({'argv':list(map(str,args)),'phase':self.phase,'started_at':start,'finished_at':now(),'exit_code':p.returncode,'stdout':stdout,'stderr':stderr,'stdout_bytes_base64':base64.b64encode(p.stdout).decode(),'stderr_bytes_base64':base64.b64encode(p.stderr).decode()})
        self.save('commands',self.calls);rejection(p.returncode,code)
        return stdout

    def cli(self,*args,code=0):
        text=self.run(self.argv('smm_local.cli','--db',self.db,*args),code)
        return json.loads(text) if code==0 else text

    def read_cli(self,item,*,start=None,end=None,collector=None):
        self.validate_hit(item)
        options=[]
        if start is not None:options+=['--start',start]
        if end is not None:options+=['--end',end]
        result=self.cli('documents','read','--reference',item['reference'],*options)
        path=Path(item['path']);read_matches(result,item,self.expected[path],path,start=start,end=end,collector=self.collectors[path] if collector is None else collector)
        return result

    def read_mcp(self,items):
        values=self.mcp_sync([('read_document',{'reference':item['reference']},False) for item in items])
        assert len(values)==len(items)
        for item,result in zip(items,values):
            self.validate_hit(item);path=Path(item['path']);read_matches(result,item,self.expected[path],path,collector=self.collectors[path])
        return values

    def validate_hit(self,item):
        path=Path(item['path']);hit(item,self.expected[path],path)
        expected_ids=[self.single['id']] if path==self.other else [self.source['id']]
        if path==self.guide and getattr(self,'web_source',None) and not getattr(self,'web_removed',False):expected_ids.append(self.web_source['id'])
        assert set(item['source_ids'])==set(expected_ids)
        assert item['project_ids']==[self.q['id'] if path==self.other else self.p['id']]
        assert item['captured_by_source_id']==self.collectors[path]

    def reject_refs(self,items):
        for item in items:self.cli('documents','read','--reference',item['reference'],code=2)
        if items:self.mcp_sync([('read_document',{'reference':item['reference']},True) for item in items])

    def known_sources(self,ready):
        def counts(files,links=0):
            return {'ready':len(files),'failed':0,'candidates':len(files),'billed_bytes':sum(len(self.expected[p]) for p in files),'ignored_entries':links,'ignored_links':links,'ignored_excluded':0,'ignored_format':0}
        doc_files=[p for p in self.expected if p.is_relative_to(self.docs)]
        assert len(doc_files)==ready
        expected={self.source['id']:{'path':str(self.docs),'kind':'directory','project_ids':[self.p['id']],'recursive':True,'exclude':['excluded/'],'revision':1,'status':'ready','counts':{'ready':ready,'failed':0}},
                  self.single['id']:{'path':str(self.other),'kind':'file','project_ids':[self.q['id']],'recursive':True,'exclude':[],'revision':1,'status':'ready','counts':{'ready':1,'failed':0}}}
        expected[self.source['id']]['counts']=counts(doc_files,1);expected[self.single['id']]['counts']=counts([self.other])
        if getattr(self,'web_source',None) and not getattr(self,'web_removed',False):
            expected[self.web_source['id']]={'path':str(self.guide),'kind':'file','project_ids':[self.p['id']],'recursive':True,'exclude':[],'revision':1,'status':'ready','counts':{'ready':1,'failed':0}}
            expected[self.web_source['id']]['counts']=counts([self.guide])
        return expected

    def all_files(self,wanted):
        result=self.cli('documents','search','needle','--limit','50');paths(result,wanted)
        for item in result['results']:hit(item,self.expected[Path(item['path'])],Path(item['path']));self.read_cli(item)
        return result['results']

    def read_web(self,page,index,item,*,start=None,end=None):
        self.validate_hit(item)
        with page.expect_response(lambda r:r.url.endswith('/api/documents/read') and r.request.method=='POST') as info:
            if start is None and end is None:page.locator(f'[data-doc-read="{index}"]').click()
            else:
                page.locator('#doc-read-start').fill(str(start));page.locator('#doc-read-end').fill(str(end));page.locator('#doc-read-range').click()
        response=info.value;rejection(response.status,200);value=response.json();path=Path(item['path'])
        read_matches(value,item,self.expected[path],path,start=start,end=end,collector=self.collectors[path])
        page.wait_for_function('(expected)=>document.querySelector("#doc-reader-text").textContent===expected',arg=value['text'])
        assert page.locator('#doc-reader-text').inner_text()==value['text']
        meta=page.locator('#doc-reader-meta').inner_text()
        assert str(path) in meta and value['sha256'] in meta and f'采集版本 {item["version"]}' in meta
        return value

    def put(self,path,raw):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);self.expected[path]=raw
        self.edits.append({'time':now(),'action':'fixture-write','path':str(path),'sha256':hashlib.sha256(raw).hexdigest()});self.save('fixture-edits',self.edits)

    def stamp(self,label):
        result={str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':p.stat().st_mtime_ns,'bytes':p.stat().st_size} for p in self.expected if p.exists()}
        self.save('source-'+label,result);return result

    def inspect_identity(self):
        actual={'platform':sys.platform,'system':platform.platform(),'user':getpass.getuser(),'pid':os.getpid(),'python':sys.executable,'time':now()}
        if sys.platform=='win32':
            sid=ctypes.c_ulong();assert ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(sid))
            actual.update(is_admin=bool(ctypes.windll.shell32.IsUserAnAdmin()),session_id=sid.value)
        else:actual['uid']=os.getuid()
        self.save('identity',actual);identity(actual,self.config['expected_platform'])
        wheel=Path(self.config['wheel'])
        with zipfile.ZipFile(wheel) as z:
            expected={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('smm_local/') and n.endswith(('.py','.html'))}
        code="import importlib.util,pathlib,json,hashlib,sys;root=pathlib.Path(importlib.util.find_spec('smm_local').origin).parent.parent;print(json.dumps({p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in json.loads(sys.argv[1])}))"
        installed=json.loads(self.run([self.python,'-I','-B','-c',code,json.dumps(list(expected))]));assert installed==expected
        self.save('installation',{'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'expected':expected,'installed':installed,'local_python':self.python})

    def setup(self):
        self.inspect_identity();self.save('checker-self-test',self_check())
        code="from smm_local.core import Archive;import sys;d=Archive(sys.argv[1]);d.set_settings(codex_root=sys.argv[2],claude_root=sys.argv[2],sync_paused=True)"
        self.run([self.python,'-I','-B','-c',code,str(self.db),str(self.empty)])
        self.p=self.cli('project','create','文档项目P');self.q=self.cli('project','create','文档项目Q')
        self.guide=self.docs/'指南.md';self.note=self.docs/'nested'/'notes.txt';self.control=self.docs/'control.txt';self.other=self.out/'other.txt'
        self.raw='needle 中文😀 e\u0301\r\n第二行 <script>window.__docExecution=1</script>\r\nlast\n'.encode()
        self.put(self.guide,self.raw);self.put(self.note,b'needle nested original\n');self.put(self.control,('İ'*3000+' needle continuous control\n').encode());self.put(self.other,b'needle unrelated Q\n')
        outside=self.out/'outside';self.put(outside/'escape.txt',b'escapeuniquemarker must never be read')
        self.link=self.docs/'linked-directory'
        if sys.platform=='win32':self.run(['cmd','/c','mklink','/J',str(self.link),str(outside)])
        else:self.link.symlink_to(outside,target_is_directory=True)
        self.phase='configure';before=self.stamp('configured-before')
        self.source=self.cli('documents','add',self.docs,'--project-id',self.p['id'],'--exclude','excluded/')
        self.single=self.cli('documents','add',self.other,'--project-id',self.q['id'])
        assert self.source['status']==self.single['status']=='pending'
        sources=self.cli('documents','sources');assert {s['id'] for s in sources}=={self.source['id'],self.single['id']}
        assert self.cli('documents','files')==[]
        self.cli('documents','add',self.link,code=2)
        pending=self.cli('documents','search','needle');assert pending['results']==[] and pending['coverage']['indexed_files']==0
        assert self.stamp('configured-after')==before
        self.phase='explicit-refresh';self.cli('documents','refresh')
        self.collectors={self.guide:self.source['id'],self.note:self.source['id'],self.control:self.source['id'],self.other:self.single['id']}
        self.phase='cli-search-read'
        result=self.cli('documents','search','needle','--scope','project','--project-id',self.p['id'],'--limit','50')
        paths(result,[self.guide,self.note,self.control]);assert self.cli('documents','search','escapeuniquemarker')['results']==[]
        for item in result['results']:
            path=Path(item['path']);hit(item,self.expected[path],path)
            self.read_cli(item)
        self.initial={Path(h['path']):h for h in result['results']}
        self.old_cli=next(h for h in result['results'] if h['path']==str(self.guide))
        hit(self.old_cli,self.raw,self.guide);self.read_cli(self.old_cli);self.read_cli(self.old_cli,start=7,end=14)
        zero=self.cli('documents','search','nonexistentuniqueterm');assert zero['results']==[] and zero['coverage']['indexed_files']==4
        assert self.stamp('initial-read-after')==before

    def start_service(self):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        self.url=f'http://127.0.0.1:{port}';self.phase='service-start-without-refresh'
        self.service_log=open(self.out/f'service-{len(self.services)+1}.log','w',encoding='utf-8')
        argv=self.argv('smm_local.cli','--db',self.db,'serve','--host','127.0.0.1','--port',port,'--skip-initial-sync')
        self.process=subprocess.Popen(argv,stdout=self.service_log,stderr=subprocess.STDOUT,env=self.env())
        self.services.append({'pid':self.process.pid,'argv':argv,'started_at':now(),'url':self.url});self.save('services',self.services)
        import urllib.request
        for i in range(180):
            assert self.process.poll() is None,'service exited before ready'
            try:
                with urllib.request.urlopen(self.url+'/api/documents/sources',timeout=1) as r:
                    if r.status==200:
                        identities=[json.loads(s) for s in (self.out/'product-processes.jsonl').read_text().splitlines()]
                        actual=next(v for v in reversed(identities) if '--port' in v['argv'] and str(port) in v['argv'])
                        self.services[-1]['actual_pid']=actual['pid'];self.save('services',self.services)
                        return
            except OSError:time.sleep(.2)
        raise AssertionError('service not ready')

    def stop_service(self):
        if self.process is None:return
        if sys.platform=='win32':
            # A venv python.exe may launch a second Python process. Terminate
            # the owned tree, then independently check the real PID and port.
            result=subprocess.run(['taskkill','/PID',str(self.process.pid),'/T','/F'],capture_output=True)
            self.services[-1]['taskkill']={'exit_code':result.returncode,'stdout':result.stdout.decode(errors='replace'),'stderr':result.stderr.decode(errors='replace')}
            assert result.returncode==0
        else:self.process.terminate()
        try:code=self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:self.process.kill();code=self.process.wait(timeout=20)
        actual_pid=self.services[-1]['actual_pid'];port=int(self.url.rsplit(':',1)[1])
        for _ in range(100):
            if sys.platform=='win32':
                from ctypes import wintypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.OpenProcess.restype=wintypes.HANDLE
                handle=kernel.OpenProcess(0x100000,False,actual_pid)
                if handle:
                    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
                    actual_alive=kernel.WaitForSingleObject(handle,0)==258
                    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(handle)
                else:
                    assert ctypes.get_last_error()==87
                    actual_alive=False
            else:
                try:os.kill(actual_pid,0);actual_alive=True
                except ProcessLookupError:actual_alive=False
            with socket.socket() as sock:
                sock.settimeout(.2);port_closed=sock.connect_ex(('127.0.0.1',port))!=0
            if not actual_alive and port_closed:break
            time.sleep(.1)
        self.services[-1].update(finished_at=now(),exit_code=code,alive=self.process.poll() is None,actual_alive=actual_alive,port_closed=port_closed,actual_exit_checked_at=now())
        self.save('services',self.services);self.service_log.close();self.process=None
        assert not actual_alive and port_closed,'actual service must stop before restart/cleanup'

    async def mcp(self,steps):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        number=len(list(self.out.glob('mcp-call-*.json')))+1
        child=self.argv('smm_local.mcp_server','--db',self.db)
        receipt=self.out/f'mcp-process-{number}.json'
        args=[self.python,'-I','-B','-X','utf8',str(Path(__file__).with_name('local_documents_mcp_worker.py')),str(receipt),json.dumps(child)]
        records=[];answers=[];started=now()
        err=open(self.out/f'mcp-{number}.stderr','w',encoding='utf-8')
        try:
            async with stdio_client(StdioServerParameters(command=args[0],args=args[1:],env=self.env()),errlog=err) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize();tools=await session.list_tools();records.append({'list_tools':tools.model_dump(mode='json')})
                    for name in ['list_document_sources','search_documents','read_document']:
                        assert next(t for t in tools.tools if t.name==name).annotations.readOnlyHint is True
                    for name,data,bad in steps:
                        result=await session.call_tool(name,data);records.append({'name':name,'input':data,'response':result.model_dump(mode='json'),'time':now()})
                        if bad:rejection(result.isError,True);answers.append(None)
                        else:
                            assert not result.isError
                            answer=json.loads(result.content[0].text);answers.append(answer)
        finally:
            err.close();self.save(f'mcp-call-{number}',{'started_at':started,'finished_at':now(),'transport':'actual stdio subprocess','argv':args,'records':records})
        assert receipt.exists(),'MCP process cleanup receipt missing'
        process=json.loads(receipt.read_text());assert process['alive'] is False and process['exit_code']==0,process
        return answers

    def mcp_sync(self,steps):
        # Playwright's synchronous API owns an asyncio loop in this thread.
        # The independent MCP client needs its own loop, never a nested run().
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run,self.mcp(steps)).result(timeout=120)

    def check_mcp(self):
        self.phase='mcp-search-read'
        values=self.mcp_sync([('list_document_sources',{},False),('search_documents',{'query':'needle','scope':'project','project_id':self.p['id'],'limit':50},False),('search_documents',{'query':'nonexistentuniqueterm'},False)])
        sources(values[0],self.known_sources(3))
        paths(values[1],[self.guide,self.note,self.control]);assert values[2]['results']==[] and values[2]['coverage']['indexed_files']==4
        self.old_mcp=next(h for h in values[1]['results'] if h['path']==str(self.guide));hit(self.old_mcp,self.raw,self.guide)
        for item in values[1]['results']:path=Path(item['path']);hit(item,self.expected[path],path)
        self.read_mcp(values[1]['results'])
        read=self.mcp_sync([('read_document',{'reference':self.old_mcp['reference'],'start':7,'end':14},False)])[0]
        read_matches(read,self.old_mcp,self.raw,self.guide,start=7,end=14)

    def web_response(self,r):
        if '/api/documents/' in r.url or r.url.endswith('/api/projects'):
            try:self.web.append({'url':r.url,'status':r.status,'method':r.request.method,'request':r.request.post_data,'json':r.json(),'time':now()});self.save('web-responses',self.web)
            except Exception:pass

    def inspect_web_state(self,label,*,partial=False,checkpoint=None):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':self.config['browser']} if self.config.get('browser') else {}))
            context=browser.new_context(viewport={'width':1280,'height':1000});context.tracing.start(screenshots=True,snapshots=True,sources=True);page=context.new_page();page.on('response',self.web_response)
            try:
                page.goto(self.url);page.locator('[data-tab=documents]').click();page.wait_for_selector(f'[data-doc-files="{self.source["id"]}"]')
                if partial:
                    assert 'partial' in page.locator('#doc-source-list').inner_text()
                    page.locator(f'[data-doc-files="{self.source["id"]}"]').click()
                    page.wait_for_function("document.querySelector('#doc-file-list').textContent.includes('UTF-8')")
                    assert 'failed' in page.locator('#doc-file-list').inner_text()
                else:
                    with page.expect_response(lambda r:r.url.endswith('/api/documents/search') and r.request.method=='POST') as info:
                        page.locator('#doc-query').fill('needle');page.locator('#doc-limit').select_option('50');page.locator('#doc-search-submit').click()
                    result=info.value.json();paths(result,checkpoint)
                    page.wait_for_selector('#doc-results [data-doc-read]')
                    for i,item in enumerate(result['results']):
                        expected=checkpoint[Path(item['path'])]
                        for key in ['id','version','sha256','text_length','captured_at','captured_by_source_id','source_ids']:assert item[key]==expected[key]
                        self.read_web(page,i,item)
                page.screenshot(path=str(self.out/(label+'.png')),full_page=True)
            finally:context.tracing.stop(path=str(self.out/(label+'-trace.zip')));context.close();browser.close()

    def browser_flow(self):
        from playwright.sync_api import sync_playwright
        self.start_service();self.phase='web-read-configure'
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':self.config['browser']} if self.config.get('browser') else {}))
            context=browser.new_context(viewport={'width':1280,'height':1000});context.tracing.start(screenshots=True,snapshots=True,sources=True)
            page=context.new_page()
            page.on('response',self.web_response)
            try:
                page.goto(self.url);page.locator('[data-tab=documents]').click()
                page.locator('#doc-project-name').fill('Web创建项目R');page.locator('#doc-project-create').click()
                page.wait_for_function("document.querySelector('#notice').textContent.includes('已创建')")
                created=[r['json'] for r in self.web if r['method']=='POST' and r['url'].endswith('/api/projects')][-1]
                assert created['name']=='Web创建项目R' and created['kind']=='ordinary' and created['stable_key'] and created['id'] not in [self.p['id'],self.q['id']]
                page.locator('#doc-path').fill(str(self.guide));page.locator('#doc-projects').select_option(str(self.p['id']))
                page.locator('#doc-save').click();page.wait_for_function("document.querySelector('#doc-source-list').textContent.includes('pending')")
                page.screenshot(path=str(self.out/'web-pending.png'),full_page=True)
                rows=[r for r in self.web if r['method']=='POST' and r['url'].endswith('/api/documents/sources')]
                self.web_source=rows[-1]['json'];assert self.web_source['project_ids']==[self.p['id']] and self.web_source['status']=='pending'
                self.phase='explicit-refresh-web';page.locator(f'[data-doc-refresh="{self.web_source["id"]}"]').click()
                page.wait_for_function("!document.querySelector('#doc-source-list').textContent.includes('pending')")
                self.collectors[self.guide]=self.web_source['id']
                self.phase='web-search-read';page.locator('#doc-query').fill('needle');page.locator('#doc-scope').select_option('project');page.locator('#doc-search-project').select_option(str(self.p['id']));page.locator('#doc-limit').select_option('50');page.locator('#doc-search-submit').click()
                page.wait_for_selector('#doc-results [data-doc-read]');page.locator('#doc-results [data-doc-read]').filter(has_text='读取原文')
                searches=[r['json'] for r in self.web if r['url'].endswith('/api/documents/search') and r['method']=='POST'];result=searches[-1];paths(result,[self.guide,self.note,self.control])
                self.old_web=next(h for h in result['results'] if h['path']==str(self.guide));index=result['results'].index(self.old_web)
                for i,item in enumerate(result['results']):
                    path=Path(item['path']);hit(item,self.expected[path],path)
                    self.read_web(page,i,item)
                self.read_web(page,index,self.old_web)
                assert page.locator('#doc-reader-text').inner_text()==normalized(self.raw);assert page.evaluate('window.__docExecution') is None
                page.screenshot(path=str(self.out/'web-original.png'),full_page=True)
                self.read_web(page,index,self.old_web,start=7,end=14)
                page.locator('#doc-query').fill('nonexistentuniqueterm');page.locator('#doc-search-submit').click()
                page.wait_for_function("document.querySelector('#doc-results').textContent.includes('没有匹配')")
                zero=[r['json'] for r in self.web if r['url'].endswith('/api/documents/search')][-1]
                assert zero['results']==[] and zero['coverage']['indexed_files']==3
                page.screenshot(path=str(self.out/'web-zero.png'),full_page=True)
                page.locator('#doc-query').fill('needle');page.locator('#doc-search-submit').click();page.wait_for_selector('#doc-results [data-doc-read]')
                self.check_mcp();before=self.stamp('before-edit');assert before==self.stamp('after-three-entrances')
                self.raw2='needle edited 中文😀 e\u0301\r\nnew captured text\n'.encode();self.put(self.guide,self.raw2)
                self.phase='explicit-refresh-edit';self.cli('documents','refresh','--source-id',self.source['id'])
                for path in [self.guide,self.note,self.control]:self.collectors[path]=self.source['id']
                fresh=self.cli('documents','search','needle','--scope','project','--project-id',self.p['id'],'--limit','50');paths(fresh,[self.guide,self.note,self.control])
                mcp_fresh=self.mcp_sync([('search_documents',{'query':'needle','scope':'project','project_id':self.p['id'],'limit':50},False)])[0];paths(mcp_fresh,[self.guide,self.note,self.control])
                for item in fresh['results']:self.read_cli(item)
                self.read_mcp(mcp_fresh['results'])
                self.phase='reject-old-references';self.cli('documents','read','--reference',self.old_cli['reference'],code=2)
                self.mcp_sync([('read_document',{'reference':self.old_mcp['reference']},True)])
                with page.expect_response(lambda r:r.url.endswith('/api/documents/read') and r.request.method=='POST') as old_response:
                    page.locator(f'[data-doc-read="{index}"]').click()
                rejection(old_response.value.status,400);page.wait_for_function("document.querySelector('#notice').classList.contains('error')")
                page.screenshot(path=str(self.out/'web-old-reference-rejected.png'),full_page=True)
                page.locator('#doc-search-submit').click();page.wait_for_function("document.querySelector('#notice').textContent.includes('文档') && !document.querySelector('#notice').classList.contains('error')")
                result=[r['json'] for r in self.web if r['url'].endswith('/api/documents/search')][-1];new=next(h for h in result['results'] if h['path']==str(self.guide));assert new['id']==self.old_cli['id'] and new['version']!=self.old_cli['version'];hit(new,self.raw2,self.guide)
                for i,item in enumerate(result['results']):self.read_web(page,i,item)
                self.read_web(page,result['results'].index(new),new)
                assert page.locator('#doc-reader-text').inner_text()==normalized(self.raw2)
                page.screenshot(path=str(self.out/'web-updated.png'),full_page=True)
                self.current=new
                # Exercise complete replacement through the actual Web form as well.
                page.locator(f'[data-doc-edit="{self.web_source["id"]}"]').click();page.locator('#doc-projects').select_option([str(self.p['id']),str(self.q['id'])]);page.locator('#doc-exclude').fill('private/**');page.locator('#doc-recursive').uncheck();page.locator('#doc-save').click()
                page.wait_for_function("document.querySelector('#doc-source-list').textContent.includes('pending')")
                changed=[r['json'] for r in self.web if r['method']=='PUT'][-1];assert set(changed['project_ids'])=={self.p['id'],self.q['id']} and changed['recursive'] is False and changed['exclude']==['private/**']
                self.phase='explicit-refresh-web-set';page.locator(f'[data-doc-refresh="{self.web_source["id"]}"]').click();page.wait_for_function("!document.querySelector('#doc-source-list').textContent.includes('pending')")
                self.collectors[self.guide]=self.web_source['id']
                page.once('dialog',lambda dialog:dialog.accept());page.locator(f'[data-doc-remove="{self.web_source["id"]}"]').click()
                page.wait_for_function('(id)=>!document.querySelector(`[data-doc-remove="${id}"]`)',arg=self.web_source['id'])
                self.web_removed=True
                self.phase='surviving-overlap-reference'
                expected={**self.current,'source_ids':[self.source['id']],'captured_by_source_id':self.web_source['id']}
                cli_read=self.cli('documents','read','--reference',self.current['reference'])
                mcp_read=self.mcp_sync([('read_document',{'reference':self.current['reference']},False)])[0]
                with page.expect_response(lambda r:r.url.endswith('/api/documents/read') and r.request.method=='POST') as survivor_response:
                    page.locator(f'[data-doc-read="{result["results"].index(new)}"]').click()
                assert survivor_response.value.status==200
                web_read=survivor_response.value.json()
                for value in [cli_read,mcp_read,web_read]:
                    read_matches(value,expected,self.raw2,self.guide,collector=self.web_source['id'])
                self.save('overlap-survivor',{'original_hit':self.current,'removed_source_id':self.web_source['id'],'current_qualification_source_ids':[self.source['id']],'historical_collector':self.web_source['id'],'cli_read':cli_read,'mcp_read':mcp_read,'web_read':web_read})
            finally:
                context.tracing.stop(path=str(self.out/'web-trace.zip'));context.close();browser.close()

    def failures_and_restart(self):
        self.phase='fixture-delete';self.note.unlink();self.expected.pop(self.note);self.edits.append({'time':now(),'action':'fixture-delete','path':str(self.note)})
        self.phase='explicit-refresh-delete';self.cli('documents','refresh','--source-id',self.source['id'])
        for path in [self.guide,self.control]:self.collectors[path]=self.source['id']
        self.all_files([self.guide,self.control,self.other]);self.reject_refs([self.initial[self.note]])
        old=self.cli('documents','search','continuous')['results'][0]
        assert self.cli('documents','read','--reference',self.current['reference'])['text']==normalized(self.raw2)
        bad=self.docs/'bad.txt';self.put(bad,b'needle repaired');denied=self.docs/'denied.txt';self.put(denied,b'needle unreadable')
        self.phase='explicit-refresh-error-positive';self.cli('documents','refresh','--source-id',self.source['id'])
        for path in [self.guide,self.control,bad,denied]:self.collectors[path]=self.source['id']
        before_bad=self.cli('documents','search','repaired')['results'][0]
        before_denied=self.cli('documents','search','unreadable')['results'][0]
        self.put(bad,b'\xff\xfe');before=self.stamp('errors-before');old_permission=None
        if sys.platform!='win32':old_permission=denied.stat().st_mode;denied.chmod(0)
        try:
            self.phase='explicit-refresh-errors';self.cli('documents','refresh','--source-id',self.source['id'])
            source=next(s for s in self.cli('documents','sources') if s['id']==self.source['id']);assert source['status']=='partial'
            files=self.cli('documents','files','--source-id',self.source['id']);failed={Path(x['path']).name:x for x in files if x['status']=='failed'}
            assert 'bad.txt' in failed
            if old_permission is not None:assert 'denied.txt' in failed
            successful=[self.guide,self.control,self.other]+([] if old_permission is not None else [denied])
            self.all_files(successful)
            mcp_partial=self.mcp_sync([('search_documents',{'query':'needle','limit':50},False)])[0];paths(mcp_partial,successful);self.read_mcp(mcp_partial['results'])
            self.reject_refs([before_bad]+([before_denied] if old_permission is not None else []))
            assert self.cli('documents','search','escapeuniquemarker')['results']==[]
            self.read_cli(old)
            self.save('native-file-errors',{'source':source,'files':files,'junction_or_symlink':str(self.link),'permission_failure_expected':old_permission is not None})
            self.phase='web-error-state';self.inspect_web_state('web-partial',partial=True)
        finally:
            if old_permission is not None:denied.chmod(old_permission)
        assert self.stamp('errors-after')==before
        self.put(bad,b'needle repaired');self.phase='explicit-refresh-repair';self.cli('documents','refresh','--source-id',self.source['id'])
        wanted=[self.guide,self.control,bad,denied,self.other]
        before_sources=self.cli('documents','sources');sources(before_sources,self.known_sources(4))
        before_files=self.cli('documents','files')
        before_hits=self.all_files(wanted);checkpoint={Path(h['path']):h for h in before_hits}
        for previous in [before_bad,before_denied]:
            restored=checkpoint[Path(previous['path'])]
            assert restored['id']==previous['id'] and restored['version']==previous['version'] and restored['sha256']==previous['sha256']
        self.reject_refs([before_bad]+([before_denied] if old_permission is not None else []))
        self.phase='restart-without-refresh';before=self.stamp('restart-before');self.stop_service();self.start_service()
        assert self.cli('documents','sources')==before_sources and self.cli('documents','files')==before_files
        after_hits=self.all_files(wanted)
        values=self.mcp_sync([('list_document_sources',{},False),('search_documents',{'query':'needle','limit':50},False)])
        assert values[0]==before_sources;paths(values[1],wanted)
        for collection in [after_hits,values[1]['results']]:
            for item in collection:
                previous=checkpoint[Path(item['path'])]
                for key in ['id','version','sha256','text_length','captured_at','captured_by_source_id','source_ids']:assert item[key]==previous[key]
        self.read_mcp(values[1]['results'])
        # References obtained before stopping must remain valid without refresh.
        for item in before_hits:self.read_cli(item)
        self.read_mcp(before_hits)
        self.inspect_web_state('web-restarted',checkpoint=checkpoint)
        self.save('restart-checkpoint',{'sources_before':before_sources,'files_before':before_files,'hits_before':before_hits,'hits_after':after_hits,'mcp_after':values,'same_configuration_versions_and_all_original_references':True})
        assert self.stamp('restart-after')==before
        self.cli('documents','remove',self.source['id']);self.reject_refs([h for h in before_hits if Path(h['path'])!=self.other])
        remaining=self.all_files([self.other]);self.read_mcp(remaining)
        mcp_remaining=self.mcp_sync([('search_documents',{'query':'needle','limit':50},False)])[0];paths(mcp_remaining,[self.other])
        self.cli('documents','remove',self.single['id']);self.reject_refs(remaining)
        self.all_files([]);assert self.cli('documents','sources')==self.cli('documents','files')==[]
        final=self.mcp_sync([('list_document_sources',{},False),('search_documents',{'query':'needle','limit':50},False)])
        assert final[0]==[];paths(final[1],[]);assert final[1]['coverage']['indexed_files']==0 and final[1]['coverage']['sources']==[]
        assert self.stamp('after-final-removal')==before
        self.save('fixture-edits',self.edits)

    def execute(self):
        outcome='failed'
        try:
            self.setup();self.browser_flow();self.failures_and_restart()
            opens=[json.loads(s) for s in self.audit.read_text(encoding='utf-8').splitlines()] if self.audit.exists() else []
            assert opens and all(x['phase'].startswith('explicit-refresh') for x in opens),opens
            assert all(x['flags'] & getattr(os,'O_ACCMODE',os.O_WRONLY|os.O_RDWR) == os.O_RDONLY for x in opens),'source opened for writing'
            outside=os.path.normcase(str(self.out/'outside'))
            assert not any(x['path']==outside or x['path'].startswith(outside+os.sep) for x in opens),'link target was opened'
            evidence_available(self.out,['web-pending.png','web-original.png','web-zero.png','web-old-reference-rejected.png','web-updated.png','web-partial.png','web-restarted.png','web-trace.zip','web-partial-trace.zip','web-restarted-trace.zip'])
            self.save('body-read-audit',{'entries':opens,'only_explicit_refresh':True});outcome='passed'
        except BaseException:
            (self.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
        finally:
            self.stop_service()
            identities=[json.loads(s) for s in (self.out/'product-processes.jsonl').read_text().splitlines()] if (self.out/'product-processes.jsonl').exists() else []
            for value in identities:identity(value,self.config['expected_platform'])
            self.save('product-identities',{'count':len(identities),'all_ordinary':bool(identities),'processes':identities})
            self.save('result',{'status':outcome,'started_at':self.started,'finished_at':now(),'platform':sys.platform,'cleanup':{'all_owned_services_stopped':all(not x.get('alive',True) and not x.get('actual_alive',True) and x.get('port_closed',False) for x in self.services)},'scope':'fresh synthetic files, installed Local only; no Hub or daily archive'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();Probe(json.loads(a.target_config.read_text(encoding='utf-8-sig')),a.output.resolve()).execute()


if __name__=='__main__':main()

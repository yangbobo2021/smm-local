"""Opt-in E1: fresh installed Local CLI, real Web and stdio MCP, ordinary user."""
import argparse
import asyncio
import ctypes
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

from local_documents_checks import hit, identity, normalized, paths, self_check, text_range


def now():return datetime.now(timezone.utc).isoformat()


class Probe:
    def __init__(self,config,out):
        assert not out.exists(),'use a new output directory'
        out.mkdir(parents=True);self.out=out;self.config=config;self.python=config['local_python'];self.db=out/'archive.sqlite3'
        self.docs=out/'资料 空格';self.docs.mkdir();self.empty=out/'empty-agent';self.empty.mkdir()
        self.calls=[];self.process=None;self.service_log=None;self.services=[];self.web=[]
        self.audit=out/'source-opens.jsonl';self.phase='initial';self.expected={};self.edits=[]
        self.started=now()
        self.bootstrap="""import sys,os,json,runpy,time
roots=json.loads(os.environ['SMM_DOC_PROBE_ROOTS']); logfile=os.environ['SMM_DOC_PROBE_AUDIT'];phasefile=os.environ['SMM_DOC_PROBE_PHASE_FILE']
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
        return dict(os.environ,PYTHONUTF8='1',SMM_DOC_PROBE_ROOTS=json.dumps([os.path.normcase(str(self.docs.resolve())),os.path.normcase(str((self.out/'outside').absolute())),os.path.normcase(str(self.out/'other.txt'))]),SMM_DOC_PROBE_AUDIT=str(self.audit),SMM_DOC_PROBE_PHASE_FILE=str(self.out/'phase.txt'))

    def argv(self,module,*args):return [self.python,'-I','-B','-c',self.bootstrap,module,*map(str,args)]

    def run(self,args,code=0):
        start=now();p=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',env=self.env(),timeout=120)
        self.calls.append({'argv':list(map(str,args)),'phase':self.phase,'started_at':start,'finished_at':now(),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        self.save('commands',self.calls);assert p.returncode==code,p.stderr
        return p.stdout

    def cli(self,*args,code=0):
        text=self.run(self.argv('smm_local.cli','--db',self.db,*args),code)
        return json.loads(text) if code==0 else text

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
        self.put(self.guide,self.raw);self.put(self.note,b'needle nested original\n');self.put(self.control,b'needle continuous control\n');self.put(self.other,b'needle unrelated Q\n')
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
        self.phase='cli-search-read'
        result=self.cli('documents','search','needle','--scope','project','--project-id',self.p['id'],'--limit','50')
        paths(result,[self.guide,self.note,self.control]);assert self.cli('documents','search','escapeuniquemarker')['results']==[]
        self.old_cli=next(h for h in result['results'] if h['path']==str(self.guide))
        hit(self.old_cli,self.raw,self.guide);r=self.cli('documents','read','--reference',self.old_cli['reference']);text_range(r,normalized(self.raw),start=0,end=len(normalized(self.raw)))
        expanded=self.cli('documents','read','--reference',self.old_cli['reference'],'--start','7','--end','14');text_range(expanded,normalized(self.raw),start=7,end=14)
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
                    if r.status==200:return
            except OSError:time.sleep(.2)
        raise AssertionError('service not ready')

    def stop_service(self):
        if self.process is None:return
        self.process.terminate()
        try:code=self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:self.process.kill();code=self.process.wait(timeout=20)
        self.services[-1].update(finished_at=now(),exit_code=code,alive=self.process.poll() is None)
        self.save('services',self.services);self.service_log.close();self.process=None

    async def mcp(self,steps):
        from mcp import ClientSession,StdioServerParameters
        from mcp.client.stdio import stdio_client
        number=len(list(self.out.glob('mcp-call-*.json')))+1
        child=self.argv('smm_local.mcp_server','--db',self.db)
        receipt=self.out/f'mcp-process-{number}.json'
        args=[self.python,'-I','-B',str(Path(__file__).with_name('local_documents_mcp_worker.py')),str(receipt),json.dumps(child)]
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
                        if bad:assert result.isError;answers.append(None)
                        else:
                            assert not result.isError
                            answer=json.loads(result.content[0].text);answers.append(answer)
        finally:
            err.close();self.save(f'mcp-call-{number}',{'started_at':started,'finished_at':now(),'transport':'actual stdio subprocess','argv':args,'records':records})
        assert receipt.exists() and json.loads(receipt.read_text())['alive'] is False,'MCP process cleanup receipt missing'
        return answers

    def check_mcp(self):
        self.phase='mcp-search-read'
        values=asyncio.run(self.mcp([('list_document_sources',{},False),('search_documents',{'query':'needle','scope':'project','project_id':self.p['id'],'limit':50},False),('search_documents',{'query':'nonexistentuniqueterm'},False)]))
        paths(values[1],[self.guide,self.note,self.control]);assert values[2]['results']==[] and values[2]['coverage']['indexed_files']==4
        self.old_mcp=next(h for h in values[1]['results'] if h['path']==str(self.guide));hit(self.old_mcp,self.raw,self.guide)
        read=asyncio.run(self.mcp([('read_document',{'reference':self.old_mcp['reference'],'start':7,'end':14},False)]))[0]
        text_range(read,normalized(self.raw),start=7,end=14)

    def browser_flow(self):
        from playwright.sync_api import sync_playwright
        self.start_service();self.phase='web-read-configure'
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':self.config['browser']} if self.config.get('browser') else {}))
            context=browser.new_context(viewport={'width':1280,'height':1000});context.tracing.start(screenshots=True,snapshots=True,sources=True)
            page=context.new_page()
            def response(r):
                if '/api/documents/' in r.url or r.url.endswith('/api/projects'):
                    try:self.web.append({'url':r.url,'status':r.status,'method':r.request.method,'request':r.request.post_data,'json':r.json(),'time':now()});self.save('web-responses',self.web)
                    except Exception:pass
            page.on('response',response)
            try:
                page.goto(self.url);page.locator('[data-tab=documents]').click()
                page.locator('#doc-path').fill(str(self.guide));page.locator('#doc-projects').select_option(str(self.p['id']))
                page.locator('#doc-save').click();page.wait_for_function("document.querySelector('#doc-source-list').textContent.includes('pending')")
                page.screenshot(path=str(self.out/'web-pending.png'),full_page=True)
                rows=[r for r in self.web if r['method']=='POST' and r['url'].endswith('/api/documents/sources')]
                self.web_source=rows[-1]['json'];assert self.web_source['project_ids']==[self.p['id']] and self.web_source['status']=='pending'
                self.phase='explicit-refresh-web';page.locator(f'[data-doc-refresh="{self.web_source["id"]}"]').click()
                page.wait_for_function("!document.querySelector('#doc-source-list').textContent.includes('pending')")
                self.phase='web-search-read';page.locator('#doc-query').fill('needle');page.locator('#doc-scope').select_option('project');page.locator('#doc-search-project').select_option(str(self.p['id']));page.locator('#doc-limit').select_option('50');page.locator('#doc-search-submit').click()
                page.wait_for_selector('#doc-results [data-doc-read]');page.locator('#doc-results [data-doc-read]').filter(has_text='读取原文')
                searches=[r['json'] for r in self.web if r['url'].endswith('/api/documents/search') and r['method']=='POST'];result=searches[-1];paths(result,[self.guide,self.note,self.control])
                self.old_web=next(h for h in result['results'] if h['path']==str(self.guide));index=result['results'].index(self.old_web)
                page.locator(f'[data-doc-read="{index}"]').click();page.wait_for_selector('#doc-reader:not([hidden])')
                assert page.locator('#doc-reader-text').inner_text()==normalized(self.raw);assert page.evaluate('window.__docExecution') is None
                page.screenshot(path=str(self.out/'web-original.png'),full_page=True)
                self.check_mcp();before=self.stamp('before-edit');assert before==self.stamp('after-three-entrances')
                self.raw2='needle edited 中文😀 e\u0301\r\nnew captured text\n'.encode();self.put(self.guide,self.raw2)
                self.phase='explicit-refresh-edit';self.cli('documents','refresh','--source-id',self.source['id'])
                self.phase='reject-old-references';self.cli('documents','read','--reference',self.old_cli['reference'],code=2)
                asyncio.run(self.mcp([('read_document',{'reference':self.old_mcp['reference']},True)]))
                page.locator(f'[data-doc-read="{index}"]').click();page.wait_for_function("document.querySelector('#notice').classList.contains('error')")
                page.screenshot(path=str(self.out/'web-old-reference-rejected.png'),full_page=True)
                page.locator('#doc-search-submit').click();page.wait_for_function("document.querySelector('#notice').textContent.includes('文档') && !document.querySelector('#notice').classList.contains('error')")
                result=[r['json'] for r in self.web if r['url'].endswith('/api/documents/search')][-1];new=next(h for h in result['results'] if h['path']==str(self.guide));assert new['id']==self.old_cli['id'] and new['version']!=self.old_cli['version'];hit(new,self.raw2,self.guide)
                page.locator(f'[data-doc-read="{result["results"].index(new)}"]').click();page.wait_for_function("document.querySelector('#doc-reader-text').textContent.includes('edited')")
                assert page.locator('#doc-reader-text').inner_text()==normalized(self.raw2)
                page.screenshot(path=str(self.out/'web-updated.png'),full_page=True)
                self.current=new
                # Exercise complete replacement through the actual Web form as well.
                page.locator(f'[data-doc-edit="{self.web_source["id"]}"]').click();page.locator('#doc-projects').select_option([str(self.p['id']),str(self.q['id'])]);page.locator('#doc-exclude').fill('private/**');page.locator('#doc-recursive').uncheck();page.locator('#doc-save').click()
                page.wait_for_function("document.querySelector('#doc-source-list').textContent.includes('pending')")
                changed=[r['json'] for r in self.web if r['method']=='PUT'][-1];assert set(changed['project_ids'])=={self.p['id'],self.q['id']} and changed['recursive'] is False and changed['exclude']==['private/**']
                self.phase='explicit-refresh-web-set';page.locator(f'[data-doc-refresh="{self.web_source["id"]}"]').click();page.wait_for_function("!document.querySelector('#doc-source-list').textContent.includes('pending')")
            finally:
                context.tracing.stop(path=str(self.out/'web-trace.zip'));context.close();browser.close()

    def failures_and_restart(self):
        self.phase='fixture-delete';self.note.unlink();self.expected.pop(self.note);self.edits.append({'time':now(),'action':'fixture-delete','path':str(self.note)})
        self.phase='explicit-refresh-delete';self.cli('documents','refresh','--source-id',self.source['id'])
        paths(self.cli('documents','search','needle','--scope','project','--project-id',self.p['id'],'--limit','50'),[self.guide,self.control])
        old=self.cli('documents','search','continuous')['results'][0]
        self.cli('documents','remove',self.web_source['id']);assert self.cli('documents','read','--reference',self.current['reference'])['text']==normalized(self.raw2)
        bad=self.docs/'bad.txt';self.put(bad,b'needle repaired');denied=self.docs/'denied.txt';self.put(denied,b'needle unreadable')
        self.phase='explicit-refresh-error-positive';self.cli('documents','refresh','--source-id',self.source['id'])
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
            assert self.cli('documents','search','escapeuniquemarker')['results']==[]
            assert self.cli('documents','read','--reference',old['reference'])['text']=='needle continuous control\n'
            self.save('native-file-errors',{'source':source,'files':files,'junction_or_symlink':str(self.link),'permission_failure_expected':old_permission is not None})
        finally:
            if old_permission is not None:denied.chmod(old_permission)
        assert self.stamp('errors-after')==before
        self.put(bad,b'needle repaired');self.phase='explicit-refresh-repair';self.cli('documents','refresh','--source-id',self.source['id'])
        self.cli('documents','read','--reference',before_bad['reference'],code=2)
        if old_permission is not None:self.cli('documents','read','--reference',before_denied['reference'],code=2)
        self.phase='restart-without-refresh';before=self.stamp('restart-before');self.stop_service();self.start_service()
        current=self.cli('documents','search','edited')['results'][0];hit(current,self.raw2,self.guide)
        read=asyncio.run(self.mcp([('read_document',{'reference':current['reference']},False)]))[0];text_range(read,normalized(self.raw2))
        assert self.stamp('restart-after')==before
        self.cli('documents','remove',self.source['id']);self.cli('documents','read','--reference',current['reference'],code=2)
        assert self.cli('documents','search','edited')['results']==[]
        assert self.cli('documents','read','--reference',self.cli('documents','search','unrelated')['results'][0]['reference'])['text']=='needle unrelated Q\n'
        self.cli('documents','remove',self.single['id']);assert self.cli('documents','sources')==[]
        self.save('fixture-edits',self.edits)

    def execute(self):
        outcome='failed'
        try:
            self.setup();self.browser_flow();self.failures_and_restart()
            opens=[json.loads(s) for s in self.audit.read_text(encoding='utf-8').splitlines()] if self.audit.exists() else []
            assert opens and all(x['phase'].startswith('explicit-refresh') for x in opens),opens
            self.save('body-read-audit',{'entries':opens,'only_explicit_refresh':True});outcome='passed'
        except BaseException:
            (self.out/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
        finally:
            self.stop_service();self.save('result',{'status':outcome,'started_at':self.started,'finished_at':now(),'platform':sys.platform,'cleanup':{'all_owned_services_stopped':all(not x.get('alive',True) for x in self.services)},'scope':'fresh synthetic files, installed Local only; no Hub or daily archive'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();Probe(json.loads(a.target_config.read_text(encoding='utf-8-sig')),a.output.resolve()).execute()


if __name__=='__main__':main()

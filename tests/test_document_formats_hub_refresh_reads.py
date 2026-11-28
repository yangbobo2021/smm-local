"""Real Hub CLI content workers must not hold the archive read/control guard."""
import hashlib,json,os,signal,sqlite3,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
from pathlib import Path
import httpx,psutil,pytest
from document_helpers import observe,ROOT
from document_formats_partial_fixture import partial_pdf
from document_formats_refresh_barrier import HOOK,prepare_gate
from document_formats_platform import process_tree
from test_document_formats_management import native_input
from test_document_formats_retry import ENGINE,DATA,FONT,keep
from test_document_formats_upload_restart import Server
from test_document_formats_installed_minimum import assert_complete_source_text

pytestmark=pytest.mark.skipif(os.name!='posix' or not all((ENGINE,DATA,FONT)),reason='requires actual POSIX creator assets and isolated HTTP process; not Windows/service evidence when skipped')


def test_actual_raw_barrier_has_scope_and_release_controls(tmp_path):
    path=tmp_path/'raw'/('a'*64);path.parent.mkdir();path.write_bytes(b'known raw bytes')
    other=path.parent/'other';other.write_bytes(b'allowed bytes')
    gate=tmp_path/'gate';env=prepare_gate(gate,[path])
    normal=subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;print(Path(sys.argv[1]).read_text())',str(path)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    different=subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;print(Path(sys.argv[1]).read_text())',str(other),'--task-token','probe'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert normal.returncode==different.returncode==0 and normal.stdout.strip()=='known raw bytes' and different.stdout.strip()=='allowed bytes'
    assert list(gate.glob('*.json'))==[]
    process=subprocess.Popen([sys.executable,'-c','from pathlib import Path;import sys;print(Path(sys.argv[1]).read_text())',str(path),'--task-token','probe'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',start_new_session=True)
    try:
        until=time.monotonic()+10;entry=gate/(path.name+'.json')
        while not entry.exists() and process.poll() is None and time.monotonic()<until:time.sleep(.02)
        assert entry.exists() and process.poll() is None
        value=json.loads(entry.read_text());assert value['pid']==process.pid and value['token']=='probe' and value['path']==str(path)
    finally:
        (gate/'abort').write_text('release')
        out,err=process.communicate(timeout=10)
    assert process.returncode==0 and out.strip()=='known raw bytes'
    observe('refresh-raw-gate-controls',{'normal_source_read_exit':normal.returncode,'different_path_exit':different.returncode,'controlled_child_exit':process.returncode,'entry':value,'raw_bytes_after_release':out.strip()})


def test_hub_refresh_keeps_all_existing_control_reads_available(tmp_path,monkeypatch):
    # TC-008-hub-refresh-reads
    server=Server(tmp_path/'hub','hub');server.db=server.root/'smm-hub.sqlite3'
    materials=server.root/'materials';materials.mkdir();controls=[];targets=[];sources=[];all_items=[]
    readonly=server.root/'query-processing-audit.jsonl';monkeypatch.setenv('SMM_008_WEB_READ_ONLY',str(readonly))
    for group in (0,1):
        for category in ('controls','targets'):
            directory=materials/category/str(group);directory.mkdir(parents=True)
            kinds=[('docx','ready'),('pdf','partial')] if category=='controls' else [(f,'ready') for f in ('docx','xlsx','pdf')]
            for format,status in kinds:
                for number in (1,2):
                    key=category+str(group)+format+status+str(number)
                    if status=='partial':
                        raw,t=partial_pdf(key,FONT);truth={'words':[t['anchor']],'excluded':[],'tables':[],'partial_reason':t['known_failure']}
                    else:raw,truth=native_input(format,key)
                    if format=='docx':truth['ordered_groups']=[truth['words'][:12]]
                    path=directory/(key+'.'+format);path.write_bytes(raw)
                    item={'name':path.name,'group':group,'category':category,'path':path,'raw':raw,'truth':truth,'format':format,'status':status,'sha256':hashlib.sha256(raw).hexdigest(),'mtime_ns':path.stat().st_mtime_ns,'anchor':truth['words'][0].split()[0]}
                    (controls if category=='controls' else targets).append(item);all_items.append(item)
                    keep('inputs/'+item['name'],raw);keep('truth/'+item['name']+'.json',json.dumps(truth,ensure_ascii=False).encode())
    assert len(controls)==8 and len(targets)==12 and len({i['sha256'] for i in all_items})==20
    # Refresh/reprocess now execute in the actual Hub service.  Install the raw
    # worker barrier before starting that service, not only in the CLI caller.
    gate=server.root/'raw-gate';env=prepare_gate(gate,[server.root/'.document-snapshots'/'raw'/i['sha256'] for i in targets])
    monkeypatch.setenv('SMM_008_QUERY_SCOPED_GUARD','1')
    for name in ('SMM_008_REFRESH_GATE','SMM_008_REFRESH_RAW_PATHS'):monkeypatch.setenv(name,env[name])
    (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\n'+HOOK,encoding='utf-8')
    cli_prefix=[sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(server.root),'documents']
    cli_runs=[];failed=[];observations=[];seen=set();worker_tokens=set();baseline_readonly=None;baseline_source=None
    def cli(*args):
        argv=cli_prefix+list(map(str,args));r=subprocess.run(argv,cwd=server.root,capture_output=True,text=True,encoding='utf-8',timeout=90)
        observe('refresh-setup-cli',{'argv':argv,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0,r.stderr
        return json.loads(r.stdout)
    def request(method,path,body=None):return server.call(method,path,body)
    def assign_identity(item):
        with sqlite3.connect('file:'+str(server.db)+'?mode=ro',uri=True) as c:
            row=c.execute('SELECT id FROM documents WHERE path_key=?',(os.path.normcase(str(item['path'].resolve())),)).fetchone();assert row is not None
            archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
            hub=json.loads(c.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()[0])
        item['id']=row[0];item['origin']={'device_id':hub,'archive_id':archive,'document_id':row[0]};assert hub==server.context['hub_id']
    def complete(item,reference=None):
        hits=request('POST','/documents/search',{**server.context,'scope':'project','project_id':item['project']['id'],'query':item['anchor'],'limit':50}).json()['results']
        assert len(hits)==1 and hits[0]['id']==item['id'];hit=hits[0]
        assert hit['origin']==item['origin'] and hit['version']==hit['processing_version']==1 and hit['sha256']==item['sha256'] and hit['format']==item['format'] and hit['processing_status']==item['status']
        body={**server.context,'reference':reference or hit['reference']}
        value=request('POST','/documents/read',{**body,'start':0,'end':hit['text_length']}).json()
        if item['format']=='docx':assert_complete_source_text(value['text'],item['truth'])
        else:assert all(word in value['text'] for word in item['truth']['words'])
        assert all(word not in value['text'] for word in item['truth']['excluded'])
        if item['status']=='partial':assert value['text']==item['truth']['words'][0] and any(e['page']==2 and item['truth']['partial_reason']['reason_contains'] in e['reason'] for e in value['coverage']['errors'])
        expected=item['truth']['tables'];assert len(value['tables'])==len(expected) and len({t['table_id'] for t in value['tables']})==len(expected)
        actual=[];used=set()
        for table in value['tables']:
            view=request('POST','/documents/read',{**body,'view':'table','table_id':table['table_id'],'row_start':1,'row_end':table['rows']+1,'column_start':1,'column_end':table['columns']+1}).json();actual.append(view)
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
            matches=[i for i,t in enumerate(expected) if (view['rows'],view['columns'])==(t['rows'],t['columns']) and len(cells)==len(t['cells']) and set(cells)==set(t['cells']) and all(view['location'].get(k)==v for k,v in t['location'].items())]
            assert len(matches)==1 and matches[0] not in used;used.add(matches[0])
        assert used==set(range(len(expected)))
        info=request('POST','/documents/read',{**body,'view':'original-info'}).json()
        for data in [value,info,*actual]:assert data['id']==item['id'] and data['origin']==item['origin'] and data['version']==data['processing_version']==1 and data['sha256']==item['sha256']
        raw=request('POST','/documents/original',body).content;assert raw==item['raw'] and info['bytes']==len(raw) and info['available'] is True
        keep('downloads/'+item['sha256'],raw)
        return hit,{'read':value,'tables':actual,'info':info}
    def query_controls():
        for item in controls:assert complete(item,item['reference'])[1]==item['snapshot']
        assert request('GET','/documents/sources').status_code==200
        assert request('GET','/documents/files').status_code==200
        return True
    try:
        server.start(deny=[i['path'] for i in all_items]);server.client.timeout=httpx.Timeout(3)
        probe=server.client.post('/__test_processing_probe');assert probe.status_code==200 and probe.json()=={'blocked':['processing','subprocess','source'],'pid':server.serving_pid}
        baseline_readonly=readonly.read_text();assert len(baseline_readonly.splitlines())==2
        baseline_source=server.log.read_text() if server.log.exists() else ''
        cli('processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
        projects=[request('POST','/projects',{**server.context,'name':'Concurrent ordinary','kind':'ordinary'}).json(),request('POST','/projects',{**server.context,'name':'Concurrent global','kind':'global'}).json()]
        assert [p['project_kind'] for p in projects]==['ordinary','global']
        for item in all_items:item['project']=projects[item['group']]
        for group,project in enumerate(projects):
            source=cli('add',materials/'controls'/str(group),'--project-id',project['id']);cli('refresh','--source-id',source['id'])
            source=cli('add',materials/'targets'/str(group),'--project-id',project['id']);sources.append((source,[i for i in targets if i['group']==group]))
        # First search creates archive reference material; identity expectations
        # subsequently come from raw readonly DB rows, not the search response.
        request('POST','/documents/search',{**server.context,'query':controls[0]['anchor'],'scope':'project','project_id':controls[0]['project']['id']})
        for item in controls:
            assign_identity(item);hit,item['snapshot']=complete(item);item['reference']=hit['reference']
        assert len({i['id'] for i in controls})==8
        # Product CLI must request execution from the enrolled service; the
        # service's own environment carries the gate to its real content child.
        env=dict(os.environ)
        by_sha={i['sha256']:i for i in targets}
        with ThreadPoolExecutor(max_workers=1) as pool:
            for source,group_items in sources:
                argv=cli_prefix+['refresh','--source-id',source['id']]
                outs=(server.root/(source['id']+'.stdout')).open('w');errs=(server.root/(source['id']+'.stderr')).open('w')
                process=subprocess.Popen(argv,cwd=server.root,env=env,stdout=outs,stderr=errs,text=True,encoding='utf-8',start_new_session=True);created=psutil.Process(process.pid).create_time()
                try:
                    while len(seen.intersection(i['sha256'] for i in group_items))<len(group_items):
                        until=time.monotonic()+30;entry=None
                        while time.monotonic()<until and process.poll() is None:
                            new=[p for p in gate.glob('*.json') if p.stem not in seen]
                            if new:assert len(new)==1;entry=new[0];break
                            time.sleep(.02)
                        assert entry is not None,{'exit':process.poll(),'seen':sorted(seen)}
                        state=json.loads(entry.read_text());digest=state['sha256'];assert digest in by_sha and by_sha[digest] in group_items
                        item=by_sha[digest];worker=psutil.Process(state['pid']);tree=process_tree(server.serving_stamp)
                        assert any(p['pid']==state['pid'] and p['created']==state['created'] for p in tree)
                        assert state['ppid']==worker.ppid()==server.serving_pid and worker.is_running()
                        assert state['created']==worker.create_time() and state['actual_executable']==worker.exe()
                        assert Path(state['cwd']).resolve()==(server.root/'.document-snapshots/tasks'/state['token']).resolve()
                        assert Path(state['argv'][0]).resolve()==(ROOT/'src/smm_local/document_worker.py').resolve() and state['uid']==os.getuid()!=0
                        with sqlite3.connect('file:'+str(server.db)+'?mode=ro',uri=True) as c:
                            actual=c.execute('SELECT a.state,x.raw_sha256,d.path FROM document_processing_attempts a JOIN document_captures x ON x.id=a.capture_id JOIN documents d ON d.pk=x.document_pk WHERE a.id=?',(state['token'],)).fetchone()
                        assert actual is not None and actual[0]=='processing' and actual[1]==digest and Path(actual[2]).resolve()==item['path'].resolve()
                        future=pool.submit(query_controls);early=False;error=None
                        try:early=future.result(timeout=5) is True
                        except Exception as exc:error=type(exc).__name__+': '+str(exc)
                        finally:
                            if not early:(gate/'abort').write_text('release remaining workers')
                            (gate/(digest+'.release')).write_text('release')
                        observe('refresh-before-release',{'worker':state,'controller_pid':process.pid,'controller_created':created,'control_ids':sorted(i['id'] for i in controls),'completed_correctly_before_release':early,'error':error})
                        observations.append(early);seen.add(digest);worker_tokens.add(state['token'])
                        if not early:failed.append(error);break
                finally:
                    (gate/'abort').write_text('cleanup') if failed or sys.exc_info()[0] is not None else None
                    try:process.wait(timeout=40)
                    except subprocess.TimeoutExpired:
                        live=psutil.Process(process.pid);assert live.create_time()==created
                        os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10)
                    outs.close();errs.close();stdout=Path(outs.name).read_text();stderr=Path(errs.name).read_text();cli_runs.append({'argv':argv,'pid':process.pid,'created':created,'exit':process.returncode,'stdout':stdout,'stderr':stderr})
                    observe('refresh-controller',cli_runs[-1])
                assert process.returncode==0,stderr
                assert query_controls() is True
                if failed:break
        assert observations and all(observations),{'queries_waited_for_content_worker':failed,'barriers':len(seen)}
        assert seen==set(by_sha)
        for item in targets:assign_identity(item);complete(item)
        assert len({i['id'] for i in all_items})==20
        assert readonly.read_text()==baseline_readonly
        source_events=[e for e in server.events() if e['event']=='open']
        assert source_events==[json.loads(line) for line in baseline_source.splitlines()]
        worker_events=[e for e in server.events() if e['event']=='subprocess.Popen']
        assert len(worker_tokens)==12 and worker_tokens<={e['task_token'] for e in worker_events}
        for item in all_items:assert item['path'].stat().st_mtime_ns==item['mtime_ns'] and item['path'].read_bytes()==item['raw']
        observe('refresh-all-controls-available',{'target_workers':len(seen),'old_control_documents':len(controls),'ready_and_partial':True,'ordinary_and_global':True,'all_old_refs_unchanged':True,'original_inputs_unchanged':20,'http_source_opens':0,'http_processing_events_after_positive_control':0})
    finally:
        if 'gate' in locals():(gate/'abort').write_text('final cleanup')
        keep('server/readonly-audit.jsonl',readonly.read_bytes() if readonly.exists() else b'')
        server.stop()

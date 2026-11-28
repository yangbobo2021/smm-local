"""Real in-flight cached workers: continuous authorization and final removal."""
import hashlib,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
from uuid import uuid4
import psutil,pytest
from document_helpers import ROOT,observe
from document_formats_platform import process_identity,spawn_identity,process_tree,terminate_verified,matching_process,utf8_environment,preserve_diagnostics,same_existing_path
from document_formats_exit_observer import waiting_for_owned_exit
from document_formats_partial_fixture import partial_pdf
from test_document_formats_management import native_input
from test_document_formats_installed_minimum import assert_complete_source_text
from test_document_formats_retry import ENGINE,DATA,FONT,keep
from test_document_formats_upload_restart import Server


def write_json(name,value):keep(name,json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8'))


def test_active_worker_barrier_and_source_deny_have_real_controls(tmp_path,monkeypatch):
    root=tmp_path/'gate';root.mkdir();hooks=tmp_path/'hooks';hooks.mkdir()
    raw=tmp_path/'raw'/('a'*64);raw.parent.mkdir();raw.write_bytes(b'known raw bytes')
    other=tmp_path/'other';other.write_bytes(b'other bytes');source=tmp_path/'source';source.write_bytes(b'forbidden source')
    (hooks/'sitecustomize.py').write_text('from document_formats_lifecycle_hook import install\ninstall()\n',encoding='utf-8')
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_ACTIVE_GATE=str(root),SMM_008_ACTIVE_RAW=json.dumps([str(raw)]),SMM_008_ACTIVE_SOURCES=json.dumps([str(source)]))
    (root/'armed').write_text(raw.name);code='from pathlib import Path;import sys;sys.stdout.buffer.write(Path(sys.argv[1]).read_bytes())'
    normal=subprocess.run([sys.executable,'-B','-c',code,str(raw)],env=env,capture_output=True,timeout=10)
    different=subprocess.run([sys.executable,'-B','-c',code,str(other),'--task-token','other'],env=env,capture_output=True,timeout=10)
    assert normal.returncode==different.returncode==0 and normal.stdout==b'known raw bytes' and different.stdout==b'other bytes' and not list(root.glob('*.json'))
    child=subprocess.Popen([sys.executable,'-B','-c',code,str(raw),'--task-token','probe'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=os.name!='nt');stamp=spawn_identity(psutil.Process(child.pid))
    try:
        until=time.monotonic()+10;entry=root/'probe.json'
        while not entry.exists() and child.poll() is None and time.monotonic()<until:time.sleep(.01)
        assert entry.exists() and child.poll() is None
        value=json.loads(entry.read_bytes())
        members={p['pid']:p for p in process_tree(stamp)}
        assert value['pid'] in members, 'gate entered outside the owned launcher tree'
        worker=members[value['pid']]
        assert value['created']==worker['created'] and value['argv']==worker['argv']
        assert value['argv'][1:]==child.args[1:]
        assert same_existing_path(value['exe'],worker['exe'])
        assert any(same_existing_path(value['exe'],p) for p in (sys.executable,getattr(sys,'_base_executable',sys.executable),psutil.Process().exe()))
        assert value['sha256']==raw.name and value['token']=='probe' and value['path']==os.path.normcase(str(raw.resolve()))
    finally:
        (root/'probe.release').touch()
        try:out,err=child.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            terminate_verified(process_tree(stamp),owner=child);out,err=child.communicate(timeout=3)
        keep('controls/gate.stdout',out);keep('controls/gate.stderr',err)
    assert child.returncode==0 and out==b'known raw bytes'
    (root/'deny-sources').touch()
    denied=subprocess.run([sys.executable,'-B','-c',code,str(source)],env=env,capture_output=True,timeout=10)
    keep('controls/denied.stdout',denied.stdout);keep('controls/denied.stderr',denied.stderr)
    assert denied.returncode!=0 and b'active source must not reopen' in denied.stderr
    events=[json.loads(line) for line in (root/'source-opens.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events==[{'path':os.path.normcase(str(source.resolve())),'pid':events[0]['pid']}]
    assert raw.read_bytes()==b'known raw bytes' and source.read_bytes()==b'forbidden source'
    observe('active-gate-controls',{'normal_exit':normal.returncode,'different_exit':different.returncode,'launcher':stamp,'owned_members':members,'worker':value,'released_exit':child.returncode,'denied_exit':denied.returncode,'denied_events':events})


@pytest.mark.skipif(os.name!='posix' or not all((ENGINE,DATA,FONT)),reason='this candidate is actual POSIX foreground development only; no Windows or service claim')
@pytest.mark.parametrize('owner',['local','hub'])
def test_active_source_removal_cancels_only_after_last_continuous_authorization(tmp_path,owner,monkeypatch):
    # TC-008-active-source-removal
    server=Server(tmp_path/owner,owner)
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    gate=server.root/'active-gate';gate.mkdir();items=[];controllers=[];observed_trees=[];seen_tokens=set()
    for group in (0,1):
        for status in ('ready','partial'):
            for index in (1,2):
                key=owner+'active'+str(group)+status+str(index)
                if status=='ready':raw,truth=native_input('docx',key);extension='docx'
                else:
                    raw,t=partial_pdf(key,FONT);truth={'words':[t['anchor']],'excluded':[],'tables':[]};extension='pdf'
                directory=server.root/'sources'/key;directory.mkdir(parents=True);path=directory/(key+'.'+extension);path.write_bytes(raw)
                item={'path':path,'raw':raw,'truth':truth,'status':status,'group':group,'key':key,'sha256':hashlib.sha256(raw).hexdigest(),'mtime_ns':path.stat().st_mtime_ns};items.append(item)
                keep('inputs/'+path.name,raw);write_json('truth/'+key+'.json',truth)
    anchors=[item['truth']['words'][0].split()[0] for item in items];assert len(anchors)==len(set(anchors))
    control_raw,control_truth=native_input('docx',owner+'activecontrol');assert control_truth['words'][0].split()[0] not in anchors
    control_path=server.root/'control.docx';control_path.write_bytes(control_raw)
    all_paths=[i['path'] for i in items]+[control_path]
    monkeypatch.setenv('SMM_008_ACTIVE_GATE',str(gate));monkeypatch.setenv('SMM_008_ACTIVE_RAW',json.dumps([str(server.root/'.document-snapshots/raw'/i['sha256']) for i in items]+[str(server.root/'.document-snapshots/raw'/hashlib.sha256(control_raw).hexdigest())]));monkeypatch.setenv('SMM_008_ACTIVE_SOURCES',json.dumps(list(map(str,all_paths))))
    monkeypatch.delenv('SMM_008_WEB_READ_ONLY',raising=False);monkeypatch.delenv('SMM_008_WEB_PROCESSING_GATE',raising=False);monkeypatch.delenv('SMM_008_RESTART_PAUSE',raising=False)
    (server.hooks/'sitecustomize.py').write_text('from document_formats_lifecycle_hook import install\ninstall()\nfrom document_formats_restart_server import install_audit\ninstall_audit()\n',encoding='utf-8')
    cli_prefix=[sys.executable,'-B','-m','smm_local.cli','--db',str(server.db),'documents'] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(server.root),'documents']
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(server.hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_RESTART_AUDIT=str(server.root/'cli-audit.jsonl'))
    def cli(*args,success=True):
        argv=cli_prefix+list(map(str,args));r=subprocess.run(argv,cwd=server.root,env=env,capture_output=True,timeout=35)
        tag=uuid4().hex;keep('cli/'+tag+'.stdout',r.stdout);keep('cli/'+tag+'.stderr',r.stderr)
        observe('active-cli',{'argv':argv,'exit':r.returncode,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest(),'log':tag})
        assert (r.returncode==0) if success else (r.returncode!=0),(r.stdout,r.stderr)
        return json.loads(r.stdout) if success else r
    def rows():
        r=server.client.get(server.prefix+'/documents/files');assert r.status_code==200,r.text
        digest=hashlib.sha256(r.content).hexdigest();keep('lists/'+digest+'.json',r.content)
        return r.json()
    def same_document(entries):
        assert entries and len({e['id'] for e in entries})==1
        assert len({e['source_id'] for e in entries})==len(entries)
        fields=('id','path','version','sha256','processing_version','published_snapshot','latest_attempt','retry_target','original_reference')
        expected={k:entries[0].get(k) for k in fields}
        assert all({k:e.get(k) for k in fields}==expected for e in entries)
        return entries[0]
    def entry(item):return same_document([e for e in rows() if e['id']==item['id']])
    def search(item,expected=True):
        body={**server.context,'query':item['truth']['words'][0].split()[0],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}
        hits=server.call('POST','/documents/search',body).json()['results']
        assert [h['id'] for h in hits]==([item['id']] if expected else [])
        if expected:
            assert hits[0]['sha256']==item['sha256'] and hits[0]['version']==hits[0]['processing_version']==1
        other=projects[1-item['group']]
        assert server.call('POST','/documents/search',{**body,'project_id':other['id']}).json()['results']==[]
        return hits
    def retry_args(item,target):
        return ['reprocess','--document-id',item['id'],*[v for k in ('capture_id','expected_attempt_id','expected_version','expected_processing_version') for v in ['--'+k.replace('_','-'),str(target[k])]]]
    def snapshot(item,reference=None):
        e=entry(item);ref=reference or e['original_reference'];args={**server.context,'reference':ref}
        read=server.call('POST','/documents/read',{**args,'start':0,'end':e['text_length']}).json()
        assert read['id']==item['id'] and read['sha256']==item['sha256'] and read['version']==read['processing_version']==1 and read['processing_status']==item['status']
        assert_complete_source_text(read['text'],item['truth']);assert all(w not in read['text'] for w in item['truth']['excluded'])
        with sqlite3.connect(server.db) as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        expected_origin={'device_id':archive if owner=='local' else server.context['hub_id'],'archive_id':archive,'document_id':item['id']}
        assert read['origin']==expected_origin
        if item['status']=='partial':assert read['text']==item['truth']['words'][0] and any(v['page']==2 and '1600万像素' in v['reason'] for v in read['coverage']['errors'])
        tables=[];used=set();expected=item['truth']['tables'];assert len(read['tables'])==len(expected)
        for t in read['tables']:
            view=server.call('POST','/documents/read',{**args,'view':'table','table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,'column_start':1,'column_end':t['columns']+1}).json();tables.append(view)
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
            matched=[n for n,v in enumerate(expected) if (view['rows'],view['columns'])==(v['rows'],v['columns']) and len(cells)==len(v['cells']) and set(cells)==set(v['cells']) and all(view['location'].get(k)==value for k,value in v['location'].items())]
            assert len(matched)==1 and matched[0] not in used;used.add(matched[0])
        assert used==set(range(len(expected)))
        original=server.call('POST','/documents/original',args).content;assert original==item['raw'];keep('downloads/'+item['sha256'],original)
        search(item)
        return {'text':read['text'],'tables':tables,'ref':ref}
    def raw_state():
        with sqlite3.connect(server.db) as c:
            names=[row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%' OR name LIKE 'hub_document_%' OR name LIKE 'hub_processed_%')")]
            state={t:sorted([list(row) for row in c.execute('SELECT * FROM "'+t+'"')],key=lambda x:json.dumps(x,default=str)) for t in names}
            if owner=='hub':assert 'hub_document_processing_jobs' in state
            return state
    def owned_task_tree(worker,controller):
        live=psutil.Process(worker['pid'])
        parent=psutil.Process(controller.pid if owner=='local' else server.serving_pid)
        if owner=='hub':assert parent.create_time()==server.serving_stamp['created']
        assert live.create_time()==worker['created'] and live.ppid()==parent.pid and live.is_running()
        tree=process_tree(process_identity(live))
        expected=str(server.root/'.document-snapshots/tasks'/worker['token']/'supervision.json')
        watchers=[]
        for sibling in parent.children():
            try:
                argv=sibling.cmdline()
                if (len(argv)>=6 and argv[1:3]==['-B','-m'] and argv[3] in {'smm_local.document_supervisor','smm_hub._archive.document_supervisor'}
                        and argv[4:]==['--watch',expected]):watchers.append(process_identity(sibling))
            except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
        assert len(watchers)==1,{'worker':worker,'controller':parent.pid,'watchers':watchers}
        return tree+watchers
    try:
        server.start()
        configured=cli('processing-configure','--expected-revision',0,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
        assert configured['config']['revision']==1 and configured['ocr']['ready'] is True
        projects=[server.call('POST','/projects',{'name':'active ordinary'} if owner=='local' else {**server.context,'name':'active ordinary','kind':'ordinary'}).json(),server.call('POST','/projects/global').json() if owner=='local' else server.call('POST','/projects',{**server.context,'name':'active global','kind':'global'}).json()]
        for item in items:
            item['project']=projects[item['group']];item['sources']=[]
            for path in (item['path'],item['path'].parent):
                source=cli('add',path,'--project-id',item['project']['id']);cli('refresh','--source-id',source['id']);item['sources'].append(source['id'])
            found=[e for e in rows() if Path(e['path'])==item['path']];assert len(found)==2 and {e['source_id'] for e in found}==set(item['sources'])
            assert all(e['status']=='ready' for e in found),found
            e=same_document(found);assert e['version']==e['processing_version']==1 and e['latest_attempt']['status']==item['status'];item['id']=e['id'];item['initial']=snapshot(item);item['target']=e['retry_target']
            assert item['path'].read_bytes()==item['raw'] and item['path'].stat().st_mtime_ns==item['mtime_ns']
        control_source=cli('add',control_path,'--project-id',projects[0]['id']);cli('refresh','--source-id',control_source['id']);e=next(e for e in rows() if Path(e['path'])==control_path)
        control={'id':e['id'],'path':control_path,'raw':control_raw,'truth':control_truth,'status':'ready','sha256':hashlib.sha256(control_raw).hexdigest(),'project':projects[0],'group':0,'key':owner+'control'};control_snapshot=snapshot(control)
        for p in all_paths:p.unlink()
        (gate/'deny-sources').touch()
        for item in items:
            target=entry(item)['retry_target'];assert target is not None
            (gate/'armed').write_text(item['sha256'],encoding='utf-8')
            argv=cli_prefix+list(map(str,retry_args(item,target)));out=server.root/(item['key']+'.stdout');err=server.root/(item['key']+'.stderr')
            with out.open('wb') as stdout,err.open('wb') as stderr:
                child=subprocess.Popen(argv,cwd=server.root,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            stamp=spawn_identity(psutil.Process(child.pid));controllers.append((child,stamp));until=time.monotonic()+15;worker=None
            while time.monotonic()<until and child.poll() is None:
                matches=list(gate.glob('*.json'))
                for p in matches:
                    value=json.loads(p.read_bytes())
                    if value['sha256']==item['sha256'] and value['token'] not in seen_tokens:worker=value;break
                if worker:break
                time.sleep(.01)
            assert worker is not None,{'exit':child.poll(),'stderr':err.read_text(encoding='utf-8')}
            token=worker['token'];seen_tokens.add(token);tree=owned_task_tree(worker,child);observed_trees.append(tree)
            lease=server.root/'.document-snapshots/tasks/active.json';supervision=json.loads(lease.read_bytes());assert supervision['token']==token and supervision['worker']=={'pid':worker['pid'],'created':worker['created']}
            with sqlite3.connect(server.db) as c:
                a=c.execute('SELECT capture_id,state FROM document_processing_attempts WHERE id=?',(token,)).fetchone();assert a==(target['capture_id'],'processing')
            assert snapshot(item,item['initial']['ref'])['text']==item['initial']['text']
            server.call('DELETE','/documents/sources/'+item['sources'][0],server.context if owner=='hub' else None)
            time.sleep(.2);assert child.poll() is None and matching_process(tree[0]) is not None
            with sqlite3.connect(server.db) as c:
                auth=c.execute('SELECT a.source_id FROM document_capture_authorizations a JOIN document_sources s ON s.id=a.source_id AND s.revision=a.revision WHERE a.capture_id=? AND a.active=1',(target['capture_id'],)).fetchall();assert auth==[(item['sources'][1],)]
            assert snapshot(item,item['initial']['ref'])['text']==item['initial']['text']
            for other in [i for i in items if not i.get('removed')]+[control]:snapshot(other,other['initial']['ref'] if other is not control else control_snapshot['ref'])
            started=time.monotonic();server.call('DELETE','/documents/sources/'+item['sources'][1],server.context if owner=='hub' else None)
            until=started+5;terminal=None
            while time.monotonic()<until:
                with sqlite3.connect(server.db) as c:terminal=c.execute('SELECT state,error,finished_at FROM document_processing_attempts WHERE id=?',(token,)).fetchone()
                if terminal and terminal[0]=='failed' and terminal[2] and not lease.exists() and all(not waiting_for_owned_exit(s) for s in tree):break
                time.sleep(.02)
            elapsed=time.monotonic()-started
            assert elapsed<=5 and terminal[0]=='failed' and terminal[2] and not lease.exists() and all(not waiting_for_owned_exit(s) for s in tree),{'seconds':elapsed,'terminal':terminal,'lease':lease.exists()}
            item['removed']=True
            for other in [i for i in items if not i.get('removed')]+[control]:snapshot(other,other['initial']['ref'] if other is not control else control_snapshot['ref'])
            search(item,expected=False)
            (gate/(token+'.release')).touch();(gate/'armed').unlink();child.wait(timeout=5);assert child.returncode!=0
            keep('cli/'+item['key']+'.stdout',out.read_bytes());keep('cli/'+item['key']+'.stderr',err.read_bytes());write_json('workers/'+token+'.json',worker);write_json('supervision/'+token+'.json',json.loads((lease.parent/token/'supervision.json').read_bytes()))
            before=raw_state();cli(*retry_args(item,{'capture_id':target['capture_id'],'expected_attempt_id':token,'expected_version':1,'expected_processing_version':1}),success=False);assert raw_state()==before
            ref=item['initial']['ref']
            bodies=[('/documents/read',{'reference':ref,'view':'text'}),('/documents/original',{'reference':ref})]+[('/documents/read',{'reference':ref,'view':'table','table_id':t['table_id']}) for t in item['initial']['tables']]
            for path,body in bodies:
                before_read=raw_state()
                r=server.client.post(server.prefix+path,json={**server.context,**body});assert r.status_code==400,r.text
                assert raw_state()==before_read==before
            assert all(not waiting_for_owned_exit(s) for s in tree)
            current=entry(control)['retry_target'];(gate/'armed').write_text(control['sha256'],encoding='utf-8')
            control_argv=cli_prefix+list(map(str,retry_args(control,current)));control_out=server.root/(token+'-control.stdout');control_err=server.root/(token+'-control.stderr')
            with control_out.open('wb') as stdout,control_err.open('wb') as stderr:
                next_child=subprocess.Popen(control_argv,cwd=server.root,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            next_stamp=spawn_identity(psutil.Process(next_child.pid));controllers.append((next_child,next_stamp));until=time.monotonic()+15;next_worker=None
            while time.monotonic()<until and next_child.poll() is None:
                for p in gate.glob('*.json'):
                    value=json.loads(p.read_bytes())
                    if value['sha256']==control['sha256'] and value['token'] not in seen_tokens:next_worker=value;break
                if next_worker:break
                time.sleep(.01)
            assert next_worker is not None and next_worker['token']!=current['expected_attempt_id'],{'exit':next_child.poll(),'stderr':control_err.read_text(encoding='utf-8')}
            seen_tokens.add(next_worker['token']);next_tree=owned_task_tree(next_worker,next_child);observed_trees.append(next_tree)
            next_lease=json.loads(lease.read_bytes());assert next_lease['token']==next_worker['token'] and next_lease['worker']=={'pid':next_worker['pid'],'created':next_worker['created']}
            (gate/(next_worker['token']+'.release')).touch();next_child.wait(timeout=35);assert next_child.returncode==0,control_err.read_text(encoding='utf-8');(gate/'armed').unlink()
            result=json.loads(control_out.read_bytes());assert result['latest_attempt']['attempt_id']==next_worker['token'] and result['latest_attempt']['capture_id']==current['capture_id'] and result['latest_attempt']['status']=='ready'
            assert not lease.exists() and all(not waiting_for_owned_exit(s) for s in next_tree)
            keep('cli/'+token+'-control.stdout',control_out.read_bytes());keep('cli/'+token+'-control.stderr',control_err.read_bytes());write_json('workers/'+next_worker['token']+'.json',next_worker)
            assert snapshot(control,control_snapshot['ref'])['text']==control_snapshot['text']
            assert not (gate/'source-opens.jsonl').exists()
            observe('active-source-last-removed',{'owner':owner,'document_id':item['id'],'project':item['project']['id'],'before_status':item['status'],'target':target,'worker':worker,'tree':tree,'seconds_to_terminal_and_slot':elapsed,'terminal':terminal,'control_attempt':result['latest_attempt'],'old_requests_rejected':len(bodies)+1,'source_reopens':0})
    finally:
        original=sys.exception();cleanup_errors=[]
        (gate/'abort').touch()
        def save_gate(stage):
            for path in gate.iterdir():
                if path.is_file() and path.suffix in {'.json','.jsonl'}:keep('gate-'+stage+'/'+owner+'/'+path.name,path.read_bytes())
            audit=server.root/'cli-audit.jsonl'
            if audit.exists():keep('gate-'+stage+'/'+owner+'/cli-audit.jsonl',audit.read_bytes())
            write_json('gate-'+stage+'/'+owner+'/observed-trees.json',observed_trees)
            preserve_diagnostics(server.root,'active-source-'+stage)
        try:save_gate('before-cleanup')
        except Exception as error:cleanup_errors.append('evidence: '+str(error))
        for child,stamp in controllers:
            try:
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:terminate_verified(process_tree(stamp),owner=child)
            except Exception as error:cleanup_errors.append('controller: '+str(error))
        try:server.stop()
        except Exception as error:cleanup_errors.append('server: '+str(error))
        try:save_gate('after-cleanup')
        except Exception as error:cleanup_errors.append('final evidence: '+str(error))
        write_json('gate-finally/'+owner+'/cleanup.json',{'errors':cleanup_errors,'original_error':str(original) if original is not None else None})
        if cleanup_errors:
            if original is not None:original.add_note('cleanup incomplete: '+str(cleanup_errors))
            else:raise AssertionError(cleanup_errors)

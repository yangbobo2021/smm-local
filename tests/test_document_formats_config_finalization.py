"""A stale post-processing result must end as failed, not wait forever."""
import hashlib,json,os,re,sqlite3,subprocess,sys,time
import psutil
from pathlib import Path
from uuid import uuid4
import pytest
from document_helpers import ROOT,observe
from document_formats_platform import utf8_environment,spawn_identity,process_tree,terminate_verified
from document_formats_partial_fixture import partial_pdf
from test_document_formats_management import native_input
from test_document_formats_installed_minimum import assert_complete_source_text
from test_document_formats_retry import ENGINE,DATA,FONT,keep
from test_document_formats_upload_restart import Server


@pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real creator OCR assets')
@pytest.mark.parametrize('owner',['local','hub'])
@pytest.mark.parametrize('entry_mode',['upload','cache'])
def test_configuration_changed_after_processing_has_terminal_failure_and_saved_byte_retry(tmp_path,owner,entry_mode,monkeypatch):
    # TC-008-postprocess-config-finalization; no source cancellation/restart claim.
    server=Server(tmp_path/owner,owner)
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    gate=server.root/'publication-gate';gate.mkdir();monkeypatch.setenv('SMM_008_PUBLICATION_GATE',str(gate))
    for key in ('SMM_008_WEB_PROCESSING_GATE','SMM_008_WEB_READ_ONLY'):monkeypatch.delenv(key,raising=False)
    (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\nfrom document_formats_publication_hook import install\ninstall()\n',encoding='utf-8')
    cli_prefix=([sys.executable,'-B','-m','smm_local.cli','--db',str(server.db)] if owner=='local' else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(server.root)])+['documents']
    env=utf8_environment(os.environ,PYTHONPATH=os.pathsep.join([str(server.hooks),str(ROOT/'tests'),str(ROOT/'src')]),SMM_008_RESTART_AUDIT=str(server.root/'cli-audit.jsonl'))
    items=[];completed=[];children=[]
    def save(name,value):keep('config-finalization/'+entry_mode+'/'+owner+'/'+name,json.dumps(value,ensure_ascii=False,indent=2).encode())
    def cli(*args,success=True):
        p=subprocess.run(cli_prefix+list(map(str,args)),cwd=server.root,env=env,capture_output=True,timeout=40);tag=uuid4().hex
        keep('config-finalization/'+entry_mode+'/'+owner+'/cli/'+tag+'.stdout',p.stdout);keep('config-finalization/'+entry_mode+'/'+owner+'/cli/'+tag+'.stderr',p.stderr)
        assert (p.returncode==0) if success else p.returncode!=0,p.stderr
        return json.loads(p.stdout) if success else p
    def configure():
        current=cli('processing-status')['config']['revision']
        p=cli('processing-configure','--expected-revision',current,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng' if current%2==0 else 'eng+chi_sim')
        assert p['config']['revision']==current+1 and p['ocr']['ready'] is True
        return current+1
    def library():return server.call('GET','/documents/library').json()
    def entry(item):return next(e for e in library() if e['id']==item['id'])
    def material(status,key):
        if status=='ready':
            raw,t=native_input('docx',key);t['ordered_groups']=[[key+'Before',key+'Inserted',key+'After']];return raw,t
        raw,t=partial_pdf(key,FONT);return raw,{'words':[t['anchor']],'excluded':[],'tables':[],'reason':t['known_failure']}
    def upload(item,v,update=False):
        raw,truth=item['versions'][v];keep('config-finalization/'+entry_mode+'/'+owner+'/inputs/'+item['key']+str(v)+'.'+item['format'],raw);save('truth/'+item['key']+str(v)+'.json',truth)
        p=item['project'];body={**server.context,'project_id':p['id'],'project_key':p['stable_key'] if owner=='local' else p['source_key'],'submission_id':item['key']+str(v),'name':item['key']+'.'+item['format'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if update:
            current=entry(item);body.update(document_id=item['id'],expected_version=current['version'],expected_processing_version=current['processing_version'],expected_revision=current['source_revision'],capture_id=current['latest_attempt']['capture_id'],expected_attempt_id=current['latest_attempt']['attempt_id'])
        begin=server.call('POST','/documents/uploads',body).json()
        for index,offset in enumerate(range(0,len(raw),begin['block_bytes'])):
            part=raw[offset:offset+begin['block_bytes']];server.call('PUT','/documents/uploads/'+begin['upload_id']+'/parts/'+str(index),raw=part,headers={'X-Chunk-SHA256':hashlib.sha256(part).hexdigest()})
        result=server.call('POST','/documents/uploads/'+begin['upload_id']+'/commit',server.context).json()
        if update:assert result['document_id']==item['id']
        else:item['id']=result['document_id']
        return result
    def published(item,receipt,v,p):
        until=time.monotonic()+30
        while time.monotonic()<until:
            e=entry(item);pub=e['published_snapshot'];attempt=e['latest_attempt']
            if pub and pub['capture_id']==receipt['capture_id'] and attempt['attempt_id']==receipt['attempt_id'] and attempt['status']==item['status'] and (e['version'],e['processing_version'])==(v,p) and not e['publication_pending']:return e
            time.sleep(.03)
        raise AssertionError({'phase':'publication not reached','entry':e,'receipt':receipt})
    def full(item,v,reference=None):
        e=entry(item);raw,truth=item['versions'][v];ref=reference or e['original_reference'];body={**server.context,'reference':ref}
        value=server.call('POST','/documents/read',{**body,'start':0,'end':e['text_length']}).json()
        assert value['id']==item['id'] and value['sha256']==hashlib.sha256(raw).hexdigest() and value['processing_status']==item['status']
        assert_complete_source_text(value['text'],truth);assert all(x not in value['text'] for x in truth['excluded'])
        assert len(value['tables'])==len(truth['tables']);views=[];matched=set()
        for table in value['tables']:
            view=server.call('POST','/documents/read',{**body,'view':'table','table_id':table['table_id'],'row_start':1,'row_end':table['rows']+1,'column_start':1,'column_end':table['columns']+1}).json();views.append(view)
            cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in view['cells']]
            matches=[i for i,t in enumerate(truth['tables']) if (view['rows'],view['columns'])==(t['rows'],t['columns']) and len(cells)==len(t['cells']) and set(cells)==set(t['cells']) and all(view['location'].get(k)==v for k,v in t['location'].items())]
            assert len(matches)==1 and matches[0] not in matched;matched.add(matches[0])
        if item['status']=='partial':assert any(e['page']==2 and truth['reason']['reason_contains'] in e['reason'] for e in value['coverage']['errors'])
        original=server.call('POST','/documents/original',body).content;assert original==raw;keep('config-finalization/'+entry_mode+'/'+owner+'/downloads/'+hashlib.sha256(raw).hexdigest(),original)
        hits=server.call('POST','/documents/search',{**server.context,'query':truth['words'][0].split()[0],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results'];assert [h['id'] for h in hits]==[item['id']]
        return {'reference':ref,'text':value['text'],'tables':views,'coverage':value['coverage'],'sha256':value['sha256'],'version':value['version'],'processing_version':value['processing_version']}
    def job(item):
        with sqlite3.connect(server.db) as c:
            c.row_factory=sqlite3.Row;row=c.execute('SELECT state,error,payload FROM document_upload_jobs WHERE document_id=?',(item['id'],)).fetchone();return dict(row)
    def business_state():
        with sqlite3.connect(server.db) as c:
            c.row_factory=sqlite3.Row
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%')")]
            return {name:sorted([dict(r) for r in c.execute('SELECT * FROM "'+name+'"')],key=lambda x:json.dumps(x,sort_keys=True,default=str)) for name in names}
    def retry_args(item,target):
        return ['reprocess','--document-id',item['id']]+[x for k in ('capture_id','expected_attempt_id','expected_version','expected_processing_version') for x in ('--'+k.replace('_','-'),target[k])]
    def others(current):
        assert full(control,1,control['saved']['reference'])==control['saved'] and entry(control)==control['entry']
        for other in items:
            if other is current:continue
            if 'saved' in other:
                assert full(other,other['v'],other['saved']['reference'])==other['saved'] and entry(other)==other['entry']
            elif 'old' in other:
                assert full(other,1,other['old']['reference'])==other['old'] and entry(other)==other['old_entry']
    def wait_gate(item,raw,attempt=None,child=None,stamp=None):
        until=time.monotonic()+25
        while time.monotonic()<until:
            for marker in gate.glob('*.json'):
                m=json.loads(marker.read_bytes())
                if m['raw_sha256']!=hashlib.sha256(raw).hexdigest() or (gate/(m['attempt_id']+'.release')).exists() or (attempt and m['attempt_id']!=attempt):continue
                if child is None or owner=='hub':
                    assert m['pid']==server.serving_stamp['pid'] and m['created']==server.serving_stamp['created']
                    assert m['argv']==server.serving_stamp['argv']
                else:
                    tree=process_tree(stamp);assert any(v['pid']==m['pid'] and v['created']==m['created'] for v in tree)
                    assert m['argv'][1:]==child.args[1:]
                result=(server.root/'.document-snapshots/results'/m['result_sha256']).read_bytes();assert hashlib.sha256(result).hexdigest()==m['result_sha256']
                decoded=json.loads(result);assert decoded['raw_sha256']==m['raw_sha256'] and decoded['status']==m['result_status'] and decoded['profile']==m['profile']
                keep('config-finalization/'+entry_mode+'/'+owner+'/results/'+m['result_sha256']+'.json',result);save('gates/'+m['attempt_id']+'.json',m)
                return m
            time.sleep(.02)
        raise AssertionError('real processing did not reach result gate')
    def release(m):
        (gate/(m['attempt_id']+'.release')).touch();(gate/'armed').unlink()
    def failed_job(item):
        until=time.monotonic()+20
        while True:
            failed=job(item)
            if failed['state']!='pending':break
            assert time.monotonic()<until,'queue failed to finalize';time.sleep(.02)
        assert failed['state']=='failed' and failed['error'];return failed
    try:
        server.start();configure()
        projects=([server.call('POST','/projects',{'name':'finalize ordinary'}).json(),server.call('POST','/projects/global').json()] if owner=='local' else [server.call('POST','/projects',{**server.context,'name':'finalize '+kind,'kind':kind}).json() for kind in ('ordinary','global')])
        control={'key':owner+'finalizecontrol','project':projects[0],'format':'docx','status':'ready'};control['versions']={1:material('ready',control['key'])};receipt=upload(control,1);published(control,receipt,1,1);control['saved']=full(control,1);control['entry']=entry(control);save('control.json',control['saved'])
        for group,p in enumerate(projects):
            for before in ('none','ready','partial'):
                for index in (1,2):
                    key=owner+'finalize'+str(group)+before+str(index);status='partial' if before=='partial' else 'ready'
                    item={'key':key,'project':p,'before':before,'status':status,'format':'pdf' if status=='partial' else 'docx','versions':{v:material(status,key+'v'+str(v)) for v in (1,2)}};items.append(item)
                    if before!='none':
                        old=upload(item,1);published(item,old,1,1);item['old']=full(item,1);item['old_entry']=entry(item)
        for item in items:
            v=1 if entry_mode=='cache' or item['before']=='none' else 2;raw,truth=item['versions'][v];child=None
            if entry_mode=='cache':
                # A first failed-but-legally-captured original is prepared through
                # a real stale-config upload, not by writing product metadata.
                if item['before']=='none':
                    (gate/'armed').write_text(hashlib.sha256(raw).hexdigest(),encoding='utf-8');first=upload(item,1);initial=wait_gate(item,raw,first['attempt_id'])
                    configure();others(item);release(initial);failed_job(item)
                else:configure();others(item)
                target=entry(item)['retry_target'];argv=cli_prefix+list(map(str,retry_args(item,target)));(gate/'armed').write_text(hashlib.sha256(raw).hexdigest(),encoding='utf-8')
                out=server.root/(item['key']+'.stdout');err=server.root/(item['key']+'.stderr')
                with out.open('wb') as a,err.open('wb') as b:child=subprocess.Popen(argv,cwd=server.root,env=env,stdout=a,stderr=b,start_new_session=os.name!='nt')
                stamp=spawn_identity(psutil.Process(child.pid));children.append((child,stamp));m=wait_gate(item,raw,child=child,stamp=stamp);receipt={'capture_id':m['capture_id'],'attempt_id':m['attempt_id']};assert m['capture_id']==target['capture_id'] and m['attempt_id']!=target['expected_attempt_id']
            else:
                (gate/'armed').write_text(hashlib.sha256(raw).hexdigest(),encoding='utf-8');receipt=upload(item,v,item['before']!='none');m=wait_gate(item,raw,receipt['attempt_id'])
            assert m['capture_id']==receipt['capture_id'] and m['result_status']==item['status'];assert entry(item)['publication_pending'] is True
            revision=configure();assert revision==m['config_revision']+1;others(item);release(m)
            if child is None:failed=failed_job(item)
            else:
                child.wait(timeout=30);keep('config-finalization/'+entry_mode+'/'+owner+'/cli/'+item['key']+'.stdout',out.read_bytes());keep('config-finalization/'+entry_mode+'/'+owner+'/cli/'+item['key']+'.stderr',err.read_bytes());assert child.returncode!=0 and re.search(r'配置|发布|config|publish|revision|失效',err.read_text(encoding='utf-8'),re.I);failed={'cli_exit':child.returncode,'stderr':err.read_text(encoding='utf-8')}
            current=entry(item);save('finalized/'+receipt['attempt_id']+'.json',{'failure':failed,'entry':current,'marker':m,'current_config_revision':revision})
            latest=current['latest_attempt'];assert latest['attempt_id']==receipt['attempt_id'] and latest['status']=='failed' and isinstance(latest['error'],str) and latest['error'].strip()
            assert re.search(r'配置|发布|config|publish|revision|失效',latest['error'],re.I)
            assert current['publication_pending'] is False
            assert (current['version'],current['processing_version'])==((0,0) if item['before']=='none' else (1,1))
            if item['before']=='none':assert current['published_snapshot'] is None and not current['original_available']
            else:assert full(item,1,item['old']['reference'])==item['old']
            others(item);target=current['retry_target'];assert target['capture_id']==receipt['capture_id'] and target['expected_attempt_id']==receipt['attempt_id']
            Path(current['path']).unlink();args=retry_args(item,target);cli(*args);new=entry(item)
            assert new['latest_attempt']['capture_id']==receipt['capture_id'] and new['latest_attempt']['attempt_id']!=receipt['attempt_id'] and new['latest_attempt']['config_revision']==revision
            expected=(1,1) if item['before']=='none' else (1,2) if entry_mode=='cache' else (2,2)
            assert (new['version'],new['processing_version'])==expected and new['latest_attempt']['status']==item['status'] and not new['publication_pending']
            item['saved']=full(item,v);item['v']=v;item['entry']=entry(item);completed.append(item)
            before_state=business_state();before_entries=library();rejected=cli(*args,success=False)
            assert re.search(r'过期|撤销|stale|expired|撤回|不一致',rejected.stderr.decode('utf-8'),re.I)
            assert business_state()==before_state and library()==before_entries
            save('stale-rejected/'+receipt['attempt_id']+'.json',{'state_sha256':hashlib.sha256(json.dumps(before_state,sort_keys=True,default=str).encode()).hexdigest(),'unchanged':True,'exit':rejected.returncode})
            if item['before']!='none':
                old=item['old'];requests=[('/documents/read',{}),('/documents/read',{'view':'original-info'}),('/documents/original',{})]+[('/documents/read',{'view':'table','table_id':t['table_id']}) for t in old['tables']]
                for path,fields in requests:
                    response=server.client.post(server.prefix+path,json={**server.context,'reference':old['reference'],**fields});observe('config-finalization-oldref-rejected',{'owner':owner,'id':item['id'],'path':path,'fields':fields,'status':response.status_code});assert response.status_code==400,response.text
            others(item);assert full(item,v,item['saved']['reference'])==item['saved']
        rows=library();assert len(rows)==len({e['id'] for e in rows})==13
        assert {e['id'] for e in rows}=={i['id'] for i in items}|{control['id']}
    finally:
        (gate/'abort').touch()
        for child,stamp in children:
            if child.poll() is None:
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:terminate_verified(process_tree(stamp),owner=child)
        server.stop()

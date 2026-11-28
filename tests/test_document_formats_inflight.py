"""Real CLI cached reprocessing preserves qualified old snapshots while paused."""
import hashlib
from itertools import count
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest
import psutil
from document_formats_platform import spawn_identity,process_tree,same_existing_path
from document_helpers import Fixture, observe, deny_source_reads
from document_formats_fixtures import docx_fixture
from document_formats_partial_fixture import partial_pdf
from document_formats_inflight_observer import install
from document_formats_sync_observer import install as query_guard
from test_document_formats_retry import ENGINE, DATA, FONT, cli, keep
from test_document_formats_cli import saved_state, assert_read_identity

DOWNLOADS=count(1)


def assert_original_metadata(value,hit,raw,source_id,format,archive):
    assert value['id']==hit['id'] and value['version']==hit['version'] and value['processing_version']==hit['processing_version']
    assert value['sha256']==hashlib.sha256(raw).hexdigest()==hit['sha256'] and value['bytes']==len(raw)
    assert value['format']==format and value['available'] is True and value.get('reason') is None
    assert value['origin']=={'device_id':archive,'archive_id':archive,'document_id':hit['id']}
    assert value['source_ids']==[source_id] and value['archive_scope']=='local'


def assert_terminal(attempt,request,target,revision,status):
    assert attempt['attempt_id']==request['task_token']
    assert attempt['capture_id']==target['capture_id'] and attempt['config_revision']==revision
    assert attempt['status']==status and attempt['error'] is None
    assert isinstance(attempt['finished_at'],str) and attempt['finished_at']


def test_inflight_metadata_and_terminal_oracles_reject_other_targets():
    import copy
    archive='a'*32;source_id='b'*32;raws=[b'first original',b'second original']
    for index,format in enumerate(('docx','pdf')):
        raw=raws[index];hit={'id':str(index)*32,'version':1,'processing_version':2,'sha256':hashlib.sha256(raw).hexdigest()}
        good={**hit,'bytes':len(raw),'format':format,'available':True,'reason':None,'origin':{'device_id':archive,'archive_id':archive,'document_id':hit['id']},'source_ids':[source_id],'archive_scope':'local'}
        assert_original_metadata(good,hit,raw,source_id,format,archive)
        for field,bad in [('id','x'*32),('version',2),('processing_version',1),('sha256',hashlib.sha256(raws[1-index]).hexdigest()),('bytes',0),('format','xlsx'),('available',False),('reason','failed'),('origin',{}),('source_ids',[]),('archive_scope','hub')]:
            with pytest.raises(AssertionError):assert_original_metadata({**good,field:bad},hit,raw,source_id,format,archive)
    request={'task_token':'c'*32};target={'capture_id':'d'*32}
    for status in ('ready','partial'):
        good={'attempt_id':request['task_token'],'capture_id':target['capture_id'],'config_revision':2,'status':status,'error':None,'finished_at':'2026-11-25T00:00:00+00:00'}
        assert_terminal(good,request,target,2,status)
        for field,bad in [('attempt_id','old'),('capture_id','other'),('config_revision',1),('status','processing'),('error','failure'),('finished_at',None)]:
            with pytest.raises(AssertionError):assert_terminal({**good,field:bad},request,target,2,status)


def complete_snapshot(f, hit, raw, source_id, format):
    read=f.read(hit,start=0,end=hit['text_length'])
    tables={table['table_id']:f.read(hit,view='table',table_id=table['table_id']) for table in read['tables']}
    info=f.read(hit,view='original-info')
    with f.db.connect() as con:archive=json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    assert_original_metadata(info,hit,raw,source_id,format,archive)
    assert read['id']==hit['id'] and read['version']==hit['version'] and read['processing_version']==hit['processing_version']
    assert read['sha256']==hit['sha256']==hashlib.sha256(raw).hexdigest()
    assert read['origin']==info['origin'] and read['source_ids']==[source_id] and read['format']==format
    response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
    assert response.status_code==200
    keep('downloads/'+str(next(DOWNLOADS))+'-'+hit['id']+'-P'+str(hit['processing_version']),response.content)
    observe('cached-snapshot-read',{'hit':hit,'read':read,'tables':tables,'info':info,'raw_sha256':hashlib.sha256(response.content).hexdigest(),'raw_bytes':len(response.content)})
    return {'read':read,'tables':tables,'info':info,'raw':response.content}


def assert_snapshot(f, item, expected):
    hits=f.search(item['anchor'],scope='project',project_id=item['project'],local=True,limit=50)['results']
    own=[hit for hit in hits if hit['id']==item['hit']['id']]
    assert len(own)==1
    current=own[0]
    assert (current['version'],current['processing_version'],current['sha256'],current['result_sha256'])==(item['hit']['version'],item['hit']['processing_version'],item['hit']['sha256'],item['hit']['result_sha256'])
    value=complete_snapshot(f,item['hit'],item['raw'],item['source_id'],item['path'].suffix[1:])
    assert value==expected
    assert value['raw']==item['raw'] and hashlib.sha256(value['raw']).hexdigest()==current['sha256']
    return current


def test_inflight_source_audit_has_known_controls(tmp_path):
    original=tmp_path/'protected.docx';original.write_bytes(b'protected input')
    env,entered,release,reads=install(tmp_path/'hook',[original])
    positive=subprocess.run([sys.executable,'-c','print("cache-hook-ready")'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert positive.returncode==0 and positive.stdout.strip()=='cache-hook-ready' and not reads.exists() and not entered.exists()
    negative=subprocess.run([sys.executable,'-c','from pathlib import Path;Path('+repr(str(original))+').read_bytes()'],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
    assert negative.returncode!=0 and 'inflight source must not reopen' in negative.stderr
    events=[json.loads(line) for line in reads.read_text().splitlines()]
    assert len(events)==1 and events[0]['kind']=='source-open' and Path(events[0]['path'])==original
    observe('inflight-source-audit-controls',{'positive_exit':positive.returncode,'negative_exit':negative.returncode,'events':events})


@pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real creator assets')
def test_cached_reprocess_keeps_old_views_for_ready_and_partial(tmp_path,monkeypatch):
    # TC-008-cached-inflight
    f=Fixture(tmp_path/'archive');project=f.project('Cached inflight');control_project=f.project('Unrelated control')
    status=cli(f,'processing-status')
    configured=cli(f,'processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    first_revision=configured['config']['revision'];items={}
    for key in ('alpha','beta'):
        for kind in ('ready','partial'):
            name='cached'+kind+key
            if kind=='ready':
                raw,truth=docx_fixture(name);extension='docx';anchor=truth['words'][0]
            else:
                raw,truth=partial_pdf(name,FONT);extension='pdf';anchor=truth['anchor']
            path=f.file(name+'.'+extension,raw=raw)
            items[path.name]={'path':path,'raw':raw,'truth':truth,'anchor':anchor,'status':kind,'project':project}
            keep('inputs/'+path.name,raw)
            keep('truth/'+path.name+'.json',json.dumps(truth,ensure_ascii=False,default=lambda v:sorted(v) if isinstance(v,set) else str(v)).encode())
    source=f.add(f.root/'docs',[project]);f.refresh(source)
    for name,item in items.items():
        hits=f.search(item['anchor'],scope='project',project_id=project,local=True,limit=50)['results']
        own=[hit for hit in hits if Path(hit['path']).name==name];assert len(own)==1
        item['hit']=own[0];item['source_id']=source['id'];item['snapshot']=complete_snapshot(f,item['hit'],item['raw'],source['id'],item['path'].suffix[1:])
        assert item['hit']['version']==item['hit']['processing_version']==1
        assert item['snapshot']['read']['processing_status']==item['status']
        if item['status']=='ready':
            assert all(item['snapshot']['read']['text'].count(word)==1 for word in item['truth']['words'])
            assert len(item['snapshot']['tables'])==3
        else:
            assert item['snapshot']['read']['text']==item['anchor']
            assert any(error['page']==2 and '1600万像素' in error['reason'] for error in item['snapshot']['read']['coverage']['errors'])
        assert item['snapshot']['raw']==item['raw']
    control_raw,control_truth=docx_fixture('cachedcontrol')
    control_path=f.file('control.docx',raw=control_raw);control_source=f.add(control_path,[control_project]);f.refresh(control_source)
    control_hit=f.search(control_truth['words'][0],scope='project',project_id=control_project,local=True,limit=50)['results'][0]
    control={'path':control_path,'raw':control_raw,'truth':control_truth,'anchor':control_truth['words'][0],'status':'ready','project':control_project,'hit':control_hit}
    control['source_id']=control_source['id'];control['snapshot']=complete_snapshot(f,control_hit,control_raw,control_source['id'],'docx')
    for item in [*items.values(),control]:item['path'].unlink()
    configured=cli(f,'processing-configure','--expected-revision',first_revision,'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    second_revision=configured['config']['revision'];assert second_revision==first_revision+1
    all_items={**items,'control':control};completed=set()
    for number,(name,item) in enumerate(items.items()):
        entries={entry['id']:entry for entry in f.files(source)};entry=entries[item['hit']['id']];target=entry['retry_target']
        assert target is not None and target['expected_version']==target['expected_processing_version']==1
        env,entered,release,reads=install(tmp_path/('attempt-'+str(number)),[value['path'] for value in all_items.values()])
        command=[sys.executable,'-B','-m','smm_local.cli','--db',str(f.db.db_path),'documents','reprocess','--document-id',entry['id']]
        for field in ('capture_id','expected_attempt_id','expected_version','expected_processing_version'):
            command+=['--'+field.replace('_','-'),str(target[field])]
        process=subprocess.Popen(command,env=env,cwd=f.root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',start_new_session=os.name!='nt')
        launcher=spawn_identity(psutil.Process(process.pid))
        stdout=stderr=''
        try:
            deadline=time.monotonic()+20
            while not entered.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
            assert entered.exists(),{'exit':process.poll(),'phase':'CLI never reached actual supervisor barrier'}
            request=json.loads(entered.read_text())
            members=process_tree(launcher)
            worker=next(p for p in members if p['pid']==request['pid'] and p['created']==request['created'])
            assert request['argv']==worker['argv'] and request['argv'][1:]==command[1:]
            assert same_existing_path(request['exe'],worker['exe'])
            assert any(same_existing_path(request['exe'],p) for p in (sys.executable,getattr(sys,'_base_executable',sys.executable),psutil.Process().exe()))
            assert request['raw_sha256']==entry['sha256']
            assert Path(request['raw']).name==entry['sha256'] and not any(Path(request['raw'])==value['path'] for value in all_items.values())
            during={value['id']:value for value in f.files(source)}[entry['id']]
            assert during['published_snapshot']==entry['published_snapshot']
            assert during['latest_attempt']['capture_id']==target['capture_id']
            assert during['latest_attempt']['attempt_id']==request['task_token']!=target['expected_attempt_id']
            assert during['latest_attempt']['config_revision']==second_revision and during['latest_attempt']['status']=='processing'
            with monkeypatch.context() as guard:
                attempts=query_guard(guard)
                source_reads=deny_source_reads(guard,*[value['path'] for value in all_items.values()])
                before=saved_state(f)
                for other_name,other in all_items.items():
                    assert_snapshot(f,other,other['snapshot'])
                assert saved_state(f)==before and attempts==[] and source_reads==[]
                assert process.poll() is None
                observe('cached-inflight-'+name,{'request':request,'published':during['published_snapshot'],'latest_attempt':during['latest_attempt'],'targets':sorted(value['hit']['id'] for value in all_items.values()),'query_state_unchanged':True,'processing_attempts':attempts,'source_reads':source_reads})
        finally:
            release.write_text('release')
            try:stdout,stderr=process.communicate(timeout=45)
            except subprocess.TimeoutExpired:
                if os.name!='nt':os.killpg(process.pid,signal.SIGTERM)
                else:process.kill()
                stdout,stderr=process.communicate(timeout=10)
            observe('cached-reprocess-cli-'+name,{'argv':command,'exit_code':process.returncode,'stdout':stdout,'stderr':stderr,'source_events':reads.read_text() if reads.exists() else ''})
        assert process.returncode==0,stderr
        answer=json.loads(stdout);assert answer['document_id']==entry['id'] and answer['processing_version']==2
        assert_terminal(answer['latest_attempt'],request,target,second_revision,item['status'])
        finished={value['id']:value for value in f.files(source)}[entry['id']]
        assert_terminal(finished['latest_attempt'],request,target,second_revision,item['status'])
        assert finished['latest_attempt']==answer['latest_attempt']
        assert not reads.exists() or reads.read_text()==''
        for view in ('text','original-info'):
            response=f.client.post('/api/documents/read',json={'reference':item['hit']['reference'],'view':view})
            assert response.status_code==400
        for table_id in item['snapshot']['tables']:
            response=f.client.post('/api/documents/read',json={'reference':item['hit']['reference'],'view':'table','table_id':table_id})
            assert response.status_code==400
        assert f.client.post('/api/documents/original',json={'reference':item['hit']['reference']}).status_code==400
        own=[hit for hit in f.search(item['anchor'],scope='project',project_id=project,local=True,limit=50)['results'] if hit['id']==entry['id']];assert len(own)==1
        item['hit']=own[0];updated=complete_snapshot(f,item['hit'],item['raw'],item['source_id'],item['path'].suffix[1:])
        assert item['hit']['version']==1 and item['hit']['processing_version']==2
        assert updated['read']['processing_status']==item['status'] and updated['read']['text']==item['snapshot']['read']['text']
        assert updated['read']['profile']['config_revision']==second_revision
        assert updated['raw']==item['raw'] and updated['read']['result_sha256']!=item['snapshot']['read']['result_sha256']
        assert updated['read']['locations']==item['snapshot']['read']['locations'] and updated['read']['coverage']==item['snapshot']['read']['coverage']
        assert updated['read']['tables']==item['snapshot']['read']['tables'] and set(updated['tables'])==set(item['snapshot']['tables'])
        for table in updated['read']['tables']:
            table_id=table['table_id'];view=updated['tables'][table_id];old_view=item['snapshot']['tables'][table_id]
            assert_read_identity(view,updated['read'],updated['read']['origin'],source['id'])
            assert all(view[key]==value for key,value in table.items())
            for field in ('cells','window','header_context','window_origin'):assert view[field]==old_view[field]
        item['snapshot']=updated;completed.add(entry['id'])
        for other in all_items.values():assert_snapshot(f,other,other['snapshot'])
        keep('completed-originals/'+name,updated['raw'])
    assert len(completed)==4 and control['hit']['processing_version']==1

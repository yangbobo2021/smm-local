"""Real creator/watchdog failure; isolated archives and independently owned IDs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

import psutil
from document_formats_exit_observer import waiting_for_owned_exit
import pytest

from document_helpers import observe
from document_formats_health_hook import write,DESCENDANT
from document_formats_health_fixture import partial_with_table
from document_formats_platform import matching_process,same_existing_path,process_identity
from test_document_formats_management import Creator,native_input
from test_document_formats_upload_restart import Server
from test_document_formats_retry import keep
from test_document_formats_installed_minimum import assert_complete_source_text
from smm_local.core import Archive
from smm_local import references


class SocketCreator(Creator):
    def __init__(self,server):
        self.server=server;self.owner=server.owner;self.db=Archive(server.db)
        self.w=SimpleNamespace(root=server.root,device=references.material(self.db)[0])
        self.client=server.client;self.prefix=server.prefix;self.context=server.context;self.items=[]
        if self.owner=='local':
            self.projects=[self.request('POST','/projects',{'name':'health ordinary'}).json(),
                           self.request('POST','/projects/global').json()]
        else:
            self.projects=[self.request('POST','/projects',{**self.context,'name':'health '+kind,'kind':kind}).json()
                           for kind in ('ordinary','global')]


    def upload(self,item,raw,comparison=None):
        uid,receipt,entry=super().upload(item,raw,comparison)
        # Extraction status precedes the atomic published snapshot.
        entry=await_state(self,{'id':receipt['document_id']},entry['latest_attempt']['status'])
        return uid,receipt,entry

    def entries(self):
        # Separate HTTP requests may straddle a background state transition.
        files=self.request('GET','/documents/files').json()
        library=self.request('GET','/documents/library').json()
        assert len(files)==len({e['id'] for e in files})
        assert len(library)==len({e['id'] for e in library})
        assert {e['id'] for e in files}=={e['id'] for e in library}
        return {e['id']:e for e in library}


def capture(client,item,raw):
    body={**client.project(item['project']),'name':item['name'],'bytes':len(raw),
          'sha256':hashlib.sha256(raw).hexdigest(),'submission_id':uuid4().hex}
    if 'id' in item:body.update(document_id=item['id'],**client.comparison(client.entries()[item['id']]))
    start=client.request('POST','/documents/uploads',body).json();uid=start['upload_id']
    for index,offset in enumerate(range(0,len(raw),start['block_bytes'])):
        part=raw[offset:offset+start['block_bytes']]
        client.request('PUT','/documents/uploads/'+uid+'/parts/'+str(index),raw=part,
                       headers={'X-Chunk-SHA256':hashlib.sha256(part).hexdigest()})
    receipt=client.request('POST','/documents/uploads/'+uid+'/commit',client.context).json()
    item['id']=receipt['document_id'];return receipt


def await_state(client,item,status,seconds=15):
    deadline=time.monotonic()+seconds
    while True:
        entry=client.entries()[item['id']]
        if entry['latest_attempt']['status']==status:
            if status not in {'ready','partial','empty-success'}:return entry
            published=entry['published_snapshot']
            if (not entry.get('publication_pending') and published
                    and published['capture_id']==entry['latest_attempt']['capture_id']
                    and published['status']==status and entry['version']==published['version']>0
                    and entry['processing_version']==published['processing_version']>0):return entry
        assert time.monotonic()<deadline,{'expected':status,'entry':entry}
        time.sleep(.01)


def snapshot(client,item):
    entry=client.entries()[item['id']];version=item['version'];status=item['status']
    file_state(client,item,entry)
    assert entry['version']==entry['processing_version']==version
    assert entry['published_snapshot']['status']==status
    ref=entry['original_reference'];assert ref
    value=client.request('POST','/documents/read',{**client.context,'reference':ref,'start':0,'end':entry['text_length']}).json()
    assert value['id']==item['id'] and value['version']==value['processing_version']==version
    assert value['processing_status']==status and value['sha256']==hashlib.sha256(item['raw']).hexdigest()
    assert_complete_source_text(value['text'],{**item['truth'],'ordered_groups':[item['truth']['words']]})
    tables=[client.request('POST','/documents/read',{**client.context,'reference':ref,'view':'table',
            'table_id':t['table_id'],'row_start':1,'row_end':t['rows']+1,
            'column_start':1,'column_end':t['columns']+1}).json() for t in value['tables']]
    assert len(value['tables'])==len(item['truth']['tables'])
    for expected in item['truth']['tables']:
        own=[t for t in tables if all(t['location'].get(k)==v for k,v in expected['location'].items())
             and any(c['text']==expected['cells'][0][2] for c in t['cells'])]
        assert len(own)==1
        table=own[0]
        cells=[(c['row'],c['column'],c['text'],c['row_span'],c['column_span']) for c in table['cells']]
        assert (table['rows'],table['columns'])==(expected['rows'],expected['columns'])
        assert len(cells)==len(expected['cells']) and set(cells)==set(expected['cells'])
    raw=client.request('POST','/documents/original',{**client.context,'reference':ref}).content
    assert raw==item['raw'];keep('health-originals/'+hashlib.sha256(raw).hexdigest()+'.pdf',raw)
    info=client.request('POST','/documents/read',{**client.context,'reference':ref,'view':'original-info'}).json()
    assert info['sha256']==hashlib.sha256(raw).hexdigest() and info['bytes']==len(raw) and info['available']
    hits=client.request('POST','/documents/search',{**client.context,'query':item['truth']['words'][0],
         'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if client.owner=='local' else {})}).json()['results']
    own=[h for h in hits if h['id']==item['id']];assert len(own)==1
    assert own[0]['version']==own[0]['processing_version']==version and own[0]['sha256']==info['sha256']
    return {'published':entry['published_snapshot'],'reference':ref,'read':value,'tables':tables,'info':info}


def file_state(client,item,expected):
    # Called after a terminal barrier or while the real worker gate holds state.
    rows=client.request('GET','/documents/files').json()
    own=[row for row in rows if row['id']==item['id']];assert len(own)==1
    for key in ('latest_attempt','retry_target','published_snapshot','version','processing_version'):
        assert own[0][key]==expected[key],{'field':key,'files':own[0],'expected':expected}


def preserved(client,item):
    saved=item['saved'];assert snapshot(client,item)==saved
    reference=saved['reference']
    value=client.request('POST','/documents/read',{**client.context,'reference':reference,
          'start':0,'end':len(saved['read']['text'])}).json()
    assert value==saved['read']
    for table in saved['tables']:
        view=client.request('POST','/documents/read',{**client.context,'reference':reference,'view':'table',
             'table_id':table['table_id'],'row_start':1,'row_end':table['rows']+1,
             'column_start':1,'column_end':table['columns']+1}).json()
        assert view==table
    raw=client.request('POST','/documents/original',{**client.context,'reference':reference}).content
    assert raw==item['raw']
    assert client.request('POST','/documents/read',{**client.context,'reference':reference,
           'view':'original-info'}).json()==saved['info']


def text_preserved(client,item):
    client.assert_text(item)
    value=client.request('POST','/documents/read',{**client.context,'reference':item['old_reference'],
          'start':0,'end':len(item['text'])}).json()
    assert value['id']==item['id'] and value['text']==item['text']


def wait_json(path,seconds=8):
    deadline=time.monotonic()+seconds
    while not path.exists():
        assert time.monotonic()<deadline,str(path)
        time.sleep(.005)
    return json.loads(path.read_text(encoding='utf-8'))


def enroll(control,receipt,nonce,server):
    token=receipt['attempt_id'];worker=wait_json(control/('worker-ready-'+token+'.json'))
    assert worker['token']==token and worker['nonce']==nonce
    stamps=[]
    records=[('worker',worker['worker']),('descendant',worker['descendant'])]
    for index in range(3):
        if index==2:
            live=wait_json(control/('watch-live-'+token+'.json'))
            assert live['token']==token and live['nonce']==nonce
            records.append(('watcher',live['watcher']))
        key,record=records[index]
        process=psutil.Process(record['pid']);actual=process_identity(process)
        assert actual['created']==record['created'] and actual['argv']==record['argv']
        assert same_existing_path(actual['exe'],record['exe']) and same_existing_path(process.cwd(),record['cwd'])
        assert same_existing_path(actual['exe'],psutil.Process().exe())
        assert process.status()!=psutil.STATUS_ZOMBIE
        assert token in actual['argv'] or key=='watcher' and str(Path(worker['directory'])/'supervision.json') in actual['argv']
        assert same_existing_path(process.cwd(),worker['directory'])
        expected_parent=worker['worker']['pid'] if key=='descendant' else server.serving_stamp['pid']
        assert process.ppid()==expected_parent
        stamps.append({'kind':key,**actual})
        # Register each verified historical member before further assertions/faults.
        remembered={(v['pid'],v['created']):v for v in server.known_tree}
        remembered[(actual['pid'],actual['created'])]=actual
        server.known_tree=list(remembered.values())
    handshake=worker['descendant_handshake']
    assert handshake['stdin_eof_observed'] and handshake['token']==token and handshake['nonce']==nonce
    assert worker['descendant_requested_argv'][1:]==['-B','-c',DESCENDANT,
           str(control/('descendant-started-'+token+'.json')),str(control),token,nonce]
    descendant=next(v for v in stamps if v['kind']=='descendant')
    assert descendant['argv'][1:]==worker['descendant_requested_argv'][1:]
    worker_process=psutil.Process(worker['worker']['pid']);watcher=psutil.Process(live['watcher']['pid'])
    assert worker_process.ppid()==watcher.ppid()==server.serving_stamp['pid']
    assert psutil.Process(worker['descendant']['pid']).ppid()==worker_process.pid
    state=json.loads((Path(worker['directory'])/'supervision.json').read_text())
    assert state['token']==token and state['worker']=={k:worker['worker'][k] for k in ('pid','created')}
    assert state['controller']=={k:server.serving_stamp[k] for k in ('pid','created')}
    assert Path(worker['payload']).read_bytes()==b'owned temporary processing payload 008'
    observe('health-owned-enrollment',{'receipt':receipt,'nonce':nonce,'worker':worker,'watch_live':live,'stamps':stamps,'supervision':state})
    return worker,stamps


def released(stamps):
    rows=[]
    for record in stamps:
        stamp={k:record[k] for k in ('pid','created','argv','exe')}
        assert matching_process(stamp) is None,record
        try:state=psutil.Process(stamp['pid']).status()
        except psutil.NoSuchProcess:state='absent'
        assert state in {'absent',psutil.STATUS_ZOMBIE}
        rows.append({'identity':record,'state':state})
    return rows


@pytest.mark.skipif(os.name=='nt',reason='POSIX independent-watchdog component; Windows Job acceptance is separate')
@pytest.mark.parametrize('owner',['local','hub'])
def test_live_content_task_fails_when_independent_watchdog_exits(tmp_path,monkeypatch,owner):
    # TC-008-watchdog-health. Production budgets, task responses and identities are real.
    root=tmp_path/owner;control=tmp_path/'health-control';control.mkdir()
    monkeypatch.setenv('SMM_008_HEALTH_CONTROL',str(control))
    server=Server(root,owner)
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    (server.hooks/'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\nfrom document_formats_health_hook import install\ninstall()\n',encoding='utf-8')
    try:
        server.start();client=SocketCreator(server)
        unrelated=client.request('POST','/projects',{**client.context,'name':'unrelated health',**({'kind':'ordinary'} if owner=='hub' else {})}).json()
        client.projects.append(unrelated);text_controls=client.text_controls();client.projects.pop()
        for text in text_controls:
            hits=client.request('POST','/documents/search',{**client.context,'query':text['text'],
                 'scope':'project','project_id':text['project']['id'],'limit':50,
                 **({'local':True} if owner=='local' else {})}).json()['results']
            own=[h for h in hits if h['id']==text['id']];assert len(own)==1
            text['old_reference']=own[0]['reference'];text_preserved(client,text)
        unrelated_pdf=client.add('pdf','Unrelated'+owner[0],unrelated);unrelated_pdf['version']=1
        unrelated_pdf['saved']=snapshot(client,unrelated_pdf)
        protected=[unrelated_pdf];targets=[]
        for group,project in enumerate(client.projects):
            for before in ('none','ready','partial'):
                for index in range(2):
                    key=owner+'health'+str(group)+before+str(index)
                    if before=='ready':
                        item=client.add('pdf',key,project);item['version']=1
                    elif before=='partial':
                        raw,truth=partial_with_table(owner[0]+'P'+str(group)+str(index))
                        item={'name':key+'.pdf','project':project,'format':'pdf','raw':raw,'truth':truth,'status':'partial','version':1}
                        capture(client,item,raw);await_state(client,item,'partial')
                    else:item={'name':key+'.pdf','project':project,'format':'pdf','version':0}
                    item.update(before=before,mode='denial' if index==0 else 'exit0')
                    if before!='none':item['saved']=snapshot(client,item);protected.append(item)
                    targets.append(item)
        assert len(targets)==12 and len({i['name'] for i in targets})==12
        # Normal pass-through with the very same real worker/watch gate.
        normal={'name':owner+'healthnormal.pdf','project':client.projects[0],'format':'pdf','version':1,'status':'ready'}
        normal['raw'],normal['truth']=native_input('pdf',owner+'HealthNormal')
        nonce=uuid4().hex;write(control/'arm.json',{'nonce':nonce})
        receipt=capture(client,normal,normal['raw']);worker,stamps=enroll(control,receipt,nonce,server)
        (control/'arm.json').unlink();(control/('release-'+receipt['attempt_id'])).touch()
        await_state(client,normal,'ready');exited=wait_json(control/('watch-exit-'+receipt['attempt_id']+'.json'))
        assert exited['actual_returncode']==0
        normal['saved']=snapshot(client,normal);protected.append(normal)
        observe('health-normal-control',{'receipt':receipt,'exit':exited,'members':released(stamps)})
        for item in targets:
            raw,truth=native_input('pdf','H'+uuid4().hex[:8])
            keep('health-inputs/'+hashlib.sha256(raw).hexdigest()+'.pdf',raw)
            nonce=uuid4().hex;write(control/'arm.json',{'nonce':nonce})
            receipt=capture(client,item,raw);token=receipt['attempt_id'];worker,stamps=enroll(control,receipt,nonce,server)
            current=client.entries()[item['id']]
            assert current['latest_attempt']['status']=='processing' and current['latest_attempt']['attempt_id']==token
            file_state(client,item,current)
            step=0
            for text in text_controls:
                write(control/('preparing-'+token+'.json'),{'token':token,'nonce':nonce,'step':step});step+=1
                text_preserved(client,text)
            for existing in protected:
                write(control/('preparing-'+token+'.json'),{'token':token,'nonce':nonce,'step':step});step+=1
                preserved(client,existing)
            assert not (control/('gate-timeout-'+token+'.json')).exists()
            assert all(matching_process({k:stamp[k] for k in ('pid','created','argv','exe')}) is not None for stamp in stamps)
            write(control/('fault-'+token+'.json'),{'nonce':nonce,'token':token,'mode':item['mode']})
            fault=wait_json(control/('fault-observed-'+token+'.json'))
            assert fault['token']==token and fault['mode']==item['mode'] and fault['non_target_original_unchanged']
            watcher=next(v for v in stamps if v['kind']=='watcher');deadline=time.monotonic()+2
            while waiting_for_owned_exit({k:watcher[k] for k in ('pid','created','argv','exe')}):
                assert time.monotonic()<deadline,'watchdog fault did not actually exit'
                time.sleep(.005)
            died=time.monotonic();entry=await_state(client,item,'failed',seconds=5)
            file_state(client,item,entry)
            assert entry['latest_attempt']['finished_at'] and entry['latest_attempt']['attempt_id']==token
            error=entry['latest_attempt']['error'];assert isinstance(error,str) and ('监督' in error or 'watchdog' in error.lower()),error
            assert not error.startswith('原生解析失败'),error
            root_task=Path(worker['directory']);observations=released(stamps)
            assert not (root_task.parent/'active.json').exists() and not Path(worker['payload']).exists()
            failure_elapsed=time.monotonic()-died
            assert failure_elapsed<=5
            assert entry['version']==entry['processing_version']==item['version']
            assert (entry['published_snapshot'] is None)==(item['before']=='none')
            target=entry['retry_target'];assert target['capture_id']==receipt['capture_id'] and target['expected_attempt_id']==token
            assert target['sha256']==hashlib.sha256(raw).hexdigest()
            assert (root/'.document-snapshots/raw'/target['sha256']).read_bytes()==raw
            for existing in protected:preserved(client,existing)
            for text in text_controls:text_preserved(client,text)
            exit_record=wait_json(control/('watch-exit-'+token+'.json'))
            assert exit_record['pid']==watcher['pid'] and exit_record['actual_returncode']==(1 if item['mode']=='denial' else 0)
            observe('health-failed-and-reclaimed',{'name':item['name'],'before':item['before'],'receipt':receipt,'entry':entry,
                    'fault':fault,'exit':exit_record,'members':observations,'five_second_elapsed':failure_elapsed})
            (control/'arm.json').unlink()
            with client.db.connect() as connection:
                failed_attempt=dict(connection.execute('SELECT * FROM document_processing_attempts WHERE id=?',(token,)).fetchone())
            argv=([sys.executable,'-B','-m','smm_local.cli','--db',str(server.db),'documents'] if owner=='local'
                  else [sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(root),'documents'])+['reprocess','--document-id',item['id']]
            for key in ('capture_id','expected_attempt_id','expected_version','expected_processing_version'):argv+=['--'+key.replace('_','-'),str(target[key])]
            result=subprocess.run(argv,capture_output=True,encoding='utf-8',timeout=20)
            observe('health-explicit-retry',{'argv':argv,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
            assert result.returncode==0,result.stderr
            item.update(raw=raw,truth=truth,status='ready',version=item['version']+1)
            retried=await_state(client,item,'ready')
            assert retried['latest_attempt']['capture_id']==receipt['capture_id']
            assert retried['latest_attempt']['attempt_id']!=token and retried['latest_attempt']['finished_at']
            with client.db.connect() as connection:
                assert dict(connection.execute('SELECT * FROM document_processing_attempts WHERE id=?',(token,)).fetchone())==failed_attempt
            observe('health-retry-identity',{'saved_capture_id':receipt['capture_id'],'failed_attempt':failed_attempt,
                    'new_attempt':retried['latest_attempt']})
            item['saved']=snapshot(client,item)
            if item not in protected:protected.append(item)
            follow={'name':uuid4().hex+'.pdf','project':item['project'],'format':'pdf','version':1,'status':'ready'}
            follow['raw'],follow['truth']=native_input('pdf','Next'+uuid4().hex[:8])
            capture(client,follow,follow['raw']);await_state(client,follow,'ready');snapshot(client,follow)
            observe('health-following-service-task',{'after':token,'document_id':follow['id'],'same_service':server.serving_stamp})
    finally:
        original=sys.exception();cleanup_errors=[]
        (control/'release-all').touch()
        try:
            stopped=server.stop();observe('health-server-final-cleanup',stopped)
        except BaseException as error:
            cleanup_errors.append({'stage':'server','type':type(error).__name__,'error':str(error)})
        try:observe('health-historical-members-final',{'members':released(server.known_tree)})
        except BaseException as error:
            cleanup_errors.append({'stage':'historical members','type':type(error).__name__,'error':str(error)})
        observe('health-cleanup-result',{'errors':cleanup_errors,'original_error':str(original) if original else None})
        for path in sorted(control.glob('*.json')):keep('health-process/'+path.name,path.read_bytes())
        if cleanup_errors and original is None:raise AssertionError(cleanup_errors)

"""C1 expansion of current-update replay; legacy helper module stays immutable."""
import hashlib,json,os,sqlite3,time
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from io import BytesIO
import pytest
from document_formats_fixtures import package,W,R,REL,CT
from document_helpers import observe
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server


from test_document_formats_update_replay import material,state,settle

def test_update_replay_materials_have_independent_full_source_truth():
    hashes=set()
    for owner in ('local','hub'):
        for key in ('alpha','beta','gamma','delta'):
            for version in (1,2,3):
                raw,truth=material(owner,key,version)
                with ZipFile(BytesIO(raw)) as archive:
                    assert archive.testzip() is None
                    root=ET.fromstring(archive.read('word/document.xml'));ns={'w':W}
                    assert '\n'.join(n.text or '' for n in root.findall('.//w:t',ns))==truth['text']
                    rows=root.findall('./w:body/w:tbl/w:tr',ns);assert len(rows)==1
                    assert [n.text for n in rows[0].findall('./w:tc/w:p/w:r/w:t',ns)]==truth['cells']
                assert truth['sha256'] not in hashes;hashes.add(truth['sha256'])
    assert len(hashes)==24
    observe('update-replay-source-controls',{'distinct_originals':24,'full_xml_text_and_two_cells_independently_checked':True})


@pytest.mark.parametrize('owner',['local','hub'])
def test_committed_update_can_reopen_own_identity_but_not_supersede_newer_state(tmp_path,owner,monkeypatch):
    # TC-008-managed-update-replay; no browser/SC1-upload claim.
    monkeypatch.delenv('SMM_008_WEB_READ_ONLY',raising=False)
    gate=tmp_path/'release';gate.touch();monkeypatch.setenv('SMM_008_WEB_PROCESSING_GATE',str(gate))
    server=Server(tmp_path/owner,owner);items=[]
    def bad(method,path,body=None,raw=None):
        kwargs={'json':body} if body is not None else {'content':raw,'headers':{'X-Chunk-SHA256':hashlib.sha256(raw).hexdigest()}}
        r=server.client.request(method,server.prefix+path,**kwargs)
        observe('update-replay-rejected',{'owner':owner,'method':method,'path':path,'request':body,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw else None,'status':r.status_code,'response':r.json()})
        assert 400<=r.status_code<500,r.text
    def entry(item):
        return next(e for e in server.call('GET','/documents/library').json() if e['id']==item['id'])
    def body(item,version,update=False):
        raw,truth=item['materials'][version]
        value={**server.context,'project_id':item['project']['id'],'project_key':item['project']['stable_key'] if owner=='local' else item['project']['source_key'],'submission_id':owner+item['key']+'v'+str(version),'name':item['key']+'.docx','bytes':len(raw),'sha256':truth['sha256']}
        if update:
            current=entry(item)
            value.update(document_id=item['id'],expected_version=current['version'],expected_processing_version=current['processing_version'],expected_revision=current['source_revision'],capture_id=current['latest_attempt']['capture_id'],expected_attempt_id=current['latest_attempt']['attempt_id'])
        return value
    def send(payload,raw):
        started=server.call('POST','/documents/uploads',payload).json()
        for n,offset in enumerate(range(0,len(raw),started['block_bytes'])):
            chunk=raw[offset:offset+started['block_bytes']]
            server.call('PUT','/documents/uploads/'+started['upload_id']+'/parts/'+str(n),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
        committed=server.call('POST','/documents/uploads/'+started['upload_id']+'/commit',server.context).json()
        return started,committed
    def verify(item):
        raw,truth=item['materials'][item['version']]
        hits=server.call('POST','/documents/search',{**server.context,'scope':'project','project_id':item['project']['id'],'query':truth['anchor'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
        assert [h['id'] for h in hits]==[item['id']]
        other=global_project if item['project']['id']==ordinary['id'] else ordinary
        assert server.call('POST','/documents/search',{**server.context,'scope':'project','project_id':other['id'],'query':truth['anchor'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']==[]
        with sqlite3.connect(server.db) as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        expected_origin={'device_id':archive if owner=='local' else server.context['hub_id'],'archive_id':archive,'document_id':item['id']}
        h=hits[0];assert h['origin']==expected_origin and h['version']==h['processing_version']==item['version'] and h['sha256']==truth['sha256'] and h['text_length']==len(truth['text'])
        value=server.call('POST','/documents/read',{**server.context,'reference':h['reference'],'start':0,'end':len(truth['text'])}).json()
        assert value['id']==item['id'] and value['origin']==expected_origin and value['version']==value['processing_version']==item['version'] and value['text']==truth['text'] and value['sha256']==truth['sha256']
        assert len(value['tables'])==1
        table=server.call('POST','/documents/read',{**server.context,'reference':h['reference'],'view':'table','table_id':value['tables'][0]['table_id']}).json()
        assert table['id']==item['id'] and table['origin']==expected_origin and table['version']==table['processing_version']==item['version']
        assert table['location']=={'part':'word/document.xml','path':'body/table[1]'} and (table['rows'],table['columns'])==(1,2)
        assert [(c['row'],c['column'],c['row_span'],c['column_span'],c['text']) for c in table['cells']]==[(1,n,1,1,text) for n,text in enumerate(truth['cells'],1)]
        response=server.call('POST','/documents/original',{**server.context,'reference':h['reference']});assert response.content==raw
        keep('downloads/'+truth['sha256']+'.docx',response.content)
        return h['reference']
    def replay(item,payload,started,receipt,status):
        before=state(server)
        resumed=server.call('POST','/documents/uploads',payload).json()
        count=(payload['bytes']+started['block_bytes']-1)//started['block_bytes']
        assert resumed=={'upload_id':started['upload_id'],'block_bytes':started['block_bytes'],'received_parts':list(range(count)),'committed':True}
        raw=item['materials'][2][0];chunk=raw[:started['block_bytes']]
        same=server.call('PUT','/documents/uploads/'+started['upload_id']+'/parts/0',raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()}).json()
        assert same==resumed
        changed=bytes([chunk[0]^1])+chunk[1:];bad('PUT','/documents/uploads/'+started['upload_id']+'/parts/0',raw=changed)
        repeated=server.call('POST','/documents/uploads/'+started['upload_id']+'/commit',server.context).json()
        assert repeated['document_id']==item['id'] and repeated['capture_id']==receipt['capture_id'] and repeated['attempt_id']==receipt['attempt_id'] and repeated['status']==status
        assert repeated['version']==repeated['processing_version']==(1 if status=='pending' else 2)
        assert state(server)==before
        observe('update-replay-current',{'owner':owner,'id':item['id'],'phase':status,'before':before,'after':state(server),'resumed':resumed,'receipt':repeated})
    def reject_old(item):
        before=state(server);payload=item['v2payload'];uid=item['v2started']['upload_id'];raw=item['materials'][2][0]
        bad('POST','/documents/uploads',payload);bad('PUT','/documents/uploads/'+uid+'/parts/0',raw=raw[:item['v2started']['block_bytes']]);bad('POST','/documents/uploads/'+uid+'/commit',server.context)
        assert state(server)==before
        observe('update-replay-old-rejected',{'owner':owner,'id':item['id'],'phase':item['version'],'before':before,'after':state(server)})
    try:
        server.start()
        ordinary=server.call('POST','/projects',{'name':'update replay'} if owner=='local' else {**server.context,'name':'update replay','kind':'ordinary'}).json()
        global_project=server.call('POST','/projects/global').json() if owner=='local' else server.call('POST','/projects',{**server.context,'name':'global replay','kind':'global'}).json()
        for key,project in (('alpha',ordinary),('beta',ordinary),('gamma',global_project),('delta',global_project)):
            item={'key':key,'project':project,'version':1,'materials':{v:material(owner,key,v) for v in (1,2,3)}}
            for version,(raw,truth) in item['materials'].items():
                keep('inputs/'+owner+key+str(version)+'.docx',raw);keep('truth/'+owner+key+str(version)+'.json',json.dumps(truth,ensure_ascii=False).encode())
            _,receipt=send(body(item,1),item['materials'][1][0]);item['id']=receipt['document_id'];items.append(item)
        settle(server,gate);assert len({i['id'] for i in items})==4
        rows=server.call('GET','/documents/library').json();assert {e['id'] for e in rows}=={i['id'] for i in items}
        for project in (ordinary,global_project):
            own={i['id'] for i in items if i['project']['id']==project['id']};assert len(own)==2
            assert {e['id'] for e in rows if project['id'] in e['project_ids']}==own
        for item in items:
            assert entry(item)['latest_attempt']['status']=='ready';item['v1ref']=verify(item)
        for item in items:
            gate.unlink()
            payload=body(item,2,update=True);started,receipt=send(payload,item['materials'][2][0])
            item.update(v2payload=payload,v2started=started)
            assert receipt['document_id']==item['id'] and receipt['status']=='pending'
            current=entry(item);assert current['version']==current['processing_version']==1 and current['latest_attempt']['capture_id']==receipt['capture_id'] and current['latest_attempt']['attempt_id']==receipt['attempt_id'] and current['latest_attempt']['status']=='pending'
            until=time.monotonic()+5
            while True:
                events=[json.loads(l) for l in Path(str(gate)+'.events').read_text().splitlines()]
                if sum(e['event']=='enter' for e in events)>sum(e['event']=='exit' for e in events):break
                assert time.monotonic()<until,events;time.sleep(.02)
            assert all(e['pid']==server.serving_pid for e in events)
            observe('update-replay-pending-gate',{'owner':owner,'id':item['id'],'events':events,'server_pid':server.serving_pid})
            replay(item,payload,started,receipt,'pending')
            for target in items:verify(target)
            gate.touch();settle(server,gate);item['version']=2
            assert entry(item)['latest_attempt']['status']=='ready'
            replay(item,payload,started,receipt,'ready')
            for target in items:verify(target)
            before=state(server);bad('POST','/documents/uploads',{**payload,'sha256':'0'*64});assert state(server)==before
            bad('POST','/documents/read',{**server.context,'reference':item['v1ref']})
            _,next_receipt=send(body(item,3,update=True),item['materials'][3][0]);assert next_receipt['capture_id']!=receipt['capture_id'] and next_receipt['attempt_id']!=receipt['attempt_id']
            settle(server,gate);item['version']=3;reject_old(item)
            for target in items:verify(target)
        for item in items:
            current=entry(item);payload={**server.context,'project_id':item['project']['id'],'project_key':item['project']['stable_key'] if owner=='local' else item['project']['source_key'],'expected_version':3,'expected_processing_version':3,'expected_revision':current['source_revision'],'capture_id':current['latest_attempt']['capture_id'],'expected_attempt_id':current['latest_attempt']['attempt_id']}
            server.call('DELETE','/documents/library/'+item['id'],payload);reject_old(item)
            assert item['id'] not in {e['id'] for e in server.call('GET','/documents/library').json()}
        observe('update-replay-all-complete',{'owner':owner,'document_ids':[i['id'] for i in items],'states':['own pending','own ready','changed data','superseded','removed']})
    finally:
        gate.touch()
        try:
            if server.process is not None:settle(server,gate)
        finally:
            if Path(str(gate)+'.events').exists():keep('gates/'+owner+'.jsonl',Path(str(gate)+'.events').read_bytes())
            stopped=server.stop()
            if stopped is not None:assert stopped['forced'] is False

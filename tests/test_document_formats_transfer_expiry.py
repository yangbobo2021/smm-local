"""Expired raw promises reclaim quota without deleting live or committed bytes."""
import gzip,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import pytest
from document_helpers import observe
from test_document_formats_retry import keep
from test_document_formats_management import Creator
from test_hub_documents_contracts import w
from smm_local.document_snapshots import Snapshots

MIB=1024*1024
CAPACITY=256*MIB
CORPUS=Path(__file__).parent/'fixtures'/'document-format-objects'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def counts(actor):
    with actor.db.connect() as c:
        return {t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('documents','document_captures','document_processing_attempts','document_upload_jobs')}


@pytest.mark.parametrize('owner',['local','hub'])
def test_expired_raw_promises_release_exclusive_bytes_and_keep_current(w,owner):
    # TC-008-transfer-expiry-raw. Real API; only task-owned persisted clock input is aged.
    actor=Creator(w,owner);snapshots=Snapshots(actor.db);bad=[];pool=[]
    def call(method,path,body=None,raw=None):
        kwargs={'json':body} if raw is None else {'content':raw,'headers':{'X-Chunk-SHA256':sha(raw)}}
        r=actor.client.request(method,actor.prefix+path,**kwargs)
        observe('expiry-raw-http',{'owner':owner,'method':method,'path':path,'body':body,'status':r.status_code,'response':r.json(),'raw_bytes':len(raw) if raw is not None else None,'raw_sha256':sha(raw) if raw is not None else None})
        return r
    def expect(r,accepted,label):
        ok=r.status_code==200 if accepted else 400<=r.status_code<500
        if not ok:bad.append({'label':label,'status':r.status_code,'response':r.json()})
        return r.json() if r.status_code==200 else None
    def body(project,key,size,digest):
        return {**actor.project(project),'submission_id':owner+key,'name':key+'.docx','bytes':size,'sha256':digest}
    def promise(project,key,raw,declared=None):
        b=body(project,key,len(raw) if declared is None else declared,sha(raw))
        value=call('POST','/documents/uploads',b);assert value.status_code==200,value.text
        return {'body':b,'uid':value.json()['upload_id']}
    def chunk(item,index,raw):
        r=call('PUT','/documents/uploads/'+item['uid']+'/parts/'+str(index),raw=raw)
        assert r.status_code==200,r.text
    def protected(project,name,status):
        raw=(CORPUS/name).read_bytes();keep('inputs/'+owner+'-'+name,raw)
        item={'project':project,'name':name};uid,receipt,e=actor.upload(item,raw)
        assert e['latest_attempt']['status']==status and e['retry_target'] is not None
        assert (snapshots.root/'raw'/sha(raw)).read_bytes()==raw
        return {'uid':uid,'receipt':receipt,'entry':e,'raw':raw}
    published=protected(actor.projects[0],'ordinarytextdocx.docx','ready')
    candidate=protected(actor.projects[1],'globalbodydocx.docx','failed')
    assert candidate['entry']['published_snapshot'] is None
    reference=published['entry']['original_reference']
    published_read=actor.request('POST','/documents/read',{**actor.context,'reference':reference,'start':0,'end':published['entry']['text_length']}).json()
    truth=next(i for i in json.loads((CORPUS/'manifest.json').read_text())['items'] if i['file']=='ordinarytextdocx.docx')
    assert published_read['text']==truth['text']
    hits=actor.request('POST','/documents/search',{**actor.context,'query':truth['text'].split()[0],'scope':'project','project_id':actor.projects[0]['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
    assert [h['id'] for h in hits]==[published['entry']['id']]
    before_counts=counts(actor);assert before_counts['documents']==before_counts['document_captures']==before_counts['document_processing_attempts']==2
    assert snapshots._unpublished_bytes()==len(candidate['raw'])
    # No parsing/commit claim for these large synthetic byte promises.
    poisoned=[(CORPUS/(p+'blankdocx.docx')).read_bytes() for p in ('ordinary','global')]
    for i in range(13):
        size=20*MIB if i<12 else 16*MIB-len(candidate['raw'])
        key='promise'+str(i);prefix=(owner+key).encode()+b'\0'
        raw=prefix+b'\0'*(size-len(prefix)) if i<11 else poisoned[i-11]
        if i<11:
            zipped=gzip.compress(raw);assert gzip.decompress(zipped)==raw
            keep('inputs/'+owner+key+'.bin.gz',zipped)
        else:keep('inputs/'+owner+key+'.docx',raw)
        keep('truth/'+owner+key+'.json',json.dumps({'actual_bytes':len(raw),'declared_bytes':size,'sha256':sha(raw),'purpose':'uncommitted resource promise; two deliberately wrong length declarations'}).encode())
        item=promise(actor.projects[i%2],key,raw,declared=size);pool.append(item)
        if i==0:chunk(item,0,raw[:MIB]);shared_prefix=raw[:2*MIB]
        if i in (1,2):chunk(item,0,raw[:MIB])
        if i in (3,4):
            for n,offset in enumerate(range(0,len(raw),MIB)):chunk(item,n,raw[offset:offset+MIB])
    assert len(candidate['raw'])+sum(i['body']['bytes'] for i in pool)==CAPACITY
    assert len({i['body']['sha256'] for i in pool})==13
    shared=pool[0];live_body={**shared['body'],'submission_id':owner+'live-alias'}
    live=call('POST','/documents/uploads',live_body);assert live.status_code==200,live.text
    live={'body':live_body,'uid':live.json()['upload_id']}
    assert live['uid']!=shared['uid'] and snapshots._unpublished_bytes()==CAPACITY
    extra=(CORPUS/'globaltextdocx.docx').read_bytes();extra_body=body(actor.projects[0],'extra',len(extra),sha(extra))
    full=call('POST','/documents/uploads',extra_body);assert 400<=full.status_code<500 and '256MiB' in full.text
    def age(uid):
        path=snapshots.root/'transfers'/uid/'state.json';state=json.loads(path.read_bytes());was=state['created_at'];state['created_at']=time.time()-25*3600
        path.write_text(json.dumps(state),encoding='utf-8');keep('aged-states/'+owner+'-'+uid+'.json',path.read_bytes())
        observe('expiry-clock-fixture',{'owner':owner,'uid':uid,'before':was,'after':state['created_at'],'committed':state['committed'],'real_wait':False})
    for item in [*pool,published,candidate]:age(item['uid'])
    # Admission must ignore expired length contracts as well as release quota.
    corrected=[]
    for n,raw in enumerate(poisoned):
        b=body(actor.projects[n],'correct'+str(n),len(raw),sha(raw));corrected.append(b)
        expect(call('POST','/documents/uploads',b),True,'raw-expiry-admission-'+str(n))
    # Shared active incoming survives; all four exclusive expired bodies disappear.
    incoming=snapshots.root/'raw'/('.incoming-'+shared['body']['sha256'])
    assert incoming.read_bytes()==shared_prefix[:MIB]
    for item in pool[1:5]:
        path=snapshots.root/'raw'/('.incoming-'+item['body']['sha256'])
        if path.exists():bad.append({'label':'raw-expiry-exclusive-bytes','uid':item['uid'],'bytes':path.stat().st_size})
    chunk(live,1,shared_prefix[MIB:])
    assert incoming.read_bytes()==shared_prefix
    resumed=call('POST','/documents/uploads',live_body);assert resumed.status_code==200 and resumed.json()['received_parts']==[0,1]
    for item in pool:
        for action,r in [('begin',call('POST','/documents/uploads',item['body'])),('part',call('PUT','/documents/uploads/'+item['uid']+'/parts/0',raw=b'x'*min(MIB,item['body']['bytes']))),('commit',call('POST','/documents/uploads/'+item['uid']+'/commit',actor.context))]:
            expect(r,False,'raw-expiry-replay-'+action)
            if '过期' not in r.text:bad.append({'label':'raw-expiry-clear-rejection','action':action,'response':r.json()})
    # New Python process reopens persisted state; no CLI/network endpoint is invoked.
    program="import sys,json;from smm_local.core import Archive;from smm_local.document_snapshots import Snapshots;from smm_local.document_transfers import BlobTransfers;t=BlobTransfers(Snapshots(Archive(sys.argv[1])),raw_only=True);out=[]\nfor uid in sys.argv[2:]:\n try:t.binding(uid);out.append({'uid':uid,'error':None})\n except ValueError as e:out.append({'uid':uid,'error':str(e)})\nprint(json.dumps(out,ensure_ascii=False))"
    result=subprocess.run([sys.executable,'-B','-c',program,str(actor.db.db_path),*[i['uid'] for i in pool]],capture_output=True,text=True,encoding='utf-8',check=True)
    reopened=json.loads(result.stdout);assert len(reopened)==13 and all('过期' in (i['error'] or '') for i in reopened)
    observe('expiry-reopen-process',{'owner':owner,'stdout':reopened,'stderr':result.stderr,'exit_code':result.returncode})
    current=actor.entries()
    assert set(current)=={published['entry']['id'],candidate['entry']['id']}
    for control in (published,candidate):
        assert current[control['entry']['id']]==control['entry']
        assert (snapshots.root/'raw'/sha(control['raw'])).read_bytes()==control['raw']
        replay=actor.request('POST','/documents/uploads/'+control['uid']+'/commit',actor.context).json();assert replay=={**control['receipt'],'status':control['entry']['latest_attempt']['status'],'version':control['entry']['version'],'processing_version':control['entry']['processing_version']}
    assert actor.request('POST','/documents/read',{**actor.context,'reference':reference,'start':0,'end':published['entry']['text_length']}).json()==published_read
    assert actor.request('POST','/documents/original',{**actor.context,'reference':reference}).content==published['raw']
    # Independently refill to the unchanged limit; +1 must be refused again.
    retained=len(candidate['raw'])+shared['body']['bytes']+sum(b['bytes'] for b in corrected)
    remaining=CAPACITY-retained;refills=[];i=0
    while remaining:
        size=min(20*MIB,remaining);key=owner+'refill'+str(i);prefix=key.encode()+b'\0';raw=prefix+b'\0'*(size-len(prefix))
        zipped=gzip.compress(raw);assert gzip.decompress(zipped)==raw;keep('inputs/'+key+'.bin.gz',zipped)
        b=body(actor.projects[i%2],key,size,sha(raw));refills.append(b)
        expect(call('POST','/documents/uploads',b),True,'raw-expiry-refill-'+str(i));remaining-=size;i+=1
    assert retained+sum(b['bytes'] for b in refills)==CAPACITY
    one=body(actor.projects[0],'plusone',1,sha(b'Z'));expect(call('POST','/documents/uploads',one),False,'raw-expiry-refill-plus-one')
    # Reaching/refusing full quota must not evict any protected content.
    assert incoming.read_bytes()==shared_prefix
    assert actor.request('POST','/documents/uploads',live_body).json()['received_parts']==[0,1]
    current=actor.entries()
    for control in (published,candidate):
        assert current[control['entry']['id']]==control['entry']
        assert (snapshots.root/'raw'/sha(control['raw'])).read_bytes()==control['raw']
    assert actor.request('POST','/documents/read',{**actor.context,'reference':reference,'start':0,'end':published['entry']['text_length']}).json()==published_read
    assert actor.request('POST','/documents/original',{**actor.context,'reference':reference}).content==published['raw']
    assert counts(actor)==before_counts
    observe('expiry-raw-complete',{'owner':owner,'errors':bad,'before_counts':before_counts,'after_counts':counts(actor),'retained_expected_bytes':retained,'refill_promised_bytes':sum(b['bytes'] for b in refills),'limit':CAPACITY,'clock_fixture_only':True})
    assert not bad,bad

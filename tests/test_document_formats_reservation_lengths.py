"""Unreceived promises remain bounded under untrusted same-SHA length aliases."""
import gzip,hashlib,json
from pathlib import Path
import pytest
from document_helpers import observe
from test_document_formats_management import Creator
from test_hub_documents_contracts import w
from test_document_formats_update_replay import material
from test_document_formats_retry import keep
from smm_local.document_snapshots import Snapshots

MIB=1024*1024
CAPACITY=256*MIB


def order_members(paths,lengths,large_first):
    return sorted(paths,key=lambda p:(lengths.get(p.name,0),p.name),reverse=large_first)


def test_reservation_directory_order_control_preserves_real_members(tmp_path):
    paths=[]
    for name in ('large','small','unmapped'):
        p=tmp_path/name;p.mkdir();paths.append(p)
    sizes={'large':20*MIB,'small':1}
    one=order_members(list(tmp_path.iterdir()),sizes,True);two=order_members(list(tmp_path.iterdir()),sizes,False)
    assert one[0].name=='large' and two[-1].name=='large' and one!=two
    assert set(one)==set(two)==set(paths)
    observe('reservation-directory-known-control',{'large_first':[p.name for p in one],'small_first':[p.name for p in two],'same_real_members':True})


def stored_state(actor,directory,original_iterdir):
    with actor.db.connect() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%') ORDER BY name")]
        business={}
        for table in tables:
            rows=sorted([list(r) for r in c.execute('SELECT * FROM "'+table+'"')],key=lambda r:json.dumps(r,default=str))
            business[table]=hashlib.sha256(json.dumps(rows,ensure_ascii=False,default=str).encode()).hexdigest()
    transfers={}
    for folder in original_iterdir(directory):
        assert folder.is_dir() and not folder.is_symlink()
        raw=(folder/'state.json').read_bytes();transfers[folder.name]=hashlib.sha256(raw).hexdigest()
    return {'business':business,'transfers':transfers}


@pytest.mark.parametrize('owner',['local','hub'])
def test_same_sha_different_lengths_cannot_shrink_current_reservations(w,owner,monkeypatch):
    # TC-008-reservation-lengths; metadata-only promises, no format acceptance claim.
    actor=Creator(w,owner);snapshots=Snapshots(actor.db);directory=snapshots._directory('transfers')
    original_iterdir=type(directory).iterdir;lengths={};mode={'large_first':True};orders=[]
    def controlled(path):
        actual=list(original_iterdir(path))
        if path==directory:
            selected=order_members(actual,lengths,mode['large_first'])
            assert set(selected)==set(actual) and len(selected)==len(actual)
            record={'mode':'large-first' if mode['large_first'] else 'small-first','members':[p.name for p in actual],'order':[p.name for p in selected]}
            orders.append(record);observe('reservation-actual-directory-order',record)
            return iter(selected)
        return iter(actual)
    monkeypatch.setattr(type(directory),'iterdir',controlled)
    def request(body,expected):
        response=actor.client.post(actor.prefix+'/documents/uploads',json=body)
        value=response.json();observe('reservation-http',{'owner':owner,'body':body,'status':response.status_code,'response':value})
        if expected=='success':assert response.status_code==200,response.text
        elif expected=='reject':assert 400<=response.status_code<500,response.text
        else:assert response.status_code==200 or 400<=response.status_code<500,response.text
        if response.status_code==200:lengths[value['upload_id']]=body['bytes']
        return response
    def unchanged_rejection(body):
        before=stored_state(actor,directory,original_iterdir);request(body,'reject');after=stored_state(actor,directory,original_iterdir)
        assert after==before
        observe('reservation-rejected-unchanged',{'owner':owner,'before':before,'after':after})
    positive_raw,positive_truth=material(owner,'capacitypositive',1)
    overflow_raw,overflow_truth=material(owner,'capacityoverflow',1)
    for label,raw,truth in [('positive',positive_raw,positive_truth),('overflow',overflow_raw,overflow_truth)]:
        keep('inputs/'+owner+'-'+label+'.docx',raw);keep('truth/'+owner+'-'+label+'.json',json.dumps(truth,ensure_ascii=False).encode())
    positive_body={**actor.project(actor.projects[0]),'submission_id':owner+'Positive','name':'positive.docx','sha256':positive_truth['sha256'],'bytes':len(positive_raw)}
    accepted=request(positive_body,'success').json();positive={'body':positive_body,'upload':accepted['upload_id'],'project':actor.projects[0]}
    assert accepted['received_parts']==[] and accepted['committed'] is False
    pool=[]
    for index in range(13):
        size=20*MIB if index<12 else 16*MIB-len(positive_raw);key=owner+'Promise'+str(index);prefix=key.encode()+b'\0'
        raw=prefix+b'\0'*(size-len(prefix));digest=hashlib.sha256(raw).hexdigest()
        compressed=gzip.compress(raw);assert len(raw)==size and gzip.decompress(compressed)==raw
        keep('inputs/'+key+'.bin.gz',compressed);keep('truth/'+key+'.json',json.dumps({'bytes':size,'sha256':digest,'purpose':'unreceived byte promise; never parsed or committed'},ensure_ascii=False).encode())
        body={**actor.project(actor.projects[index%2]),'submission_id':key,'name':key+'.docx','sha256':digest,'bytes':size}
        started=request(body,'success').json();assert started['received_parts']==[] and started['committed'] is False
        pool.append({'body':body,'upload':started['upload_id'],'project':actor.projects[index%2]})
    assert len(positive_raw)+sum(item['body']['bytes'] for item in pool)==CAPACITY
    assert len({i['body']['sha256'] for i in [positive,*pool]})==14
    for project in actor.projects:assert sum(i['project']['id']==project['id'] for i in pool)>=2
    assert actor.request('GET','/documents/files').json()==[] and actor.request('GET','/documents/library').json()==[]
    def new_valid_promise(tag):
        return {**actor.project(actor.projects[0]),'submission_id':owner+'Extra'+tag,'name':'extra.docx','sha256':overflow_truth['sha256'],'bytes':len(overflow_raw)}
    for flag in (True,False):
        mode['large_first']=flag;unchanged_rejection(new_valid_promise('Before'+str(flag)))
    mode['large_first']=True
    # Dedup at the full limit must still accept a new identical-byte promise.
    for index in (0,1,2,3):
        item=pool[index];same={**item['body'],'submission_id':owner+'Same'+str(index)}
        request(same,'success');unchanged_rejection(new_valid_promise('Same'+str(index)))
    for index in (0,1,2,3):
        item=pool[index];alias={**item['body'],'submission_id':owner+'Short'+str(index),'name':'short.docx','bytes':len(overflow_raw)}
        before=stored_state(actor,directory,original_iterdir);response=request(alias,'conflict-or-safe')
        if response.status_code!=200:assert stored_state(actor,directory,original_iterdir)==before
        # A still-resumable20MiB promise cannot turn into a small raw length.
        for flag in (True,False):
            mode['large_first']=flag
            unchanged_rejection(new_valid_promise('After'+str(index)+str(flag)))
            for original in [positive,*pool]:
                resumed=request(original['body'],'success').json()
                assert resumed['upload_id']==original['upload'] and resumed['received_parts']==[] and resumed['committed'] is False
    with actor.db.connect() as c:
        counts={table:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('documents','document_captures','document_processing_attempts','document_upload_jobs')}
    assert set(counts.values())=={0}
    assert any(r['mode']=='large-first' for r in orders) and any(r['mode']=='small-first' for r in orders)
    observe('reservation-all-complete',{'owner':owner,'promised_bytes':CAPACITY,'unique_promises':14,'source_projects':[p['id'] for p in actor.projects],'bad_aliases':4,'new_unique_valid_body_rejected':True,'no_capture_or_processing':counts})

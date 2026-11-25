"""Native managed updates must reject linked write paths before changing bytes."""
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4
import hashlib,json,os,stat,subprocess,time
import pytest
from document_helpers import observe
from test_hub_documents_contracts import w
from test_document_formats_update_replay import material,state
from test_document_formats_retry import keep


def tree(directory):
    result={};pending=[directory]
    while pending:
        p=pending.pop();info=p.lstat();linked=stat.S_ISLNK(info.st_mode) or bool(getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0))
        kind='link' if linked else 'directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode) else 'other'
        row={'kind':kind,'mode':info.st_mode,'mtime_ns':info.st_mtime_ns,'inode':info.st_ino}
        if linked:row['target']=os.readlink(p)
        elif kind=='file':
            raw=p.read_bytes();row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        elif kind=='directory':pending.extend(p.iterdir())
        result[str(p.relative_to(directory))]=row
    return result


def link_state(path):
    s=path.lstat()
    assert stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0)
    return {'target':os.readlink(path),'mode':s.st_mode,'attributes':getattr(s,'st_file_attributes',None),'inode':s.st_ino}


@contextmanager
def replace_with_link(node,target,kind,evidence):
    backup=node.with_name(node.name+'.acceptance-backup-'+uuid4().hex)
    node.rename(backup)
    made=False
    try:
        if os.name=='nt' and kind!='file':
            r=subprocess.run(['cmd','/c','mklink','/J',str(node),str(target)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10)
            observe('managed-link-junction-create',{'argv':['cmd','/c','mklink','/J',str(node),str(target)],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            assert r.returncode==0,r.stderr
        else:
            try:node.symlink_to(target,target_is_directory=kind!='file')
            except OSError as exc:
                if os.name=='nt' and getattr(exc,'winerror',None)==1314:pytest.skip('actual file symlink privilege unavailable; this branch is unverified, not passed')
                raise
        made=True;before=link_state(node);assert os.path.samefile(node,target)
        observe('managed-link-installed',{**evidence,'node':str(node),'target':str(target),'link':before,'actual_samefile':True})
        yield before
    finally:
        if made:
            try:observed=link_state(node)
            except (AssertionError,OSError):observed={'link_replaced_or_missing':True}
            observe('managed-link-before-restore',{**evidence,'node':str(node),'observed':observed})
            if os.path.lexists(node):
                if os.name=='nt' and kind!='file':node.rmdir()
                else:node.unlink()
        elif os.path.lexists(node):
            # Failed setup may not remove an unrelated ordinary directory.
            raise AssertionError('failed link setup left an unexpected node')
        backup.rename(node)
        observe('managed-link-restored',{**evidence,'node':str(node),'regular_restored':not node.is_symlink() and not (getattr(node.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0))})


@pytest.mark.parametrize('kind',['file','parent','root'])
def test_actual_link_setup_preserves_target_and_restores_regular_path(tmp_path,kind):
    node=tmp_path/'managed';target=tmp_path/'outside'
    if kind=='file':node.write_bytes(b'owned');target.write_bytes(b'external')
    else:node.mkdir();(node/'file').write_bytes(b'owned');target.mkdir();(target/'file').write_bytes(b'external')
    before=(target.read_bytes(),target.stat().st_mtime_ns) if kind=='file' else tree(target)
    with replace_with_link(node,target,kind,{'control':True,'kind':kind}) as info:
        assert info==link_state(node) and os.path.samefile(node,target)
        assert (node.read_bytes() if kind=='file' else (node/'file').read_bytes())==b'external'
    assert (node.read_bytes() if kind=='file' else (node/'file').read_bytes())==b'owned'
    assert ((target.read_bytes(),target.stat().st_mtime_ns) if kind=='file' else tree(target))==before



@pytest.mark.parametrize('member',['empty-directory','dangling-link'])
def test_external_tree_oracle_detects_nonfile_members(tmp_path,member):
    outside=tmp_path/'outside';outside.mkdir();(outside/'original').write_bytes(b'control')
    before=tree(outside);extra=outside/member
    if member=='empty-directory':extra.mkdir()
    else:
        try:extra.symlink_to(outside/'missing-target')
        except OSError as exc:
            if os.name=='nt' and getattr(exc,'winerror',None)==1314:pytest.skip('file symlink privilege unavailable; dangling-link control unverified')
            raise
    after=tree(outside);assert set(after)==set(before)|{member}
    assert after[member]['kind']==('directory' if member=='empty-directory' else 'link')
    if member=='dangling-link':assert after[member]['target']==str(outside/'missing-target') and not extra.exists()
    assert before['original']==after['original'] and before!=after
    observe('managed-external-tree-known-control',{'member':member,'before':before,'after':after,'unexpected_member_detected':True})
    if member=='empty-directory':extra.rmdir()
    else:extra.unlink()

@pytest.mark.parametrize('owner',['local','hub'])
@pytest.mark.parametrize('kind',['file','parent','root'])
def test_native_update_rejects_linked_target_before_external_write(w,tmp_path,owner,kind):
    # TC-008-managed-update-paths: temporary controlled filesystem links only.
    db=w.pair.local if owner=='local' else w.pair.remote
    fake=SimpleNamespace(db=db.db_path)
    client=w.local.client if owner=='local' else w.hub;prefix='/api' if owner=='local' else '/v1';ctx={} if owner=='local' else w.context()
    projects=[w.local.request('POST','/api/projects',{'name':'link ordinary'}),w.local.request('POST','/api/projects/global')] if owner=='local' else [w.hub_project('link ordinary'),w.hub_project('link global',kind='global')]
    items=[]
    def call(method,path,body=None,raw=None,reject=False):
        kw={'json':body} if body is not None else {'content':raw,'headers':{'X-Chunk-SHA256':hashlib.sha256(raw).hexdigest()}} if raw is not None else {}
        r=client.request(method,prefix+path,**kw)
        value=r.json() if 'json' in r.headers.get('content-type','') else {'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()}
        observe('managed-link-http',{'owner':owner,'kind':kind,'method':method,'path':path,'request':body,'raw_sha256':hashlib.sha256(raw).hexdigest() if raw is not None else None,'status':r.status_code,'response':value})
        if not reject:assert r.status_code==200,r.text
        return r
    def listed(item):return next(e for e in call('GET','/documents/library').json() if e['id']==item['id'])
    def wait(item):
        until=time.monotonic()+20
        while True:
            e=listed(item)
            with db.connect() as c:pending=c.execute("SELECT count(*) FROM document_upload_jobs WHERE state='pending'").fetchone()[0]
            if e['latest_attempt']['status']=='ready' and not pending:return e
            assert time.monotonic()<until,e;time.sleep(.03)
    def payload(item,version):
        raw,t=item['materials'][version];p=item['project']
        b={**ctx,'project_id':p['id'],'project_key':p['stable_key'] if owner=='local' else p['source_key'],'submission_id':owner+kind+item['key']+str(version),'name':item['key']+'.docx','sha256':t['sha256'],'bytes':len(raw)}
        if 'id' in item:
            e=listed(item);b.update(document_id=item['id'],expected_version=e['version'],expected_processing_version=e['processing_version'],expected_revision=e['source_revision'],capture_id=e['latest_attempt']['capture_id'],expected_attempt_id=e['latest_attempt']['attempt_id'])
        return b
    def stage(b,raw,allow_reject=False):
        r=call('POST','/documents/uploads',b,reject=allow_reject)
        if r.status_code!=200:return None,r
        s=r.json()
        for n,offset in enumerate(range(0,len(raw),s['block_bytes'])):
            if n in s['received_parts']:continue
            r=call('PUT','/documents/uploads/'+s['upload_id']+'/parts/'+str(n),raw=raw[offset:offset+s['block_bytes']],reject=allow_reject)
            if r.status_code!=200:return s,r
        return s,None
    def verify(item):
        raw,t=item['materials'][item['version']]
        hits=call('POST','/documents/search',{**ctx,'query':t['anchor'],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']
        assert [h['id'] for h in hits]==[item['id']];hit=hits[0]
        other=projects[1] if item['project']['id']==projects[0]['id'] else projects[0]
        assert call('POST','/documents/search',{**ctx,'query':t['anchor'],'scope':'project','project_id':other['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()['results']==[]
        assert hit['version']==hit['processing_version']==item['version'] and hit['sha256']==t['sha256'] and hit['text_length']==len(t['text'])
        value=call('POST','/documents/read',{**ctx,'reference':item['reference'] if item.get('reference_version')==item['version'] else hit['reference'],'start':0,'end':len(t['text'])}).json()
        assert value['id']==item['id'] and value['version']==value['processing_version']==item['version'] and value['text']==t['text'] and value['sha256']==t['sha256'] and value['origin']==hit['origin']
        assert len(value['tables'])==1
        table=call('POST','/documents/read',{**ctx,'reference':hit['reference'],'view':'table','table_id':value['tables'][0]['table_id']}).json()
        assert table['id']==item['id'] and table['version']==table['processing_version']==item['version'] and table['location']=={'part':'word/document.xml','path':'body/table[1]'} and (table['rows'],table['columns'])==(1,2)
        assert [(c['row'],c['column'],c['row_span'],c['column_span'],c['text']) for c in table['cells']]==[(1,n,1,1,text) for n,text in enumerate(t['cells'],1)]
        downloaded=call('POST','/documents/original',{**ctx,'reference':hit['reference']}).content;assert downloaded==raw
        keep('downloads/'+t['sha256']+'.docx',downloaded)
        item.update(reference=hit['reference'],reference_version=item['version'])
    for key,p in (('alpha',projects[0]),('beta',projects[0]),('gamma',projects[1]),('delta',projects[1])):
        item={'key':key,'project':p,'version':1,'materials':{v:material(owner+kind,key,v) for v in (1,2,3)}}
        for v,(raw,t) in item['materials'].items():keep('inputs/'+owner+kind+key+str(v)+'.docx',raw);keep('truth/'+owner+kind+key+str(v)+'.json',json.dumps(t,ensure_ascii=False).encode())
        s,_=stage(payload(item,1),item['materials'][1][0]);r=call('POST','/documents/uploads/'+s['upload_id']+'/commit',ctx).json();item['id']=r['document_id'];items.append(item)
    rows=call('GET','/documents/library').json();assert {e['id'] for e in rows}=={i['id'] for i in items}
    for project in projects:
        own={i['id'] for i in items if i['project']['id']==project['id']};assert len(own)==2
        assert {e['id'] for e in rows if project['id'] in e['project_ids']}==own
    for item in items:wait(item);verify(item)
    for boundary,version in (('prebegin',2),('precommit',3)):
        for item in items:
            b=payload(item,version);raw=item['materials'][version][0];s=None
            if boundary=='precommit':s,_=stage(b,raw)
            current=listed(item);path=Path(current['path']);library=path.parent.parent
            assert path.is_file() and not path.is_symlink() and library.name=='.documents'
            node=path if kind=='file' else path.parent if kind=='parent' else library
            outside=tmp_path/(owner+kind+boundary+item['key']+'-outside');outside.mkdir()
            external=outside/'external.docx' if kind=='file' else outside/'file.docx' if kind=='parent' else outside/path.relative_to(library)
            external.parent.mkdir(parents=True,exist_ok=True);external.write_bytes(('synthetic external '+owner+kind+boundary+item['key']).encode())
            target=external if kind=='file' else outside
            before_external=tree(outside);before_owned=path.read_bytes();before_owned_mtime=path.stat().st_mtime_ns;before_db=state(fake)['tables']
            details={'owner':owner,'kind':kind,'boundary':boundary,'id':item['id']}
            with replace_with_link(node,target,kind,details) as link:
                try:
                    rejected=None
                    if s is None:s,rejected=stage(b,raw,allow_reject=True)
                    if rejected is None:rejected=call('POST','/documents/uploads/'+s['upload_id']+'/commit',ctx,reject=True)
                    assert 400<=rejected.status_code<500,rejected.text
                    assert state(fake)['tables']==before_db
                    assert link_state(node)==link and tree(outside)==before_external
                    for target_item in items:verify(target_item)
                    observe('managed-link-rejected',{**details,'status':rejected.status_code,'db_before':before_db,'db_after':state(fake)['tables'],'external_before':before_external,'external_after':tree(outside),'link_before':link,'link_after':link_state(node)})
                finally:
                    observe('managed-link-after-request',{**details,'db_after':state(fake)['tables'],'external_before':before_external,'external_after':tree(outside)})
            assert path.read_bytes()==before_owned and path.stat().st_mtime_ns==before_owned_mtime
            resumed,_=stage(b,raw);assert s is None or resumed['upload_id']==s['upload_id']
            old_reference=item['reference']
            receipt=call('POST','/documents/uploads/'+resumed['upload_id']+'/commit',ctx).json();assert receipt['document_id']==item['id']
            wait(item);item['version']=version
            stale=call('POST','/documents/read',{**ctx,'reference':old_reference},reject=True);assert 400<=stale.status_code<500
            for target_item in items:verify(target_item)
            observe('managed-link-valid-after-restore',{**details,'version':version,'capture_id':receipt['capture_id'],'attempt_id':receipt['attempt_id'],'ids':sorted(i['id'] for i in items)})
    assert {e['id'] for e in call('GET','/documents/library').json()}=={i['id'] for i in items}

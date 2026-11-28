"""Public restore manifests must preserve saved bytes without restoring leases."""
import hashlib,json,os,shutil,sqlite3,subprocess,sys
from pathlib import Path
import pytest
from document_helpers import ROOT,observe
from test_document_formats_management import native_input
from test_document_formats_retry import FONT,scan_pdf,keep
from test_document_formats_upload_restart import Server
from smm_local.core import Archive
from smm_local.federation import configure_hub
from smm_local.document_protocol import DocumentGuard


def invoke(root,db,owner,*args):
    argv=([sys.executable,'-B','-m','smm_hub.cli','hub','--state-dir',str(root)] if owner=='hub' else [sys.executable,'-B','-m','smm_local.cli','--db',str(db)])+list(map(str,args))
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONUTF8='1')
    value=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
    observe('restore-cli',{'argv':argv,'exit':value.returncode,'stdout':value.stdout,'stderr':value.stderr})
    assert value.returncode==0,value.stderr
    return json.loads(value.stdout)


def metadata(path):
    with sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        names={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        tables=['documents','document_captures','document_snapshot_state','document_processing_attempts','document_capture_authorizations','document_library','local_document_sync']
        return {t:[dict(r) for r in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables if t in names}


def consistent_backup(source,target):
    with sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True) as a,sqlite3.connect(target) as b:a.backup(b)


def covered(path,roots):return any(path==r or r in path.parents for r in roots)


@pytest.mark.skipif(not FONT,reason='requires prepared local fixture font; no service/platform claim when skipped')
@pytest.mark.parametrize('variant',['local-private','local-sync','hub'])
def test_restore_manifest_copies_all_saved_snapshots_and_keeps_current_fence(tmp_path,variant):
    # TC-008-snapshot-restore-set
    owner='hub' if variant=='hub' else 'local'
    server=Server(tmp_path/'independent-hub','hub');server.db=server.root/'smm-hub.sqlite3'
    root=server.root if owner=='hub' else tmp_path/variant
    root.mkdir(exist_ok=True);db=server.db if owner=='hub' else root/'archive.sqlite3'
    items=[];missing=[]
    try:
        server.start()
        if owner=='local':
            archive=Archive(db);token=root/'task-token';token.write_text(server.token)
            if variant=='local-sync':
                configured=configure_hub(archive,'http://127.0.0.1:'+str(server.port),variant,str(token))
                observe('restore-configure-independent-hub',configured);assert configured['connected'] is True
            projects=[invoke(root,db,owner,'project','create','restore ordinary'),invoke(root,db,owner,'project','ensure-global')]
        else:projects=[invoke(root,db,owner,'project','create','restore ordinary'),invoke(root,db,owner,'project','ensure-global')]
        for group,project in enumerate(projects):
            directory=tmp_path/'external-materials'/str(group);directory.mkdir(parents=True)
            for format in ('docx','xlsx','pdf'):
                label=variant.replace('-','')+str(group)+format
                if format=='pdf':raw=scan_pdf(label);truth={'status':'failed'}
                else:raw,truth=native_input(format,label);truth['status']='ready'
                path=directory/(label+'.'+format);path.write_bytes(raw)
                items.append({'path':path,'raw':raw,'sha256':hashlib.sha256(raw).hexdigest(),'truth':truth,'project':project,'format':format})
                keep('inputs/'+label+'.'+format,raw)
            src=invoke(root,db,owner,'documents','add',directory,'--project-id',project['id'])
            invoke(root,db,owner,'documents','refresh','--source-id',src['id'])
        files=invoke(root,db,owner,'documents','files');assert len(files)==6
        bypath={Path(e['path']).resolve():e for e in files};assert set(bypath)=={i['path'].resolve() for i in items}
        for item in items:
            entry=bypath[item['path'].resolve()];item['id']=entry['id']
            assert entry['latest_attempt']['status']==item['truth']['status']
            if item['format']=='pdf':
                assert entry['published_snapshot'] is None and entry['retry_target'] is not None
            else:
                assert entry['published_snapshot']['sha256']==item['sha256'] and entry['published_snapshot']['status']=='ready'
                # Reading saved raw bytes is a real public command, not just metadata.
                hit=invoke(root,db,owner,'documents','search',item['truth']['words'][0].split()[0],'--scope','project','--project-id',item['project']['id'],*(['--local'] if owner=='local' else []))['results']
                assert len(hit)==1 and hit[0]['id']==entry['id']
                output=root/(entry['id']+'.download')
                invoke(root,db,owner,'documents','read','--reference',hit[0]['reference'],'--original-output',output)
                assert output.read_bytes()==item['raw'];keep('downloads/'+item['sha256'],output.read_bytes())
        archive=Archive(db)
        if variant=='local-private':
            # A real supported ordering: import private files before connecting
            # Hub. Later configure alone must not erase them from restore sets.
            configured=configure_hub(archive,'http://127.0.0.1:'+str(server.port),variant,str(token))
            observe('restore-configure-independent-hub',configured);assert configured['connected'] is True
        if variant=='local-sync':invoke(root,db,owner,'documents','sync-status')
        before=metadata(db)
        assert ('local_document_sync' in before)==(variant=='local-sync')
        snapshot=root/'.document-snapshots';assert snapshot.is_dir()
        durable={p.relative_to(root).as_posix():p.read_bytes() for kind in ('raw','results','transfers') for p in (snapshot/kind).rglob('*') if p.is_file()}
        assert len([p for p in durable if '/raw/' in p])==6
        assert len([p for p in durable if '/results/' in p])==4
        assert all(hashlib.sha256(raw).hexdigest()==Path(name).name for name,raw in durable.items() if '/raw/' in name or '/results/' in name)
        assert {r['raw_sha256'] for r in before['document_captures']}=={i['sha256'] for i in items}
        consistent_backup(db,tmp_path/'consistent.sqlite3')
        # The live process is quiescent; prepare-restore only fences controls.
        result=invoke(root,db,owner,*(['prepare-restore'] if owner=='hub' else ['upload','prepare-restore']))
        observe('restore-manifest',{'variant':variant,'result':result,'durable':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in durable.items()},'metadata':before})
        includes=[Path(p).resolve() for p in result['restore_files']];excludes=[Path(p).resolve() for p in result['do_not_restore']]
        for p in (snapshot,*[root/n for n in durable]):
            if not covered(p,includes):missing.append(str(p))
        expected_exclusions=[snapshot/'tasks',snapshot/'capacity.lock',snapshot/'upload-queue.lock',Path(str(db)+'.documents-guard.json'),Path(str(db)+'.documents-guard.json.lock')]
        missing_exclusions=[str(p) for p in expected_exclusions if p not in excludes]
        observe('restore-required-coverage',{'variant':variant,'missing_durable':missing,'missing_exclusions':missing_exclusions,'has_document_sync': 'local_document_sync' in before})
        assert not missing and not missing_exclusions,{'omitted_saved_bytes':missing,'omitted_runtime_exclusions':missing_exclusions}
        assert Path(db).resolve() in includes and all(p.is_relative_to(root.resolve()) for p in includes)
        assert not any(covered(i['path'].resolve(),includes) for i in items)
        destination=tmp_path/'restored';destination.mkdir()
        # Retain CURRENT guards, never restore an older backup's protection.
        retained={}
        for p in excludes:
            if p.is_file() and p.name.endswith('.json'):
                relative=p.relative_to(root);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes());retained[str(relative)]=hashlib.sha256(p.read_bytes()).hexdigest()
        assert retained and str(Path(str(db.name)+'.documents-guard.json')) in retained
        copied=[]
        for p in includes:
            if not p.exists():continue
            if p==db.resolve():
                shutil.copyfile(tmp_path/'consistent.sqlite3',destination/p.name);copied.append(p.name);continue
            for source in ([p] if p.is_file() else sorted(p.rglob('*'))):
                if not source.is_file() or covered(source.resolve(),excludes):continue
                relative=source.relative_to(root);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);copied.append(str(relative))
        assert all(str(p.relative_to(root)) not in copied for p in expected_exclusions)
        assert not (destination/'.document-snapshots'/'tasks').exists()
        for relative,raw in durable.items():assert (destination/relative).read_bytes()==raw
        for relative,digest in retained.items():assert hashlib.sha256((destination/relative).read_bytes()).hexdigest()==digest
        restored_db=destination/db.name
        with sqlite3.connect(restored_db) as c:assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert metadata(restored_db)==before
        guard=DocumentGuard(Archive(restored_db),('local_document_sync',) if owner=='local' else ())
        assert json.loads(guard.path.read_text())['restore_pending'] is True and guard.status() is not None
        status=invoke(destination,restored_db,owner,*(['documents','recovery-status'] if owner=='hub' else ['upload','status']))
        if owner=='local':assert status['state']=='conflict'
        else:assert status.get('conflict') or status.get('blocked') or status.get('protection') or status.get('requires_recovery'),status
        observe('restore-copied-and-fenced',{'variant':variant,'copied':copied,'retained_current_guards':retained,'durable_bytes':sum(map(len,durable.values())),'all_durable_exact':True,'metadata_exact':True,'restored_status':status})
    finally:server.stop()


@pytest.mark.parametrize('owner',['local','hub'])
def test_legacy_restore_manifest_does_not_invent_snapshot_storage(tmp_path,owner):
    # TC-008-snapshot-restore-set
    from smm_hub.hub import create_hub
    root=tmp_path/owner;root.mkdir();db=root/('smm-hub.sqlite3' if owner=='hub' else 'archive.sqlite3');archive=Archive(db)
    if owner=='hub':create_hub(archive,'synthetic-legacy-restore-'+'a'*32)
    else:
        # This branch concerns the shared legacy directory contract; the actual
        # connected Local public command is independently covered above.
        result=DocumentGuard(archive,()).prepare_restore()
    assert not (root/'.document-snapshots').exists()
    if owner=='hub':result=invoke(root,db,owner,'prepare-restore')
    assert all('.document-snapshots' not in p for key in ('restore_files','do_not_restore') for p in result[key])
    observe('restore-legacy-layout',{'owner':owner,'result':result,'snapshot_directory_created':False})

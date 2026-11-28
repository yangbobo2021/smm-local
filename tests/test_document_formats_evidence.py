"""Evidence custody faults are independent of application business success."""
import hashlib,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/'acceptance'/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
E=load('document_formats_evidence');D=load('document_formats_recover_evidence')


def preserve_control(name,paths,observations,folder=None):
    import os,shutil
    if not os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):return
    root=Path(os.environ['ACCEPTANCE_EVIDENCE_DIR'])/'controls'/name;root.mkdir(parents=True,exist_ok=False)
    for number,path in enumerate(paths):
        path=Path(path)
        if path.is_file():shutil.copyfile(path,root/(str(number)+'-'+path.name))
        elif path.is_dir():shutil.copytree(path,root/(str(number)+'-'+path.name))
    (root/'raw-observations.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2),encoding='utf-8')
    if folder:shutil.copytree(folder,root/'recovered')

@pytest.fixture
def bundle(tmp_path):
    # Frozen independently authored bytes, including a trace with two actions.
    source=tmp_path/'source';source.mkdir()
    body={'files':['alpha.docx','beta.pdf'],'marker':'ONLY_THIS_ORIGINAL_82741'}
    (source/'original.json').write_text(json.dumps(body),encoding='utf-8')
    with zipfile.ZipFile(source/'trace.zip','w') as trace:
        trace.writestr('trace.trace','\n'.join(json.dumps(x) for x in [{'type':'before','callId':'read-alpha'},{'type':'after','callId':'read-alpha'}])+'\n')
    (source/'cleanup.json').write_text(json.dumps({'status':'verified','checks':[{'name':'synthetic-service-control','before':{'registered':True},'after':{'registered':False},'passed':True}]}),encoding='utf-8')
    key=tmp_path/'key';receipt=E.keygen(key)
    context={'run_id':101,'job_key':'custody-control','commit':'a'*40,'artifact_name':'008-custody-control-101-1'}
    envelope=tmp_path/'raw.smm-evidence';generated=E.pack(source,key/'public.pem',context,envelope)
    archive=tmp_path/'artifact.zip'
    with zipfile.ZipFile(archive,'w') as out:out.write(envelope,envelope.name)
    metadata={'id':501,'workflow_run':{'id':101,'head_sha':'a'*40},'name':context['artifact_name'],'digest':'sha256:'+E.sha(archive),'size_in_bytes':archive.stat().st_size,'expires_at':'2030-01-01T00:00:00Z','expired':False}
    return SimpleNamespace(source=source,key=key,context=context,envelope=envelope,archive=archive,metadata=metadata,key_receipt=receipt,generated=generated,source_bytes={p.name:p.read_bytes() for p in source.iterdir()})


def test_durable_key_and_actual_opened_bytes(bundle,tmp_path):
    destination=tmp_path/'verified';result=E.verify(bundle.archive,bundle.metadata,bundle.key/'private.pem',bundle.context,destination,'cleanup.json')
    assert bundle.key_receipt['status']=='persisted_verified' and result['status']=='recovered_verified'
    assert result['artifact_id']==501 and result['run_id']==101 and result['artifact_sha256']==E.sha(bundle.archive)
    assert result['manifest_sha256']==bundle.generated['manifest_sha256']
    for source in bundle.source.iterdir():assert (destination/source.name).read_bytes()==source.read_bytes()
    assert result['opened']['trace.zip']['traces']==1 and result['opened']['original.json']['reader']=='JSON'
    assert set(result['opened'])=={'original.json','trace.zip','cleanup.json'}
    assert json.loads((destination/'recovered-verified.json').read_text())==result


@pytest.mark.parametrize('fault',['wrong-key','archive-digest','ciphertext','context','missing-cleanup','failed-cleanup','upload-failed'])
def test_faults_never_publish_verified_receipt(bundle,tmp_path,fault):
    archive=bundle.archive;metadata=dict(bundle.metadata);private=bundle.key/'private.pem';context=dict(bundle.context);cleanup='cleanup.json'
    if fault=='wrong-key':E.keygen(tmp_path/'wrong-key');private=tmp_path/'wrong-key/private.pem'
    elif fault=='archive-digest':metadata['digest']='sha256:'+'0'*64
    elif fault=='ciphertext':
        damaged=bytearray(bundle.envelope.read_bytes());damaged[-18]^=1
        archive=tmp_path/'damaged.zip'
        with zipfile.ZipFile(archive,'w') as out:out.writestr('raw.smm-evidence',damaged)
        metadata.update(digest='sha256:'+E.sha(archive),size_in_bytes=archive.stat().st_size)
    elif fault=='context':context['job_key']='another-job'
    elif fault=='missing-cleanup':cleanup='absent-cleanup.json'
    elif fault=='failed-cleanup':
        (bundle.source/'cleanup.json').write_text(json.dumps({'status':'failed','checks':[{'before':True,'after':True,'passed':False}]}),encoding='utf-8')
        replacement=tmp_path/'failed.smm-evidence';E.pack(bundle.source,bundle.key/'public.pem',bundle.context,replacement)
        archive=tmp_path/'failed.zip'
        with zipfile.ZipFile(archive,'w') as out:out.write(replacement,replacement.name)
        metadata.update(digest='sha256:'+E.sha(archive),size_in_bytes=archive.stat().st_size)
    else:archive=tmp_path/'never-uploaded.zip'
    destination=tmp_path/('recovery-'+fault)
    with pytest.raises(Exception):E.verify(archive,metadata,private,context,destination,cleanup)
    assert not destination.exists() and not list(tmp_path.rglob('recovered-verified.json'))
    assert bundle.key.joinpath('private.pem').exists() and bundle.archive.exists()

    # Exercise the public verifier CLI: an exception alone is not evidence state.
    metadata_path=tmp_path/'fault-metadata.json';metadata_path.write_text(json.dumps(metadata),encoding='utf-8')
    context_path=tmp_path/'fault-context.json';context_path.write_text(json.dumps(context),encoding='utf-8')
    failed_receipt=tmp_path/'failed-receipt.json'
    command=[sys.executable,str(ROOT/'scripts/acceptance/document_formats_evidence.py'),'verify','--artifact',str(archive),'--metadata',str(metadata_path),'--private-key',str(private),'--context',str(context_path),'--output',str(destination),'--cleanup',cleanup,'--receipt',str(failed_receipt)]
    failed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=15)
    assert failed.returncode==1 and not destination.exists()
    failure=json.loads(failed_receipt.read_text(encoding='utf-8'));assert failure==json.loads(failed.stdout) and failure['status']=='incomplete'
    assert failure['error_type']=={'wrong-key':'ValueError','archive-digest':'ValueError','ciphertext':'InvalidTag','context':'ValueError','missing-cleanup':'ValueError','failed-cleanup':'ValueError','upload-failed':'FileNotFoundError'}[fault]
    assert failure['error'] or failure['error_type']=='InvalidTag'
    unchanged=failed_receipt.read_bytes()
    # Correct context/key and the original immutable artifact recover on a new
    # attempt; the failed receipt is retained byte for byte.
    original_metadata=tmp_path/'original-metadata.json';original_metadata.write_text(json.dumps(bundle.metadata),encoding='utf-8')
    original_context=tmp_path/'original-context.json';original_context.write_text(json.dumps(bundle.context),encoding='utf-8')
    good_receipt=tmp_path/'after-recovery.json';recovered=tmp_path/'after-recovery'
    good_command=[sys.executable,str(ROOT/'scripts/acceptance/document_formats_evidence.py'),'verify','--artifact',str(bundle.archive),'--metadata',str(original_metadata),'--private-key',str(bundle.key/'private.pem'),'--context',str(original_context),'--output',str(recovered),'--cleanup','cleanup.json','--receipt',str(good_receipt)]
    good=subprocess.run(good_command,capture_output=True,text=True,encoding='utf-8',timeout=15)
    assert good.returncode==0,good.stdout+good.stderr
    assert json.loads(good_receipt.read_text())['status']=='recovered_verified' and failed_receipt.read_bytes()==unchanged
    for name,raw in bundle.source_bytes.items():assert (recovered/name).read_bytes()==raw
    preserve_control('verify-'+fault,[failed_receipt,good_receipt,metadata_path,context_path,original_metadata,original_context,bundle.archive,*([archive] if archive.exists() and archive!=bundle.archive else [])],{'failed':{'argv':command,'code':failed.returncode,'stdout':failed.stdout,'stderr':failed.stderr},'restored':{'argv':good_command,'code':good.returncode,'stdout':good.stdout,'stderr':good.stderr}},recovered)


def test_controller_offline_then_recovery_keeps_failed_attempt(bundle,tmp_path,monkeypatch):
    output=tmp_path/'download';calls=[];online=False
    def provider(argv,**kwargs):
        calls.append(list(argv))
        if not online:raise subprocess.TimeoutExpired(argv,1)
        if argv[-1].endswith('/zip'):
            kwargs['stdout'].write(bundle.archive.read_bytes());return subprocess.CompletedProcess(argv,0,stderr=b'')
        return subprocess.CompletedProcess(argv,0,stdout=json.dumps(bundle.metadata).encode(),stderr=b'')
    monkeypatch.setattr(D.subprocess,'run',provider)
    first=D.download('owner/project',501,101,'a'*40,bundle.context['artifact_name'],output)
    assert first['status']=='incomplete' and first['error_type']=='TimeoutExpired'
    assert not list(output.glob('*.zip')) and not list(output.rglob('recovered-verified.json'))
    online=True
    second=D.download('owner/project',501,101,'a'*40,bundle.context['artifact_name'],output)
    assert second['status']=='downloaded_verified' and second['attempt']==2
    assert json.loads((output/'download-1.json').read_text())==first
    actual_meta=json.loads(Path(second['metadata']).read_text());destination=tmp_path/'after-reconnect'
    result=E.verify(second['artifact'],actual_meta,bundle.key/'private.pem',bundle.context,destination,'cleanup.json')
    assert result['status']=='recovered_verified' and (destination/'original.json').read_bytes()==(bundle.source/'original.json').read_bytes()
    assert calls[-1][-1]=='repos/owner/project/actions/artifacts/501/zip'
    preserve_control('offline-restored',[output],{'first':first,'second':second,'calls':calls},destination)


@pytest.mark.parametrize('failure',['expired','not-uploaded','corrupt-download','upload-failed'])
def test_provider_failures_keep_custody_incomplete(bundle,tmp_path,monkeypatch,failure):
    calls=[]
    def provider(argv,**kwargs):
        calls.append(list(argv))
        if failure=='not-uploaded':raise subprocess.CalledProcessError(1,argv,stderr=b'404: artifact not created')
        if argv[-1].endswith('/zip'):
            kwargs['stdout'].write(b'corrupted transfer');return subprocess.CompletedProcess(argv,0,stderr=b'')
        metadata={**bundle.metadata,'expired':failure=='expired'}
        return subprocess.CompletedProcess(argv,0,stdout=json.dumps(metadata).encode(),stderr=b'')
    monkeypatch.setattr(D.subprocess,'run',provider)
    output=tmp_path/failure;result=D.download('owner/project',501,101,'a'*40,bundle.context['artifact_name'],output,upload_state='failure' if failure=='upload-failed' else 'success')
    assert result['status']=='incomplete' and not list(output.glob('*.zip')) and not list(output.rglob('recovered-verified.json'))
    assert json.loads((output/'download-1.json').read_text())==result
    if failure=='upload-failed':assert len(calls)==0 and result['phase']=='upload' and result['upload_state']=='failure'
    elif failure in ('expired','not-uploaded'):assert len(calls)==1
    else:assert len(calls)==2 and list(output.glob('*.partial'))
    assert result['error_type'] and result['error']
    preserve_control('provider-'+failure,[output],{'result':result,'calls':calls})



def test_actual_github_artifact_can_be_decrypted_and_opened(tmp_path):
    import os
    names=['SMM_008_EVIDENCE_ZIP','SMM_008_EVIDENCE_METADATA','SMM_008_EVIDENCE_CONTEXT','SMM_008_EVIDENCE_KEY']
    if not all(os.environ.get(name) for name in names):pytest.skip('explicit recovered real CI artifact and durable controller key required; unit controls alone are not final custody proof')
    archive,metadata_path,context_path,key=[Path(os.environ[name]) for name in names]
    metadata=json.loads(metadata_path.read_text(encoding='utf-8'));context=json.loads(context_path.read_text(encoding='utf-8'))
    from datetime import datetime
    key_receipt=json.loads(key.with_name('key-receipt.json').read_text(encoding='utf-8'))
    assert key_receipt['status']=='persisted_verified' and key_receipt['public_key_sha256']==E.sha(key.with_name('public.pem'))
    assert datetime.fromisoformat(key_receipt['checked_at'])<datetime.fromisoformat(metadata['created_at'].replace('Z','+00:00'))
    destination=tmp_path/'actual-recovered'
    receipt=E.verify(archive,metadata,key,context,destination,'cleanup.json')
    assert receipt['status']=='recovered_verified' and receipt['artifact_id']==metadata['id']
    assert receipt['context']==context and receipt['artifact_sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
    expected={'cleanup.json','downloads/alpha.docx','downloads/beta.pdf','index.html','observations.json','originals/alpha.docx','originals/beta.pdf','trace.zip','visible-probe.png'}
    assert set(receipt['opened'])==expected
    observations=json.loads((destination/'observations.json').read_text(encoding='utf-8'))
    assert observations['title']=='008 evidence custody probe'
    for name in ('alpha.docx','beta.pdf'):
        original=(destination/'originals'/name).read_bytes();download=(destination/'downloads'/name).read_bytes()
        assert original==download and observations['originals'][name]==observations['downloads'][name]==hashlib.sha256(original).hexdigest()
    from document_formats_fixtures import docx_fixture
    from defusedxml.ElementTree import fromstring
    with zipfile.ZipFile(destination/'originals/alpha.docx') as word:
        texts='\n'.join(''.join(fromstring(word.read(name)).itertext()) for name in word.namelist() if name.startswith('word/') and name.endswith('.xml') and '/_rels/' not in name)
    for anchor in docx_fixture('custodyalpha')[1]['words']:assert texts.count(anchor)==1
    import pdfplumber
    with pdfplumber.open(destination/'originals/beta.pdf') as pdf:
        assert len(pdf.pages)==2
        for number,page in enumerate(pdf.pages,1):assert page.extract_text()=='CUSTODY BETA ORIGINAL PAGE '+str(number)
    with zipfile.ZipFile(destination/'trace.zip') as trace:
        events=[json.loads(line) for name in trace.namelist() if name.endswith('.trace') for line in trace.read(name).splitlines()]
        assert any(event.get('type')=='before' and event.get('method')=='goto' for event in events)
        assert sum(event.get('type')=='before' and event.get('method')=='click' for event in events)==2
    cleanup=json.loads((destination/'cleanup.json').read_text(encoding='utf-8'))
    assert cleanup['status']=='verified'
    for check in cleanup['checks']:
        assert check['before']['listening'] and check['before']['thread_alive']
        assert check['after']['listening'] is False and check['after']['thread_alive'] is False and check['passed'] is True
    if evidence:=os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        import shutil
        evidence=Path(evidence);shutil.copytree(destination,evidence/'actual-ci-recovered')
        (evidence/'durable-key-preflight.json').write_text(json.dumps(key_receipt,ensure_ascii=False),encoding='utf-8')
        for name,path in [('artifact.zip',archive),('artifact-metadata.json',metadata_path),('expected-context.json',context_path)]:shutil.copyfile(path,evidence/name)

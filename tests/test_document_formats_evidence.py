"""Evidence custody faults are independent of application business success."""
import hashlib,importlib.util,json,subprocess,sys,zipfile
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/'acceptance'/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
E=load('document_formats_evidence');D=load('document_formats_recover_evidence')

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
    return SimpleNamespace(source=source,key=key,context=context,envelope=envelope,archive=archive,metadata=metadata,key_receipt=receipt,generated=generated)


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


@pytest.mark.parametrize('failure',['expired','not-uploaded','corrupt-download'])
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
    output=tmp_path/failure;result=D.download('owner/project',501,101,'a'*40,bundle.context['artifact_name'],output)
    assert result['status']=='incomplete' and not list(output.glob('*.zip')) and not list(output.rglob('recovered-verified.json'))
    assert json.loads((output/'download-1.json').read_text())==result
    if failure in ('expired','not-uploaded'):assert len(calls)==1
    else:assert len(calls)==2 and list(output.glob('*.partial'))

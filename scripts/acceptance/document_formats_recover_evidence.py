"""Download one immutable GitHub artifact; decryption/inspection is separate."""
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def download(repository,artifact_id,run_id,commit,name,output,gh='gh',timeout=45,upload_state='unknown'):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    attempt=1
    while (output/f'download-{attempt}.json').exists():attempt+=1
    receipt={'status':'incomplete','artifact_id':artifact_id,'run_id':run_id,'repository':repository,'attempt':attempt,'phase':'upload','upload_state':upload_state,'started_at':datetime.now(timezone.utc).isoformat()}
    endpoint=f'repos/{repository}/actions/artifacts/{artifact_id}'
    try:
        if upload_state not in ('success','failure','cancelled','missing','unknown'):raise ValueError('invalid upload state')
        if upload_state in ('failure','cancelled','missing'):raise ValueError('upstream evidence upload '+upload_state+'; evidence remains incomplete')
        receipt['phase']='metadata'
        response=subprocess.run([gh,'api',endpoint],capture_output=True,timeout=timeout,check=True)
        (output/f'metadata-{attempt}.json').write_bytes(response.stdout);metadata=json.loads(response.stdout)
        if metadata.get('id')!=artifact_id or metadata.get('workflow_run',{}).get('id')!=run_id or metadata.get('workflow_run',{}).get('head_sha')!=commit or metadata.get('name')!=name:raise ValueError('artifact identity mismatch')
        if metadata.get('expired'):raise ValueError('artifact expired and cannot be recovered from provider')
        receipt['phase']='download'
        path=output/f'artifact-{artifact_id}-attempt-{attempt}.partial'
        with path.open('xb') as stream:
            result=subprocess.run([gh,'api',endpoint+'/zip'],stdout=stream,stderr=subprocess.PIPE,timeout=timeout)
            stream.flush()
        (output/f'download-{attempt}.stderr').write_bytes(result.stderr)
        if result.returncode:raise RuntimeError('artifact download failed: '+result.stderr.decode('utf-8','replace')[:2000])
        actual=digest(path)
        if metadata.get('digest')!='sha256:'+actual or metadata.get('size_in_bytes')!=path.stat().st_size:raise ValueError('downloaded artifact digest/length mismatch')
        final=path.with_suffix('.zip');path.rename(final)
        receipt.update(phase='downloaded_verified',status='downloaded_verified',artifact=str(final),artifact_sha256=actual,metadata=str(output/f'metadata-{attempt}.json'),expires_at=metadata['expires_at'],bytes=final.stat().st_size)
    except Exception as error:
        receipt.update(error_type=type(error).__name__,error=str(error)[:3000])
        if isinstance(error,(subprocess.CalledProcessError,subprocess.TimeoutExpired)):
            for label,value in [('stdout',error.stdout),('stderr',error.stderr)]:
                raw=value.encode('utf-8') if isinstance(value,str) else value or b''
                path=output/f'provider-error-{attempt}.{label}';path.write_bytes(raw);receipt[label+'_file']=str(path)
    receipt['finished_at']=datetime.now(timezone.utc).isoformat()
    (output/f'download-{attempt}.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repository',required=True);p.add_argument('--artifact-id',type=int,required=True);p.add_argument('--run-id',type=int,required=True);p.add_argument('--commit',required=True);p.add_argument('--name',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--gh',default='gh');p.add_argument('--timeout',type=int,default=45);p.add_argument('--upload-state',choices=['success','failure','cancelled','missing','unknown'],default='unknown');a=p.parse_args()
    result=download(a.repository,a.artifact_id,a.run_id,a.commit,a.name,a.output,a.gh,a.timeout,a.upload_state);print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='downloaded_verified' else 1
if __name__=='__main__':sys.exit(main())

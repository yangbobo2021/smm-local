from pathlib import Path
import datetime,hashlib,json,os,subprocess
root=Path('<task-path>');out=root/'.acceptance-local/native-v1/AT-SMM-005/work/windows-empty31-formal';out.mkdir(exist_ok=False)
cmd=['<task-path>','scripts/acceptance/selective_upload_empty_recorded.py','--target-config','.acceptance-local/native-v1/AT-SMM-005/native-targets/empty-windows29.json','--probe','empty','--mode','client']
paths=[p for dirname in ['src','scripts/acceptance'] for p in (root/dirname).rglob('*') if p.is_file() and p.suffix in ['.py','.html']];paths.append(root/'.acceptance-local/native-v1/AT-SMM-005/native-targets/empty-windows29.json')
inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};(out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();env={**os.environ,'ACCEPTANCE_EVIDENCE_DIR':str(out)};error=None;code=None
with (out/'run.stdout').open('wb') as stdout,(out/'run.stderr').open('wb') as stderr:
 try:
  p=subprocess.run(cmd,cwd=root,env=env,stdout=stdout,stderr=stderr,timeout=1500);code=p.returncode
 except subprocess.TimeoutExpired:error='timed out after 1500 seconds; inspect actual remote effects before any retry'
receipt={'argv':cmd,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':code,'error':error,'environment':{'ACCEPTANCE_EVIDENCE_DIR':str(out)},'input_manifest_sha256':hashlib.sha256((out/'inputs.json').read_bytes()).hexdigest(),'stdout_sha256':hashlib.sha256((out/'run.stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((out/'run.stderr').read_bytes()).hexdigest(),'scope':'fresh formal external business execution; native manual records this actual long operation, never marks timed-out debug as passed'}
(out/'process.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
assert code==0 and error is None
assert all(hashlib.sha256((root/k).read_bytes()).hexdigest()==v for k,v in inputs.items())
result=json.loads((out/'probe/result.json').read_text());assert result['status']=='passed';assert json.loads((out/'probe/cleanup.json').read_text())['failures']==[]
print('formal external Windows business completed',flush=True)

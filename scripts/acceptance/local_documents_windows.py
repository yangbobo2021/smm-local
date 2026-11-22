"""Schedule E1 in the signed-in Windows user's Limited interactive token."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assert sys.platform=='win32'
    if a.output.exists():raise ValueError('use a new output directory')
    target=json.loads(a.target_config.read_text(encoding='utf-8-sig'));out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
    actor=Path(__file__).with_name('local_documents_platform.py').resolve()
    worker=Path(str(out)+'.worker.py');receipt=Path(str(out)+'.worker-exit.json');log=Path(str(out)+'.worker.log');driver=Path(str(out)+'.driver.ps1')
    argv=[str(actor),'--target-config',str(a.target_config.resolve()),'--output',str(out)]
    worker.write_text(f'''import ctypes,json,os,runpy,sys,time,traceback
from pathlib import Path
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(),0)
f=open({str(log)!r},'w',encoding='utf-8');sys.stdout=f;sys.stderr=f
code=0;started=time.time()
try:
 assert not ctypes.windll.shell32.IsUserAnAdmin(),'ordinary user token required'
 sys.argv={argv!r};sys.path.insert(0,{str(actor.parent)!r});runpy.run_path({str(actor)!r},run_name='__main__')
except SystemExit as e:code=e.code or 0
except BaseException:code=1;traceback.print_exc()
finally:
 f.flush();Path({str(receipt)!r}).write_text(json.dumps({{'pid':os.getpid(),'started_at':started,'finished_at':time.time(),'exit_code':code,'is_admin':bool(ctypes.windll.shell32.IsUserAnAdmin())}})+'\\n',encoding='utf-8')
sys.exit(code)
''',encoding='utf-8')
    def quote(x):return "'"+str(x).replace("'","''")+"'"
    task='SmmDocuments006-'+uuid4().hex
    driver.write_text(f'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$name={quote(task)}
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$action=New-ScheduledTaskAction -Execute {quote(target['controller_python'])} -Argument {quote('"'+str(worker)+'"')}
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 22)
try {{
 Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings | Out-Null
 Start-ScheduledTask -TaskName $name
 $deadline=(Get-Date).AddMinutes(20)
 while (!(Test-Path {quote(receipt)})) {{
  if ((Get-Date) -gt $deadline) {{throw 'ordinary interactive document probe timed out'}}
  Start-Sleep -Milliseconds 500
 }}
 $r=Get-Content {quote(receipt)} -Raw | ConvertFrom-Json
 exit $r.exit_code
}} finally {{
 Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
 Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}}
''',encoding='utf-8-sig')
    started=__import__('time').time();r=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(driver)],timeout=1320)
    check=subprocess.run(['powershell','-NoProfile','-Command',f"Get-ScheduledTask -TaskName {quote(task)} -ErrorAction SilentlyContinue | ConvertTo-Json"],capture_output=True,text=True)
    Path(str(out)+'.controller.json').write_text(json.dumps({'task':task,'argv':['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(driver)],'started_at':started,'finished_at':__import__('time').time(),'exit_code':r.returncode,'task_query_stdout':check.stdout,'task_removed':not check.stdout.strip()})+'\n',encoding='utf-8')
    assert not check.stdout.strip(),'owned interactive task was not removed'
    raise SystemExit(r.returncode)


if __name__=='__main__':main()

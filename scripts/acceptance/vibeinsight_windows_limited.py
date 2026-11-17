# SPDX-License-Identifier: Apache-2.0
"""Run the native client probe in the logged-in Windows user's ordinary session."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-config',type=Path,required=True)
    p.add_argument('--fixture-manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assert sys.platform=='win32'
    if a.output.exists():raise ValueError('use a new output directory')
    config=json.loads(a.target_config.read_text(encoding='utf-8-sig'))
    actor=Path(__file__).with_name('vibeinsight_platform.py').resolve()
    argv=[str(actor),'client','--target-config',str(a.target_config.resolve()),'--fixture-manifest',
          str(a.fixture_manifest.resolve()),'--output',str(a.output.resolve())]
    base=a.output.resolve();base.parent.mkdir(parents=True,exist_ok=True)
    bootstrap=Path(str(base)+'.worker.py');receipt=Path(str(base)+'.process.json')
    log=Path(str(base)+'.worker.log');driver=Path(str(base)+'.driver.ps1')
    bootstrap.write_text(f'''import ctypes,json,os,runpy,sys,traceback
from pathlib import Path
ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(),0)
f=open({str(log)!r},'w',encoding='utf-8'); sys.stdout=f; sys.stderr=f
code=0
try:
 assert not ctypes.windll.shell32.IsUserAnAdmin(), 'client must use an ordinary token'
 sys.argv={argv!r};sys.path.insert(0,{str(actor.parent)!r})
 runpy.run_path({str(actor)!r},run_name='__main__')
except SystemExit as e:
 code=e.code or 0
except BaseException:
 code=1;traceback.print_exc()
finally:
 f.flush()
 Path({str(receipt)!r}).write_text(json.dumps({{'pid':os.getpid(),'exit_code':code,'session':'current interactive user; Limited task'}})+'\\n',encoding='utf-8')
sys.exit(code)
''',encoding='utf-8')
    # A separate SSH service window station can reject ordinary-token processes
    # during DLL initialization. The logged-in user's own session has its normal desktop ACL.
    def quote(text):return "'"+str(text).replace("'","''")+"'"
    task='SmmVibeClient-'+uuid.uuid4().hex
    script=f'''$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$name={quote(task)}
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$action=New-ScheduledTaskAction -Execute {quote(config['local_python'])} -Argument {quote('"'+str(bootstrap)+'"')}
$settings=New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
try {{
 Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings $settings | Out-Null
 Start-ScheduledTask -TaskName $name
 $deadline=(Get-Date).AddMinutes(3)
 while (!(Test-Path {quote(receipt)})) {{
  if ((Get-Date) -gt $deadline) {{throw 'ordinary client task timed out; check interactive logon'}}
  Start-Sleep -Milliseconds 500
 }}
 $r=Get-Content {quote(receipt)} -Raw | ConvertFrom-Json
 exit $r.exit_code
}} finally {{
 Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
 Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}}
'''
    driver.write_text(script,encoding='utf-8-sig')
    process=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(driver)],timeout=220)
    raise SystemExit(process.returncode)


if __name__=='__main__':main()

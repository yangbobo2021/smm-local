param([Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$name='Smm007Preflight-'+[guid]::NewGuid().ToString('N')
$receipt=Join-Path $OutputDirectory 'limited-token.json'
$worker=Join-Path $OutputDirectory 'limited-worker.ps1'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$report=@{purpose='Environment only; no product acceptance';controller_identity=$identity.Name;controller_admin=$admin;limited_task=$false;scm_create_delete=$false}
$escaped=$receipt.Replace("'","''")
@"
`$ErrorActionPreference='Stop'
`$id=[Security.Principal.WindowsIdentity]::GetCurrent()
`$admin=([Security.Principal.WindowsPrincipal]`$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
@{identity=`$id.Name;sid=`$id.User.Value;is_admin=`$admin;pid=`$PID;session_id=(Get-Process -Id `$PID).SessionId}|ConvertTo-Json|Set-Content -Encoding UTF8 '$escaped'
"@|Set-Content -Encoding UTF8 $worker
try {
  $principal=New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
  $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+$worker+'"')
  Register-ScheduledTask -TaskName $name -Action $action -Principal $principal -Settings (New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 1))|Out-Null
  Start-ScheduledTask -TaskName $name
  $deadline=(Get-Date).AddSeconds(30)
  while (!(Test-Path $receipt) -and (Get-Date) -lt $deadline) {Start-Sleep -Milliseconds 500}
  if (Test-Path $receipt) {$r=Get-Content $receipt -Raw|ConvertFrom-Json;$report.limited_task=(!$r.is_admin);$report.limited_receipt=$r}
  else {$report.limited_error='No interactive task receipt within 30 seconds'}
} catch {$report.limited_error=$_.Exception.Message}
finally {
  Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}
# The built-in runneradmin account can retain an administrator token even at
# RunLevel Limited. Probe a distinct standard account instead of mislabelling it.
$userName='Smm007'+[guid]::NewGuid().ToString('N').Substring(0,10)
$ordinaryTask=$name+'-Ordinary'
$ordinaryReceipt=Join-Path $OutputDirectory 'ordinary-token.json'
$ordinaryWorker=Join-Path $OutputDirectory 'ordinary-worker.py'
$python=(Get-Command python).Source
$pythonReceipt=$ordinaryReceipt.Replace('\','\\').Replace("'","\'")
@"
import ctypes,json,os,subprocess
from pathlib import Path
sid=ctypes.c_ulong()
ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(sid))
value={'is_admin':bool(ctypes.windll.shell32.IsUserAnAdmin()),'pid':os.getpid(),'session_id':sid.value,'identity':subprocess.check_output(['whoami'],text=True).strip()}
Path('$pythonReceipt').write_text(json.dumps(value),encoding='utf-8')
"@|Set-Content -Encoding UTF8 $ordinaryWorker
$password='Smm!'+[guid]::NewGuid().ToString('N')+'9aA'
try {
  $secure=New-Object System.Security.SecureString
  foreach ($character in $password.ToCharArray()) {$secure.AppendChar($character)}
  $secure.MakeReadOnly()
  New-LocalUser -Name $userName -Password $secure -AccountNeverExpires|Out-Null
  Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $userName
  $account=$env:COMPUTERNAME+'\'+$userName
  & icacls.exe $OutputDirectory /grant ($account+':(OI)(CI)M')|Out-Null
  if ($LASTEXITCODE -ne 0) {throw 'Task output ACL grant failed'}
  $action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$ordinaryWorker+'"')
  Register-ScheduledTask -TaskName $ordinaryTask -Action $action -User $account -Password $password -RunLevel Limited|Out-Null
  Start-ScheduledTask -TaskName $ordinaryTask
  $deadline=(Get-Date).AddSeconds(20)
  while (!(Test-Path $ordinaryReceipt) -and (Get-Date) -lt $deadline) {Start-Sleep -Milliseconds 500}
  if (Test-Path $ordinaryReceipt) {$r=Get-Content $ordinaryReceipt -Raw|ConvertFrom-Json;$report.ordinary_password_task=(!$r.is_admin);$report.ordinary_receipt=$r}
  else {
    $report.ordinary_error='No ordinary account receipt within 20 seconds'
    $report.ordinary_task_info=(Get-ScheduledTaskInfo -TaskName $ordinaryTask|Format-List|Out-String)
    $report.ordinary_task_principal=(Get-ScheduledTask -TaskName $ordinaryTask).Principal|Select-Object UserId,LogonType,RunLevel
    Stop-ScheduledTask -TaskName $ordinaryTask -ErrorAction SilentlyContinue
    $credential=New-Object System.Management.Automation.PSCredential($account,$secure)
    $secondary=Get-Service seclogon
    $startedSecondary=$secondary.Status -ne 'Running'
    if ($startedSecondary) {Start-Service seclogon}
    try {
      $child=Start-Process -FilePath $python -ArgumentList ('"'+$ordinaryWorker+'"') -Credential $credential -LoadUserProfile -PassThru
      if (!$child.WaitForExit(15000)) {Stop-Process -Id $child.Id -Force;throw 'Ordinary credential process timed out'}
      $report.ordinary_process_exit=$child.ExitCode
      if (Test-Path $ordinaryReceipt) {$r=Get-Content $ordinaryReceipt -Raw|ConvertFrom-Json;$report.ordinary_credential_process=(!$r.is_admin);$report.ordinary_receipt=$r}
    } finally {if ($startedSecondary) {Stop-Service seclogon -ErrorAction SilentlyContinue}}
  }
} catch {$report.ordinary_error=$_.Exception.Message}
finally {
  Stop-ScheduledTask -TaskName $ordinaryTask -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $ordinaryTask -Confirm:$false -ErrorAction SilentlyContinue
  Remove-LocalUser -Name $userName -ErrorAction SilentlyContinue
  $password=$null
}
try {
  $bin='"'+$env:SystemRoot+'\System32\cmd.exe" /c exit 0'
  $out=& sc.exe create $name binPath= $bin obj= 'NT AUTHORITY\LocalService' start= demand 2>&1
  if ($LASTEXITCODE -ne 0) {throw ($out|Out-String)}
  $report.scm_configuration=(& sc.exe qc $name 2>&1|Out-String)
  $report.scm_create_delete=$true
} catch {$report.scm_error=$_.Exception.Message}
finally {& sc.exe delete $name 2>&1|Out-Null}
$report|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $OutputDirectory 'windows-capabilities.json')
$report|ConvertTo-Json -Depth 8

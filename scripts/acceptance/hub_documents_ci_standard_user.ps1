param([Parameter(Mandatory=$true)][string]$Python,[Parameter(Mandatory=$true)][string]$Runner,[Parameter(Mandatory=$true)][string]$Config,[Parameter(Mandatory=$true)][string]$Work,[Parameter(Mandatory=$true)][string]$Workspace,[string]$ReadPath)
$ErrorActionPreference='Stop'
$name='Smm007'+[guid]::NewGuid().ToString('N').Substring(0,10)
$password='Smm!'+[guid]::NewGuid().ToString('N')+'9aA'
$report=@{purpose='007 actual ordinary-account product acceptance';user=$name;started_at=(Get-Date).ToUniversalTime().ToString('o')}
$startedSecondary=$false
$child=$null
$created=$false
try {
  $secure=New-Object System.Security.SecureString
  foreach ($character in $password.ToCharArray()) {$secure.AppendChar($character)}
  $secure.MakeReadOnly()
  New-LocalUser -Name $name -Password $secure -AccountNeverExpires|Out-Null
  $created=$true
  Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $name
  $account=$env:COMPUTERNAME+'\'+$name
  & icacls.exe $Work /grant ($account+':(OI)(CI)M') /T|Out-Null
  if ($LASTEXITCODE -ne 0) {throw 'Task directory ACL grant failed'}
  & icacls.exe $Workspace /grant ($account+':(OI)(CI)RX')|Out-Null
  if ($LASTEXITCODE -ne 0) {throw 'Task source/controller read ACL grant failed'}
  if ($ReadPath) {
    & icacls.exe $ReadPath /grant ($account+':(OI)(CI)RX') /T|Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Task program read/execute ACL grant failed'}
  }
  # uv build can preserve a temporary wheel's protected ACL. Give this task's
  # ordinary reviewer explicit file read access; do not weaken Hub-state ACLs.
  $target=Get-Content $Config -Raw|ConvertFrom-Json
  $wheelAcls=@()
  foreach ($wheel in @($target.local_wheel,$target.hub_wheel)) {
    $before=(Get-Acl -LiteralPath $wheel).AccessToString
    & icacls.exe $wheel /reset|Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Task wheel inheritance reset failed'}
    & icacls.exe $wheel /grant:r ($account+':R')|Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'Task wheel explicit read grant failed'}
    $wheelAcls+=@{path=$wheel;before=$before;after=(Get-Acl -LiteralPath $wheel).AccessToString}
  }
  $report.wheel_acls=$wheelAcls
  $credential=New-Object System.Management.Automation.PSCredential($account,$secure)
  $secondary=Get-Service seclogon
  $startedSecondary=$secondary.Status -ne 'Running'
  if ($startedSecondary) {Start-Service seclogon}
  $arguments='-I "'+$Runner+'" --target-config "'+$Config+'" --output "'+(Join-Path $Work 'platform')+'"'
  $child=Start-Process -FilePath $Python -ArgumentList $arguments -WorkingDirectory $Work -Credential $credential -LoadUserProfile -PassThru
  $report.controller_pid=$child.Id
  if (!$child.WaitForExit(600000)) {throw 'Ordinary-account business probe timed out'}
  # Start-Process ExitCode may be null for a credentialed child. Require the
  # worker's actual end-to-end success receipt and its own token observation.
  $result=Get-Content (Join-Path $Work 'platform/result.json') -Raw|ConvertFrom-Json
  $actor=Get-Content (Join-Path $Work 'platform/controller-identity.json') -Raw|ConvertFrom-Json
  if ($result.status -ne 'passed' -or $actor.is_admin -ne $false) {throw 'No ordinary-account business pass receipt'}
  $report.actual_actor=$actor
  $report.status='passed'
} catch {$report.status='failed';$report.error=$_.Exception.Message;throw}
finally {
  if ($child -and !$child.HasExited) {& taskkill.exe /PID $child.Id /T /F|Out-Null}
  # Probe's normal cleanup checks its actual services/ports. Also reject and
  # remove any process still owned by this temporary account before deletion.
  $remaining=@()
  foreach ($process in Get-CimInstance Win32_Process) {
    $owner=Invoke-CimMethod -InputObject $process -MethodName GetOwner -ErrorAction SilentlyContinue
    if ($owner.User -eq $name) {$remaining+=$process.ProcessId;& taskkill.exe /PID $process.ProcessId /T /F 2>&1|Out-Null}
  }
  $report.unexpected_remaining_pids=$remaining
  if ($created) {Remove-LocalUser -Name $name -ErrorAction SilentlyContinue}
  & icacls.exe $Workspace /remove:g ($env:COMPUTERNAME+'\'+$name) 2>&1|Out-Null
  if ($startedSecondary) {Stop-Service seclogon -ErrorAction SilentlyContinue}
  $report.finished_at=(Get-Date).ToUniversalTime().ToString('o')
  $report|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $Work 'standard-user-controller.json')
  $password=$null
}
if ($remaining.Count -gt 0) {throw 'Ordinary-account processes survived normal cleanup'}

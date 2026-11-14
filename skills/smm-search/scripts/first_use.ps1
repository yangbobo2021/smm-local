# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
$ErrorActionPreference = 'Stop'
$probe = 'import sqlite3, sys, venv; assert sys.version_info >= (3, 11); sqlite3.connect('':memory:'').execute(''CREATE VIRTUAL TABLE t USING fts5(body)'')'
foreach ($candidate in @('python.exe', 'python3.exe', 'py.exe')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $command -or $command.Source -like '*\Microsoft\WindowsApps\*') { continue }
    $prefix = @()
    if ($candidate -eq 'py.exe') { $prefix = @('-3') }
    try {
        & $command.Source @prefix -c $probe 2>$null
        if ($LASTEXITCODE -ne 0) { continue }
    } catch { continue }
    & $command.Source @prefix (Join-Path $PSScriptRoot 'first_use.py') @args
    exit $LASTEXITCODE
}

$runtime = Join-Path $HOME '.local/share/smm-local/bootstrap'
New-Item -Force -ItemType Directory $runtime | Out-Null
$uv = Join-Path $runtime 'uv.exe'
if (-not (Test-Path $uv)) {
    $env:UV_UNMANAGED_INSTALL = $runtime
    $installer = (Invoke-WebRequest -UseBasicParsing 'https://astral.sh/uv/0.13.8/install.ps1').Content
    & ([ScriptBlock]::Create($installer)) | Out-Host
    if (-not (Test-Path $uv)) { throw 'uv 安装失败' }
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $runtime 'python'
$python = $null
try { $python = & $uv python find --managed-python 3.13 2>$null } catch {}
if (-not $python) {
    & $uv python install 3.13 | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $python = & $uv python find --managed-python 3.13
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& $python (Join-Path $PSScriptRoot 'first_use.py') @args
exit $LASTEXITCODE

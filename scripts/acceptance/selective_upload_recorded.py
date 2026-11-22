"""Execute an installed-package probe inside a native acceptance attempt.

The private target can supply ``execution`` with host, scripts and python paths.
Every invocation creates a new task state and runs the business probe again;
this entry never converts an earlier result.json into a new execution.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile
import uuid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-config', type=Path, required=True)
    p.add_argument('--probe', choices=['platform', 'compatibility', 'recovery'], default='platform')
    p.add_argument('--mode', choices=['client', 'self-managed', 'login-service', 'hub-service'], default='client')
    p.add_argument('--case', choices=['R1', 'R2', 'R3', 'R4'])
    p.add_argument('--child', action='store_true')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    output = a.output or Path(os.environ['ACCEPTANCE_EVIDENCE_DIR']) / 'probe'
    output.parent.mkdir(parents=True, exist_ok=True)
    assert not output.exists(), 'use a fresh attempt output'
    config = json.loads(a.target_config.read_text(encoding='utf-8-sig'))
    execution = config.pop('execution', None)
    identity = uuid.uuid4().hex
    extra = ['--probe', a.probe, '--mode', a.mode] + (['--case', a.case] if a.case else [])
    if execution and not a.child:
        remote_root = execution['root'].rstrip('/\\')
        sep = '\\' if execution.get('windows') else '/'
        stem = remote_root + sep + 'native-' + identity
        remote_config, remote_output = stem + '.json', stem + '-evidence'
        config['work'] = stem + '-state'
        with tempfile.TemporaryDirectory(prefix='smm-005-native-') as temp:
            private = Path(temp) / 'target.json'
            private.write_text(json.dumps(config), encoding='utf-8')
            host = execution['host']
            options = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes']
            destination = remote_config.replace('\\', '/')
            subprocess.run(['scp', *options, str(private), host + ':' + destination], check=True)
            actor = execution['scripts'].rstrip('/\\') + sep + Path(__file__).name
            argv = [execution['python'], actor, '--child', '--target-config', remote_config, '--output', remote_output, *extra]
            if execution.get('windows'):
                def ps(value): return "'" + str(value).replace("'", "''") + "'"
                driver = Path(temp) / 'run.ps1'
                driver.write_text("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'\n& " + ' '.join(ps(v) for v in argv) + '\nexit $LASTEXITCODE\n', encoding='utf-8-sig')
                driver_path = stem + '.ps1'
                subprocess.run(['scp', *options, str(driver), host + ':' + driver_path.replace('\\', '/')], check=True)
                command = 'powershell -NoProfile -ExecutionPolicy Bypass -File "' + driver_path + '"'
            else:
                command = shlex.join(argv)
            result = subprocess.run(['ssh', *options, host, command], timeout=2100)
            # Recover failures as well as passes; absent evidence remains a failure.
            copied = subprocess.run(['scp', '-r', *options, host + ':' + remote_output.replace('\\', '/'), str(output)], timeout=180)
            if copied.returncode:
                raise RuntimeError('could not recover the actual remote attempt evidence')
        if result.returncode:
            raise SystemExit(result.returncode)
    else:
        assert sys.platform == config['expected_platform'], 'probe is running on the wrong operating system'
        if not a.child:
            config['work'] = str(Path(config['work']).parent / ('smm-005-native-' + identity))
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0)); config['port'] = s.getsockname()[1]
        config['address'] = 'https://localhost:' + str(config['port'])
        with tempfile.TemporaryDirectory(prefix='smm-005-native-') as temp:
            private = Path(temp) / 'target.json'
            private.write_text(json.dumps(config), encoding='utf-8')
            root = Path(__file__).resolve().parent
            if sys.platform == 'win32' and (a.mode in ('client', 'hub-service')) and a.probe != 'recovery':
                argv = [sys.executable, str(root / 'selective_upload_windows_limited.py'), '--probe', a.probe, '--mode', a.mode]
            else:
                argv = [sys.executable, str(root / ('selective_upload_' + a.probe + '.py'))]
                if a.probe != 'compatibility': argv.append(a.mode)
                if a.case: argv.extend(['--case', a.case])
            result = subprocess.run([*argv, '--target-config', str(private), '--output', str(output)], timeout=2000)
            if sys.platform == 'win32':
                for suffix in ('.worker.log', '.process.json'):
                    source = Path(str(output) + suffix)
                    if source.is_file() and output.is_dir():
                        (output / ('interactive' + suffix)).write_bytes(source.read_bytes())
        if result.returncode:
            raise SystemExit(result.returncode)
    observed = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    assert observed['status'] == 'passed', observed
    cleanup = json.loads((output / 'cleanup.json').read_text(encoding='utf-8'))
    assert cleanup.get('failures') == [], cleanup
    print(json.dumps({'status': 'passed', 'probe': a.probe, 'mode': a.mode, 'case': a.case,
                      'basis': 'new business execution; installed-byte check and original evidence retained'}))


if __name__ == '__main__': main()

"""Native argv controls for restart/retry observers; no product expectations weakened."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from document_helpers import ROOT, observe
from document_formats_platform import process_arguments, document_worker_token, utf8_environment


def test_native_arguments_preserve_complete_real_child_command():
    tail = ['中文 空格 😺', '', 'a"quote', 'C:\\space dir\\tail\\', '\\"', 'last']
    command = [sys.executable, '-B', '-c', 'import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=False))', *tail]
    raw = subprocess.list2cmdline(command) if os.name == 'nt' else command
    assert process_arguments(raw) == command
    assert process_arguments(tuple(command)) == command
    result = subprocess.run(command, capture_output=True, env=utf8_environment(os.environ), timeout=10)
    assert result.returncode == 0 and result.stderr == b''
    assert json.loads(result.stdout) == tail
    for invalid in (None, 13, {}):
        with pytest.raises(TypeError):
            process_arguments(invalid)
    if os.name != 'nt':
        with pytest.raises(TypeError):
            process_arguments(subprocess.list2cmdline(command))
    observe('native-argv-real-child', {'raw': raw, 'normalized': process_arguments(raw), 'actual_tail': json.loads(result.stdout)})


def test_worker_identity_requires_exact_module_position_and_token():
    token = 'a' * 32
    for module in ('smm_local.document_worker', 'smm_hub._archive.document_worker'):
        good = [sys.executable, '-B', '-m', module, '--task-token', token]
        assert document_worker_token(good) == token
        bad = [
            [sys.executable, '-B', '-c', 'pass', module, '--task-token', token],
            [sys.executable, '-B', '-m', 'fake.document_worker', '--task-token', token],
            [sys.executable, '-B', '-m', module, '--other-token', token],
            good[:-1] + ['z' * 32], good[:-1] + ['a' * 31], good[:-1] + [None],
        ]
        assert all(document_worker_token(argv) is None for argv in bad)


def test_restart_audit_counts_actual_workers_and_rejects_substring_commands(tmp_path):
    hooks = tmp_path / 'hooks'
    hooks.mkdir()
    (hooks / 'sitecustomize.py').write_text('from document_formats_restart_server import install_audit\ninstall_audit()\n', encoding='utf-8')
    log = tmp_path / 'events.jsonl'
    env = utf8_environment(os.environ, PYTHONPATH=os.pathsep.join([str(hooks), str(ROOT/'tests'), str(ROOT/'src')]),
                           SMM_008_RESTART_DENY='[]', SMM_008_RESTART_AUDIT=str(log))
    token = 'b' * 32
    commands = [[sys.executable, '-B', '-m', 'smm_local.document_worker', '--task-token', token, '--help']]
    commands += [[sys.executable, '-B', '-c', 'pass', 'smm_local.document_worker', '--task-token', token],
                 [sys.executable, '-B', '-m', 'fake.document_worker', '--task-token', token]]
    code = 'import json,subprocess,sys;print(json.dumps([subprocess.run(c,input=b"",capture_output=True,timeout=10).returncode for c in json.loads(sys.argv[1])]))'
    result = subprocess.run([sys.executable, '-B', '-c', code, json.dumps(commands)], env=env, capture_output=True, timeout=45)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert json.loads(result.stdout) == [0, 0, 1]
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 1 and [row['argv'] for row in rows] == commands[:1]
    assert all(row['task_token'] == token and row['raw_type'] == ('str' if os.name == 'nt' else 'list') for row in rows)
    assert all(process_arguments(row['raw_argv']) == row['argv'] for row in rows)
    observe('restart-native-worker-controls', {'commands': commands, 'exit_codes': json.loads(result.stdout), 'events': rows})


def test_retry_child_source_guard_blocks_actual_open_and_native_process_arguments(tmp_path, monkeypatch):
    from test_document_formats_retry import child_source_guard
    protected = tmp_path / '保护 文件.txt'
    allowed = tmp_path / '允许 文件.txt'
    protected.write_text('original protected bytes', encoding='utf-8')
    allowed.write_text('allowed bytes', encoding='utf-8')
    before = (protected.read_bytes(), protected.stat().st_mtime_ns)
    log = child_source_guard(tmp_path, [protected], monkeypatch)
    env = utf8_environment(os.environ)
    script = 'import subprocess,sys;subprocess.run([sys.executable,"-c","pass",sys.argv[1]],check=True)'
    commands = [[sys.executable, '-B', '-c', 'from pathlib import Path;import sys;Path(sys.argv[1]).read_bytes()', str(protected)],
                [sys.executable, '-B', '-c', script, str(protected)],
                [sys.executable, '-B', '-c', script, str(allowed)]]
    results = [subprocess.run(c, env=env, capture_output=True, timeout=15) for c in commands]
    assert [r.returncode == 0 for r in results] == [False, False, True]
    assert all(b'forbidden original source read' in r.stderr for r in results[:2])
    rows = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 2 and {r['event'] for r in rows} == {'open', 'subprocess.Popen'}
    assert all(Path(r['path']) == protected for r in rows)
    assert (protected.read_bytes(), protected.stat().st_mtime_ns) == before
    observe('retry-native-source-guard-controls', {'exit_codes': [r.returncode for r in results], 'events': rows})

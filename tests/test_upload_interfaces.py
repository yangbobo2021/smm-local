"""Local control authorization and public CLI/Skill discovery contracts."""
import importlib.util
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
from smm_local.api import create_app
from test_005_contracts import pair, add_local, connect


def test_new_web_controls_require_same_origin_or_service_token(pair):
    a = add_local(pair, 'a', 'A', 'private'); connect(pair)
    with TestClient(create_app(pair.local, auto_sync=False, service_token='synthetic-local-control')) as web:
        actions = [('PUT', '/api/upload', {'mode': 'none', 'project_ids': []}),
                   ('POST', '/api/upload/reconcile', {}), ('POST', '/api/upload/prepare-restore', None),
                   ('POST', '/api/projects/global', None),
                   ('POST', '/api/projects/assign', {'conversation_id': a['id'], 'project_id': a['project_id']}),
                   ('POST', '/api/projects/map', {'path': str(pair.histories), 'project_id': a['project_id']}),
                   ('POST', '/api/projects/merge', {'source_id': a['project_id'], 'target_id': a['project_id']})]
        for method, route, payload in actions:
            for headers in ({}, {'Origin': 'https://untrusted.example', 'X-SMM-UI': '1'}):
                result = web.request(method, route, json=payload, headers=headers)
                assert result.status_code == 403, result.text
        good = web.put('/api/upload', json={'mode': 'none', 'project_ids': []}, headers={'X-SMM-Service': 'synthetic-local-control'})
        assert good.status_code == 200 and good.json()['state'] == 'confirmed'
        before = good.json()
        bad = web.put('/api/upload', json={'mode': 'all', 'project_ids': [a['project_id']]}, headers={'X-SMM-Service': 'synthetic-local-control'})
        assert bad.status_code == 400
        assert web.get('/api/upload').json()['generation'] == before['generation']


def test_new_cli_help_explains_values_and_first_use_keeps_old_install_explicit(monkeypatch, tmp_path, capsys):
    for args, phrases in [(('upload', 'set', '--help'), ['smm projects', '--project-id', 'only', 'except']),
                          (('upload', 'reconcile', '--help'), ['--expected-hub-revision', 'hub.revision']),
                          (('project', 'assign-conversation', '--help'), ['--confirm', '--project-id'])]:
        result = subprocess.run([sys.executable, '-m', 'smm_local.cli', *args], capture_output=True, text=True)
        assert result.returncode == 0
        for phrase in phrases: assert phrase in result.stdout
    path = Path(__file__).resolve().parents[1] / 'skills/smm-search/scripts/first_use.py'
    spec = importlib.util.spec_from_file_location('first_use_005', path)
    launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)
    monkeypatch.setattr(launcher, 'ensure_cli', lambda: Path('/synthetic/smm'))
    monkeypatch.setattr(launcher.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, 2, '', 'old CLI'))
    monkeypatch.setattr(sys, 'argv', ['first_use', 'upload', 'status'])
    assert launcher.main() == 1
    assert '0.4.0' in capsys.readouterr().err

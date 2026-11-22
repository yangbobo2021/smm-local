"""Confirmed dual-version reconciliation, synthetic Local/Hub only."""
import json
import sys

import pytest
from fastapi.testclient import TestClient

from smm_local import api, cli, federation
from smm_local.upload import LocalUpload
from test_005_contracts import pair, add_local, connect


def setup_control(pair, monkeypatch):
    a = add_local(pair, 'consent-a', 'A', 'private consent A')
    add_local(pair, 'consent-b', 'B', 'private consent B')
    config = connect(pair); federation.choose_upload(pair.local, 'none', [])
    request = federation._request
    monkeypatch.setattr(api, '_request', request); monkeypatch.setattr(cli, '_request', request)
    control = LocalUpload(pair.local, config, config['bound_hub_id'])
    return a, config, request, control


def head(pair, config):
    result = pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']})
    assert result.status_code == 200
    return result.json()


def web(pair):
    return TestClient(api.create_app(pair.local, auto_sync=False, sync_on_start=False,
        service_token='synthetic-consent-control'), base_url='http://127.0.0.1',
        headers={'Origin': 'http://127.0.0.1', 'X-SMM-UI': '1'})


@pytest.mark.parametrize('use', ['local', 'hub'])
def test_stale_local_generation_is_rejected_while_hub_revision_stays_unchanged(pair, monkeypatch, use):
    """TC-005-reconcile-stale-local: neither adoption may ignore the displayed local generation."""
    _, config, request, control = setup_control(pair, monkeypatch)
    with web(pair) as browser:
        shown = browser.post('/api/upload/reconcile', json={}).json()
        assert shown['local']['policy']['mode'] == shown['hub']['policy']['mode'] == 'none'
        def unavailable(config, route, payload=None):
            if route == '/upload-policy/set': raise federation.HubUnavailable('synthetic lost policy channel')
            return request(config, route, payload)
        monkeypatch.setattr(federation, '_request', unavailable)
        changed = federation.choose_upload(pair.local, 'all', [])
        monkeypatch.setattr(federation, '_request', request)
        assert changed['state'] == 'pending' and changed['generation'] != shown['local']['generation']
        assert head(pair, config)['revision'] == shown['hub']['revision']
        before = control.row(); remote_before = head(pair, config); marker = len(pair.calls)
        result = browser.post('/api/upload/reconcile', json={'use': use,
            'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
        assert result.status_code == 400, 'old displayed none must not adopt or confirm a different local all'
        assert '本机' in result.json()['detail'] and '重新' in result.json()['detail']
        assert control.row() == before and head(pair, config) == remote_before
        assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])


@pytest.mark.parametrize('use', ['local', 'hub'])
def test_local_change_during_hub_read_is_rejected_at_the_write_boundary(pair, monkeypatch, use):
    """TC-005-reconcile-write-window: initial validation is not sufficient."""
    _, config, request, control = setup_control(pair, monkeypatch)
    shown = control.reconcile(request); changed = {}
    def concurrent(config, route, payload=None):
        result = request(config, route, payload)
        if route == '/upload-policy/status' and not changed:
            control.choose('all', [])
            changed['row'] = control.row()
        return result
    monkeypatch.setattr(api, '_request', concurrent)
    remote_before = head(pair, config); marker = len(pair.calls)
    with web(pair) as browser:
        result = browser.post('/api/upload/reconcile', json={'use': use,
            'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
    assert changed['row']['desired']['mode'] == 'all'
    assert result.status_code == 400, 'a write after the initial snapshot must not be overwritten'
    assert control.row() == changed['row'] and head(pair, config) == remote_before
    assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])


def test_cli_requires_both_displayed_versions_and_accepts_a_fresh_pair(pair, monkeypatch, capsys):
    """TC-005-reconcile-cli-inputs: missing values cannot silently save another submission."""
    _, config, request, control = setup_control(pair, monkeypatch)
    def invoke(arguments):
        capsys.readouterr()
        monkeypatch.setattr(sys, 'argv', ['smm', '--db', str(pair.local.db_path), *arguments])
        try: cli.main(); code = 0
        except SystemExit as exc: code = exc.code
        captured = capsys.readouterr()
        return code, captured.out, captured.err
    code, output, _ = invoke(['upload', 'reconcile']); assert code == 0
    shown = json.loads(output); generation = shown['local']['generation']; revision = shown['hub']['revision']
    before = control.row(); remote_before = head(pair, config)
    bad_arguments = [ ['--expected-hub-revision', str(revision)],
                      ['--expected-local-generation', str(generation)], [],
                      ['--expected-hub-revision', str(revision), '--expected-local-generation', '-1'],
                      ['--expected-hub-revision', str(revision), '--expected-local-generation', 'not-an-integer'] ]
    for arguments in bad_arguments:
        code, output, error = invoke(['upload', 'reconcile', '--use', 'local', *arguments])
        assert code != 0, 'missing/invalid consent snapshot versions must fail before saving'
        assert error and not output
        assert control.row() == before and head(pair, config) == remote_before
    code, help_text, _ = invoke(['upload', 'reconcile', '--help']); assert code == 0
    assert '--expected-local-generation' in help_text and 'local.generation' in help_text
    assert '--expected-hub-revision' in help_text and 'hub.revision' in help_text
    code, output, _ = invoke(['upload', 'reconcile', '--use', 'local', '--expected-hub-revision', str(revision),
        '--expected-local-generation', str(generation)])
    assert code == 0
    assert json.loads(output)['state'] == 'confirmed'
    assert json.loads(output)['policy'] == head(pair, config)['policy'] == {'mode': 'none', 'projects': []}


@pytest.mark.parametrize('mode', ['none', 'all', 'only', 'except'])
def test_fresh_displayed_rules_are_submitted_exactly_for_all_modes(pair, monkeypatch, mode):
    """TC-005-reconcile-fresh: reject-all is not an acceptable stale-view repair."""
    a, config, _, control = setup_control(pair, monkeypatch)
    control.choose(mode, [a['project_id']] if mode in ('only', 'except') else [])
    with web(pair) as browser:
        shown = browser.post('/api/upload/reconcile', json={}).json()
        expected = shown['local']['policy']; assert expected['mode'] == mode
        marker = len(pair.calls)
        result = browser.post('/api/upload/reconcile', json={'use': 'local',
            'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
    assert result.status_code == 200, result.text
    assert result.json()['state'] == 'confirmed'
    assert result.json()['policy'] == expected == control.row()['desired'] == head(pair, config)['policy']
    submissions = [payload['policy'] for route, payload in pair.calls[marker:] if route == '/upload-policy/set']
    assert submissions == [expected]
    assert not any(route == '/upload' and payload['records'] for route, payload in pair.calls[marker:])


def test_web_reconcile_requires_valid_versions_without_mutating_either_rule(pair, monkeypatch):
    """TC-005-reconcile-web-inputs: Web adoption always uses its displayed pair."""
    _, config, request, control = setup_control(pair, monkeypatch)
    shown = control.reconcile(request); revision = shown['hub']['revision']; generation = shown['local']['generation']
    before = control.row(); remote_before = head(pair, config)
    bad = [{'use': 'local', 'expected_hub_revision': revision},
           {'use': 'hub', 'expected_hub_revision': revision},
           {'use': 'hub', 'expected_local_generation': generation},
           {'use': 'local', 'expected_hub_revision': revision, 'expected_local_generation': -1},
           {'use': 'local', 'expected_hub_revision': revision, 'expected_local_generation': True},
           {'use': 'local', 'expected_hub_revision': revision, 'expected_local_generation': 'not-a-generation'},
           {'use': 'local', 'expected_hub_revision': True, 'expected_local_generation': generation}]
    with web(pair) as browser:
        for payload in bad:
            marker = len(pair.calls); result = browser.post('/api/upload/reconcile', json=payload)
            assert result.status_code in (400, 422), 'missing or invalid displayed versions must not save a rule'
            assert control.row() == before and head(pair, config) == remote_before
            assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])

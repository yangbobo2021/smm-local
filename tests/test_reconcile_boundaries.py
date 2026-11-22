"""Caller variants of the shared reconciliation write fence."""
import json
import sys

import pytest
from fastapi.testclient import TestClient

from smm_local import api, cli, federation
from smm_local.core import Archive
from smm_hub.hub import create_hub
from test_005_contracts import pair
from test_reconcile_snapshot import setup_control, head, web


def test_cli_hub_without_version_option_protects_changes_during_its_call(pair, monkeypatch, capsys):
    _, config, request, control = setup_control(pair, monkeypatch)
    changed = {}
    def concurrent(config, route, payload=None):
        reply = request(config, route, payload)
        if route == '/upload-policy/status' and not changed:
            control.choose('all', [])
            changed['row'] = control.row()
        return reply
    monkeypatch.setattr(cli, '_request', concurrent)
    before = head(pair, config); marker = len(pair.calls)
    monkeypatch.setattr(sys, 'argv', ['smm', '--db', str(pair.local.db_path), 'upload', 'reconcile', '--use', 'hub'])
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code != 0 and '本机规则已改变' in capsys.readouterr().err
    assert changed['row']['desired']['mode'] == 'all' and control.row() == changed['row']
    assert head(pair, config) == before
    assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])


def test_hub_switch_during_reconcile_keeps_new_target_query_only(pair, monkeypatch):
    _, config, request, control = setup_control(pair, monkeypatch)
    shown = control.reconcile(request); before = control.row(); remote_before = head(pair, config)
    other = Archive(pair.local.db_path.parent / 'other-hub.sqlite3')
    token = pair.token_file.read_text(); address = 'http://localhost:18771'
    with TestClient(create_hub(other, token), headers={'Authorization': 'Bearer ' + token}) as server:
        other_id = server.get('/v1/info').json()['hub_id']; assert other_id != pair.hub_id
        def routed(cfg, route, payload=None):
            if cfg['address'] != address: return request(cfg, route, payload)
            pair.calls.append((route, json.loads(json.dumps(payload))))
            reply = server.get('/v1' + route) if payload is None else server.post('/v1' + route, json=payload)
            assert reply.status_code < 400, reply.text
            return reply.json()
        switched = {}
        def concurrent(cfg, route, payload=None):
            reply = routed(cfg, route, payload)
            if route == '/upload-policy/status' and not switched:
                switched.update(federation.configure_hub(pair.local, address, 'new-target', str(pair.token_file)))
                assert switched['connected']
            return reply
        monkeypatch.setattr(federation, '_request', routed); monkeypatch.setattr(api, '_request', concurrent)
        marker = len(pair.calls)
        with web(pair) as browser:
            response = browser.post('/api/upload/reconcile', json={'use': 'local',
                'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
        assert response.status_code == 400 and '连接已改变' in response.json()['detail']
        assert control.row() == before and head(pair, config) == remote_before
        assert federation.hub_config(pair.local)['bound_hub_id'] == other_id
        state = federation.upload_status(pair.local)
        assert state['state'] == 'needs_selection' and state['policy'] is None
        assert other.status()['messages'] == 0
        assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])

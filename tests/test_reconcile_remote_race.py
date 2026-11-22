"""Reconciliation must not commit the local rule before the remote CAS accepts it."""
import json
import sys

import pytest

from smm_local import api, cli, federation
from test_005_contracts import pair, bodies
from test_reconcile_snapshot import setup_control, head, web


@pytest.mark.parametrize('use', ['local', 'hub'])
@pytest.mark.parametrize('window', ['first-status', 'second-status', 'cas'])
@pytest.mark.parametrize('entrance', ['web', 'cli'])
def test_remote_rejection_preserves_the_local_rule_and_newer_hub_head(pair, monkeypatch, capsys, use, window, entrance):
    """TC-005-reconcile-remote-race: a rejection cannot save an unconfirmed rule."""
    _, config, request, control = setup_control(pair, monkeypatch)
    initial = head(pair, config)
    external = pair.client.post('/v1/upload-policy/set', json={'hub_id': pair.hub_id,
        'device_id': config['device_id'], 'expected_revision': initial['revision'],
        'submission_id': 'external-all', 'policy': {'mode': 'all', 'projects': []}})
    assert external.status_code == 200
    shown = control.reconcile(request); before = control.row(); body_before = bodies(pair.remote)
    injected = {}; reads = 0
    def advance():
        current = head(pair, config)
        reply = pair.client.post('/v1/upload-policy/set', json={'hub_id': pair.hub_id,
            'device_id': config['device_id'], 'expected_revision': current['revision'],
            'submission_id': 'newer-stop', 'policy': {'mode': 'none', 'projects': []}})
        assert reply.status_code == 200
        injected['head'] = head(pair, config)
    def concurrent(cfg, route, payload=None):
        nonlocal reads
        if route == '/upload-policy/set' and window == 'cas' and not injected:
            advance()
        if route == '/upload-policy/status':
            result = request(cfg, route, payload); reads += 1
            if not injected and ((window == 'first-status' and reads == 1) or
                                 (window == 'second-status' and reads == 2)):
                advance()
            return result
        if route == '/upload-policy/set':
            # Preserve the real application's HTTP CAS rejection; the pair's
            # generic request helper assumes successful responses only.
            pair.calls.append((route, json.loads(json.dumps(payload))))
            response = pair.client.post('/v1' + route, json=payload)
            if response.status_code == 409:
                raise federation.HubUnavailable('Hub 状态、规则或项目登记已改变，请重新检索或查看上传差异', status=409)
            assert response.status_code == 200, response.text
            return response.json()
        return request(cfg, route, payload)
    monkeypatch.setattr(api, '_request', concurrent); monkeypatch.setattr(cli, '_request', concurrent)
    marker = len(pair.calls)
    if entrance == 'web':
        with web(pair) as browser:
            reply = browser.post('/api/upload/reconcile', json={'use': use,
                'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
        assert reply.status_code in (400, 409, 502, 503), reply.text
        assert '改变' in reply.json()['detail'] or '重新' in reply.json()['detail']
    else:
        capsys.readouterr()
        monkeypatch.setattr(sys, 'argv', ['smm', '--db', str(pair.local.db_path), 'upload', 'reconcile', '--use', use,
            '--expected-hub-revision', str(shown['hub']['revision']), '--expected-local-generation', str(shown['local']['generation'])])
        with pytest.raises(SystemExit) as failure: cli.main()
        output = capsys.readouterr(); assert failure.value.code != 0 and not output.out
        assert '改变' in output.err or '重新' in output.err
    assert injected, 'the intended remote race must actually occur'
    assert control.row() == before, 'a rejected reconciliation must leave the complete previous local rule unchanged'
    assert head(pair, config) == injected['head']
    assert bodies(pair.remote) == body_before
    assert not any(route == '/upload' and payload.get('records') for route, payload in pair.calls[marker:])

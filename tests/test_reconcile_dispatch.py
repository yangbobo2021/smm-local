"""A target switch after saving still fences the subsequent control dispatch."""
import json

from fastapi.testclient import TestClient

from smm_local import api, federation
from smm_local.core import Archive
from smm_hub.hub import create_hub
from test_005_contracts import pair
from test_reconcile_snapshot import setup_control, head, web


def test_second_hub_read_switch_cannot_dispatch_policy_to_the_old_target(pair, monkeypatch):
    """TC-005-reconcile-target-dispatch: inject after the local conditional save."""
    _, config, request, control = setup_control(pair, monkeypatch)
    shown = control.reconcile(request); old_head = head(pair, config)
    other = Archive(pair.local.db_path.parent / 'other-after-save.sqlite3')
    token = pair.token_file.read_text(); address = 'http://localhost:18772'
    with TestClient(create_hub(other, token), headers={'Authorization': 'Bearer ' + token}) as server:
        other_id = server.get('/v1/info').json()['hub_id']; assert other_id != pair.hub_id
        def routed(cfg, route, payload=None):
            if cfg['address'] != address: return request(cfg, route, payload)
            pair.calls.append((route, json.loads(json.dumps(payload))))
            reply = server.get('/v1' + route) if payload is None else server.post('/v1' + route, json=payload)
            assert reply.status_code < 400, reply.text
            return reply.json()
        observed = {'status_reads': 0}
        def concurrent(cfg, route, payload=None):
            reply = routed(cfg, route, payload)
            if route == '/upload-policy/status':
                observed['status_reads'] += 1
                if observed['status_reads'] == 2:
                    observed['saved'] = control.row()
                    assert observed['saved']['generation'] > shown['local']['generation']
                    assert observed['saved']['state'] == 'pending'
                    switched = federation.configure_hub(pair.local, address, 'after-save-target', str(pair.token_file))
                    assert switched['connected']
                    observed['switched'] = federation.hub_config(pair.local)['bound_hub_id']
            return reply
        monkeypatch.setattr(federation, '_request', routed); monkeypatch.setattr(api, '_request', concurrent)
        marker = len(pair.calls)
        with web(pair) as browser:
            result = browser.post('/api/upload/reconcile', json={'use': 'local',
                'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
        assert observed['switched'] == other_id
        assert result.status_code == 400, 'the second status RPC must not permit a new dispatch to the old target'
        assert head(pair, config) == old_head
        assert not any(route == '/upload-policy/set' for route, _ in pair.calls[marker:])
        assert control.row()['state'] != 'confirmed'
        current = federation.upload_status(pair.local)
        assert current['hub_id'] == other_id and current['state'] == 'needs_selection' and current['policy'] is None
        assert other.status()['messages'] == 0

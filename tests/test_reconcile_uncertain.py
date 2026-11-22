"""Unknown reconcile receipts and a concurrent newer local choice remain safe."""
import pytest
from smm_local import api, federation
from test_005_contracts import pair, bodies
from test_reconcile_snapshot import setup_control, head, web


@pytest.mark.parametrize('window', ['lost-receipt', 'new-local-choice'])
def test_remote_reconcile_acceptance_cannot_overwrite_a_new_choice_or_authorize_unknown_upload(pair, monkeypatch, window):
    """TC-005-reconcile-inflight: after dispatch preserve uncertainty and newer saves."""
    _, config, request, control = setup_control(pair, monkeypatch)
    # A pending all is deliberately chosen without sending it to Hub yet.
    control.choose('all', [])
    shown = control.reconcile(request); before = control.row(); observed = {}
    def concurrent(cfg, route, payload=None):
        reply = request(cfg, route, payload)
        if route == '/upload-policy/set' and not observed:
            observed['receipt'] = reply
            if window == 'lost-receipt':
                raise federation.HubUnavailable('synthetic lost reconciliation receipt')
            control.choose('none', [])
            observed['newer'] = control.row()
        return reply
    monkeypatch.setattr(api, '_request', concurrent)
    marker = len(pair.calls)
    with web(pair) as browser:
        reply = browser.post('/api/upload/reconcile', json={'use': 'local',
            'expected_hub_revision': shown['hub']['revision'], 'expected_local_generation': shown['local']['generation']})
    assert reply.status_code in (400, 503) if window == 'lost-receipt' else reply.status_code in (200, 400, 503)
    assert observed['receipt']['policy']['mode'] == 'all'
    assert head(pair, config)['policy']['mode'] == 'all'
    if window == 'lost-receipt':
        assert control.row()['desired'] == before['desired']
        assert control.status()['state'] != 'confirmed'
    else:
        assert {k: control.row()[k] for k in ('generation', 'desired', 'submission_id')} == {k: observed['newer'][k] for k in ('generation', 'desired', 'submission_id')}
    # A normal retry is not an explicit decision to accept an unknown result.
    federation.push_pending(pair.local)
    assert not bodies(pair.remote)
    assert not any(route == '/upload' and payload.get('records') for route, payload in pair.calls[marker:])
    if window == 'lost-receipt':
        assert control.status()['state'] == 'conflict'
        fresh = control.reconcile(request)
        result = control.reconcile(request, use='hub', expected_hub_revision=fresh['hub']['revision'],
            expected_local_generation=fresh['local']['generation'])
        assert result['state'] == 'confirmed' and result['policy']['mode'] == 'all'
    else:
        assert head(pair, config)['policy']['mode'] == control.row()['desired']['mode'] == 'none'

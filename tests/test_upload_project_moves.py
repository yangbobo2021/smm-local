"""Approved affiliation propagation; no live source or user archive access."""
import pytest

from smm_local import federation, project_control
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect


def project_hits(pair, config, key):
    scope = pair.client.post('/v1/query-scope', json={'hub_id': pair.hub_id,
        'device_id': config['device_id'], 'project_id': key})
    assert scope.status_code == 200, scope.text
    result = pair.client.post('/v1/search', json={'query': 'moving', 'device_id': config['device_id'],
        'scope_reference': scope.json()['scope_reference']})
    assert result.status_code == 200, result.text
    return {h['source_session_id']: h for h in result.json()['results']}


def physical_rows(pair):
    with pair.remote.connect() as con:
        return [tuple(r) for r in con.execute("SELECT m.id,m.source_key,m.position,m.role,m.text,m.timestamp FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.source_session_id='move-a' ORDER BY m.id")]


def move(pair, a, b, operation):
    data = ({'conversation_id': a['id'], 'target_id': b['project_id']} if operation == 'assign' else
            {'source_id': a['project_id'], 'target_id': b['project_id']} if operation == 'merge' else
            {'path': str(pair.histories.parent / 'A'), 'target_id': b['project_id']})
    preview = project_control.change(pair.local, operation, data, always_preview=True)
    assert preview['requires_confirmation'] and not preview['applied']
    assert project_control.change(pair.local, operation, data, preview['confirmation'])['applied']
    assert pair.local.read(a['id'])['project_id'] == b['project_id']


@pytest.mark.parametrize('operation', ['assign', 'map', 'merge'])
def test_received_message_gets_new_allowed_project_without_body_reupload(pair, operation):
    """TC-005-move-project: forbid B first, then attach already received A to B."""
    a = add_local(pair, 'move-a', 'A', 'moving A original')
    b = add_local(pair, 'move-b', 'B', 'moving B original')
    config = connect(pair); federation.choose_upload(pair.local, 'only', [a['project_id']])
    assert federation.push_pending(pair.local)['uploaded'] == 1
    keys = {p['name']: p['source_key'] for p in HubProjects(pair.remote).list()}
    old = project_hits(pair, config, keys['A'])['move-a']['reference']
    before = physical_rows(pair)
    move(pair, a, b, operation)
    marker = len(pair.calls)
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert not any(route == '/known-upload-messages' or (route == '/upload' and data['records'])
                   for route, data in pair.calls[marker:])
    assert 'move-a' not in project_hits(pair, config, keys['B'])
    assert 'move-a' in project_hits(pair, config, keys['A'])
    federation.choose_upload(pair.local, 'only', [b['project_id']])
    marker = len(pair.calls)
    assert federation.push_pending(pair.local)['uploaded'] == 1  # B's own previously forbidden original.
    new = project_hits(pair, config, keys['B'])
    assert 'move-a' in new, 'confirmed A body still needs a separate B affiliation confirmation'
    for reference in [old, new['move-a']['reference']]:
        read = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': reference})
        assert read.status_code == 200
        assert [m['text'] for m in read.json()['messages']] == ['moving A original']
    assert 'move-a' in project_hits(pair, config, keys['A'])
    assert physical_rows(pair) == before
    assert not any(r['text'] == 'moving A original' for route, data in pair.calls[marker:]
                   if route == '/upload' for r in data['records'])
    assert federation.upload_status(pair.local)['allowed_pending_messages'] == 0
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert physical_rows(pair) == before


def test_lost_project_confirmation_retries_without_using_old_project_receipt(pair, monkeypatch):
    """TC-005-move-retry: a lost metadata acknowledgment stays pending for B."""
    a = add_local(pair, 'move-a', 'A', 'moving A original')
    b = add_local(pair, 'move-b', 'B', 'moving B original')
    config = connect(pair); federation.choose_upload(pair.local, 'all', [])
    assert federation.push_pending(pair.local)['uploaded'] == 2
    keys = {p['name']: p['source_key'] for p in HubProjects(pair.remote).list()}
    old = project_hits(pair, config, keys['A'])['move-a']['reference']
    before = physical_rows(pair)
    move(pair, a, b, 'assign')
    request = federation._request
    def lost(config, route, payload=None):
        result = request(config, route, payload)
        if route == '/known-upload-messages':
            raise federation.HubUnavailable('synthetic project confirmation lost')
        return result
    monkeypatch.setattr(federation, '_request', lost)
    result = federation.push_pending(pair.local)
    assert result['errors'] and result['pending'], 'A receipt cannot claim the new B affiliation was confirmed'
    assert 'move-a' in project_hits(pair, config, keys['B'])  # Hub did persist it before the reply was lost.
    state = federation.upload_status(pair.local)
    assert state['state'] == 'confirmed' and state['allowed_pending_messages'] == 1
    assert state['transfer_state'] == 'failed'
    monkeypatch.setattr(federation, '_request', request)
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert federation.upload_status(pair.local)['allowed_pending_messages'] == 0
    assert physical_rows(pair) == before
    assert pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': old}).json()['messages'][0]['text'] == 'moving A original'

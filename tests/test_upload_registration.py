"""A newly registered query-only client also fences a still-running legacy writer."""
from smm_local import federation
from test_005_contracts import pair, add_local, connect, bodies


def test_query_only_registration_fences_same_device_legacy_writer(pair):
    """TC-005-register: new connection adopts a fence before any upload choice."""
    add_local(pair, 'new-device', 'A', 'private before choice')
    config = connect(pair)
    assert federation.upload_status(pair.local)['state'] == 'needs_selection'
    batch = {'hub_id': pair.hub_id, 'device_id': config['device_id'], 'device_name': 'legacy still running',
             'records': [{'source': 'codex', 'source_session_id': 'new-device', 'started_at': None,
                          'source_key': 'legacy-message', 'position': 1, 'source_order': 1,
                          'role': 'user', 'text': 'private before choice', 'timestamp': None}]}
    # A distinct device not adopting new controls remains a valid legacy writer.
    other_record = {**batch['records'][0], 'source_session_id': 'other-device', 'text': 'other-device received history'}
    other = pair.client.post('/v1/upload', json={**batch, 'device_id': 'e' * 32, 'records': [other_record]})
    assert other.status_code == 200, other.text
    response = pair.client.post('/v1/upload', json=batch)
    assert response.status_code == 409, 'new client registration must fence the same device legacy writer before choice'
    assert bodies(pair.remote) == ['other-device received history']
    hit = pair.client.post('/v1/search', json={'query': 'received'}).json()['results'][0]
    read = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'conversation_id': hit['id'],
                                          'message_id': hit['matched_messages'][0]['hub_message_id']})
    assert read.status_code == 200
    assert [m['text'] for m in read.json()['messages']] == ['other-device received history']

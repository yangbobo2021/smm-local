"""Reproductions found by the independent b76 review; synthetic archives only."""
import json

from fastapi.testclient import TestClient

from smm_local import federation
from smm_local.core import Archive
from smm_hub.hub import create_hub
from test_005_contracts import pair, add_local, connect, bodies


def test_late_offset_prefix_preserves_two_identical_turns(pair):
    """TC-005-offset-prefix: late prefix cannot consume an existing turn's receipt."""
    path = pair.histories / 'offset-prefix.jsonl'
    meta = {'type': 'session_meta', 'payload': {'id': 'offset-prefix', 'cwd': str(pair.histories.parent / 'A')}}
    event = {'type': 'response_item', 'ordinal': 2, 'timestamp': '2026-11-20T10:00:00Z',
             'payload': {'type': 'message', 'role': 'user',
                         'content': [{'type': 'input_text', 'text': 'identical repeated turn'}]}}
    path.write_text(json.dumps(meta) + '\n' + json.dumps(event) + '\n')
    assert pair.local.sync_codex(pair.histories)['messages_new'] == 1
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    assert federation.push_pending(pair.local)['uploaded'] == 1
    with path.open('a') as out:
        out.write(json.dumps({**event, 'ordinal': 1}) + '\n')
    assert pair.local.sync_codex(pair.histories)['messages_new'] == 1
    federation.push_pending(pair.local)
    assert bodies(pair.remote) == ['identical repeated turn'] * 2
    with pair.remote.connect() as con:
        origins = [tuple(r) for r in con.execute('SELECT source_position,source_order FROM hub_origins ORDER BY source_order')]
    assert origins == [(1, 1), (2, 2)]
    assert federation.push_pending(pair.local)['pending'] is False
    assert federation.upload_status(pair.local)['confirmed_messages'] == 2


def test_target_switch_during_known_lookup_fences_old_body(pair, monkeypatch, tmp_path):
    """TC-005-target-dispatch: a newly chosen target fences not-yet-dispatched body."""
    add_local(pair, 'a', 'A', 'must not start to old hub after switch')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    old_request = federation._request
    second = Archive(tmp_path / 'second-hub.sqlite3')
    with TestClient(create_hub(second, pair.token_file.read_text())) as client:
        client.headers['Authorization'] = 'Bearer ' + pair.token_file.read_text()
        switched = False
        def request(config, route, payload=None):
            nonlocal switched
            if config['address'] == 'http://localhost:18771':
                response = client.get('/v1' + route) if payload is None else client.post('/v1' + route, json=payload)
                assert response.status_code == 200, response.text
                return response.json()
            result = old_request(config, route, payload)
            if route == '/known-upload-messages' and not switched:
                switched = True
                assert federation.configure_hub(pair.local, 'http://localhost:18771', 'new-target', str(pair.token_file))['connected']
            return result
        monkeypatch.setattr(federation, '_request', request)
        federation.push_pending(pair.local)
        assert switched
        assert bodies(pair.remote) == []
        assert bodies(second) == []
        assert federation.upload_status(pair.local)['state'] == 'needs_selection'


def test_timestamp_version_is_stored_before_exact_ack(pair):
    """TC-005-timestamp-version: same legacy fingerprint must not acknowledge another version."""
    add_local(pair, 'a', 'A', 'same body different source time')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    federation.push_pending(pair.local)
    old_hit = federation.search_archive(pair.local, 'different', local=False)['results'][0]
    old_hub_reference = next(r['reference'] for r in old_hit['origin_references'] if r['archive_scope'] == 'hub')
    with pair.local.connect() as con:
        con.execute("UPDATE messages SET timestamp='2026-11-20T10:00:00Z'")
    assert federation.push_pending(pair.local)['uploaded'] == 1
    with pair.remote.connect() as con:
        times = [r[0] for r in con.execute('SELECT timestamp FROM messages ORDER BY id')]
    assert times == [None, '2026-11-20T10:00:00Z']
    assert federation.upload_status(pair.local)['confirmed_messages'] == 1
    assert federation.push_pending(pair.local)['uploaded'] == 0
    old = federation.read_archive(pair.local, reference=old_hub_reference)
    assert old['messages'][0]['timestamp'] is None
    combined = federation.search_archive(pair.local, 'different')['results']
    messages = [m for h in combined for m in h['matched_messages']]
    assert len(messages) == 2
    assert {m['timestamp'] for m in messages} == {None, '2026-11-20T10:00:00Z'}


def test_body_failure_persists_in_upload_status_and_clears_after_recovery(pair, monkeypatch):
    """TC-005-transfer-status: rule confirmation and failed backfill are separate states."""
    add_local(pair, 'a', 'A', 'waiting for body transfer')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    request = federation._request
    def fail(config, route, payload=None):
        if route == '/known-upload-messages':
            raise federation.HubUnavailable('synthetic body lookup unavailable')
        return request(config, route, payload)
    monkeypatch.setattr(federation, '_request', fail)
    assert federation.push_pending(pair.local)['pending']
    state = federation.upload_status(pair.local)
    assert state['state'] == 'confirmed'
    assert state['transfer_state'] == 'failed'
    assert state['transfer_problem'] == 'synthetic body lookup unavailable'
    assert state['allowed_pending_messages'] == 1
    monkeypatch.setattr(federation, '_request', request)
    federation.push_pending(pair.local)
    state = federation.upload_status(pair.local)
    assert state['state'] == 'confirmed' and state['transfer_state'] == 'complete'
    assert state['transfer_problem'] is None
    assert state['allowed_pending_messages'] == 0

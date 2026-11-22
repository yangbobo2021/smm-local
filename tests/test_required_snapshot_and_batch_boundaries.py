"""Previously specified concurrency, batch and citation acceptance boundaries."""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from smm_local import federation, references
from smm_local.core import Archive
from smm_local.archive_protocol import ControlConflict, message_version
from smm_hub.hub import create_hub
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote, bodies


def evidence(name, value):
    directory = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
    if directory:
        path = Path(directory); path.mkdir(parents=True, exist_ok=True)
        (path / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


@pytest.mark.parametrize('window', ['scope-return', 'hub-results-return'])
def test_project_link_changes_during_one_search_do_not_mix_snapshots(pair, monkeypatch, window):
    """TC-005-scope-race: freeze both archives and the later citation reads."""
    a = add_local(pair, 'local-a', 'A', 'common private A')
    d = add_local(pair, 'local-d', 'D', 'common D')
    e = add_local(pair, 'local-e', 'E', 'common E')
    config = connect(pair); federation.choose_upload(pair.local, 'only', [d['project_id'], e['project_id']])
    federation.push_pending(pair.local, control_only=True)
    assert bodies(pair.remote) == []
    for session, name in [('remote-b', 'RemoteB'), ('remote-c', 'RemoteC')]:
        seed_remote(pair, 'common ' + name, session=session)
        reply = pair.client.post('/v1/project-metadata', json={'hub_id': pair.hub_id, 'device_id': 'b' * 32,
            'device_name': 'other-device', 'projects': [{'id': session + '-project', 'name': name}],
            'memberships': [{'source': 'codex', 'source_session_id': session, 'project_id': session + '-project'}]})
        assert reply.status_code == 200
    projects = HubProjects(pair.remote); ids = {p['name']: p['id'] for p in projects.list()}
    for name in ['D', 'RemoteB']: projects.link(ids['A'], ids[name])
    original = federation._request; observed = {'scope': [], 'hub': []}; changed = []
    def request(cfg, route, payload=None):
        reply = original(cfg, route, payload)
        if route == '/query-scope': observed['scope'].append(reply)
        if route == '/search': observed['hub'].append(reply)
        if not changed and route == ('/query-scope' if window == 'scope-return' else '/search'):
            for name in ['D', 'RemoteB']: projects.link(ids['A'], ids[name], linked=False)
            for name in ['E', 'RemoteC']: projects.link(ids['A'], ids[name])
            changed.append(projects.links())
        return reply
    monkeypatch.setattr(federation, '_request', request)
    frozen = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'], limit=50)
    assert changed and len(observed['scope']) == len(observed['hub']) == 1
    assert {p['id'] for p in frozen['effective_projects']} == {ids[k] for k in ['A', 'D', 'RemoteB']}
    assert {h['source_session_id'] for h in observed['hub'][0]['results']} == {'remote-b'}
    assert {h['source_session_id'] for h in frozen['results']} == {'local-a', 'local-d', 'remote-b'}
    assert {h['source_session_id']: h['archive_scope'] for h in frozen['results']} == {'local-a': 'local', 'local-d': 'local', 'remote-b': 'hub'}
    expected = {'local-a': 'common private A', 'local-d': 'common D', 'remote-b': 'common RemoteB'}
    original_reads = {}
    for hit in frozen['results']:
        read = federation.read_archive(pair.local, reference=hit['reference'])
        assert [m['text'] for m in read['messages']] == [expected[hit['source_session_id']]]
        original_reads[hit['source_session_id']] = read
    fresh = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'], limit=50)
    assert len(observed['scope']) == len(observed['hub']) == 2
    assert {p['id'] for p in fresh['effective_projects']} == {ids[k] for k in ['A', 'E', 'RemoteC']}
    assert {h['source_session_id'] for h in fresh['results']} == {'local-a', 'local-e', 'remote-c'}
    for hit in frozen['results']:
        assert [m['text'] for m in federation.read_archive(pair.local, reference=hit['reference'])['messages']] == [expected[hit['source_session_id']]]
    evidence('scope-race-' + window, {'changed_links': changed, 'frozen': frozen, 'reads': original_reads, 'fresh': fresh, 'endpoint_responses': observed})


@pytest.mark.parametrize('boundary', ['local-deleted-first', 'local-deleted-last', 'hub-deleted-first', 'hub-deleted-last', 'local-repeated-position', 'hub-repeated-position', 'hub-switched'])
def test_citation_message_identity_survives_repeated_positions_and_rejects_removed_targets(pair, monkeypatch, boundary):
    """TC-005-reference-boundaries: actual message identity, never integer fallback."""
    is_hub = boundary.startswith('hub-')
    if is_hub:
        add_local(pair, 'local-sentinel', 'A', 'common LOCAL WRONG ARCHIVE')
        first = seed_remote(pair, 'common first original', session='citation')
        second = {**first, 'source_key': 'citation-second', 'position': 2, 'source_order': 2, 'text': 'common second original'}
        reply = pair.client.post('/v1/upload', json={'hub_id': pair.hub_id, 'device_id': 'b' * 32,
            'device_name': 'other-device', 'records': [second]}); assert reply.status_code == 200
        db = pair.remote
    else:
        add_local(pair, 'citation', 'A', 'common first original')
        source = pair.histories / 'citation.jsonl'
        item = {'type': 'response_item', 'ordinal': 2, 'payload': {'type': 'message', 'id': 'citation-second',
            'role': 'user', 'content': [{'type': 'input_text', 'text': 'common second original'}]}}
        source.write_text(source.read_text() + json.dumps(item) + '\n'); pair.local.sync_codex(pair.histories)
        db = pair.local
    config = connect(pair)
    with db.connect() as con:
        cid = con.execute("SELECT id FROM conversations WHERE source_session_id='citation'").fetchone()[0]
        con.execute('UPDATE messages SET position=1 WHERE conversation_id=?', (cid,))
        saved = [dict(row) for row in con.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY id', (cid,))]
    assert len(saved) == 2 and [m['position'] for m in saved] == [1, 1]
    hit = next(h for h in federation.search_archive(pair.local, 'common')['results'] if h['source_session_id'] == 'citation')
    before = federation.read_archive(pair.local, reference=hit['reference'])
    assert [m['text'] for m in before['messages']] == ['common first original', 'common second original']
    if 'repeated-position' in boundary:
        for message, text in zip(db.read(cid, include_message_ids=True)['messages'], ['common first original', 'common second original']):
            ref = references.issue(db, cid, [message], scope='hub' if is_hub else 'local', hub_id=pair.hub_id if is_hub else None)
            read = federation.read_archive(pair.local, reference=ref, start=1, end=1)
            assert [m['text'] for m in read['messages']] == [text]
            stamp = references.routing_metadata(ref)['messages']
            assert len(stamp) == 1 and stamp[0]['id'] == message['_message_id']
            assert stamp[0]['version'] == message_version(message)
        evidence('reference-' + boundary, {'saved_messages': saved, 'whole_read': before})
        return
    if 'deleted' in boundary:
        deleted_index = 1 if boundary.endswith('last') else 0
        removed = saved[deleted_index]
        with db.connect() as con:
            assert con.execute('DELETE FROM messages WHERE id=?', (removed['id'],)).rowcount == 1
        with pytest.raises((ValueError, federation.HubUnavailable), match='改变|不存在|重新'):
            federation.read_archive(pair.local, reference=hit['reference'])
        assert bodies(db) == [saved[1 - deleted_index]['text']]
        evidence('reference-' + boundary, {'removed_message': removed, 'before': before, 'remaining_body': bodies(db)})
        return
    other = Archive(pair.histories.parent / 'different-hub.sqlite3'); address = 'http://localhost:18779'
    token = pair.token_file.read_text(); original = federation._request; target_calls = []
    with TestClient(create_hub(other, token), headers={'Authorization': 'Bearer ' + token}) as client:
        different_id = client.get('/v1/info').json()['hub_id']; assert different_id != pair.hub_id
        reply = client.post('/v1/upload', json={'hub_id': different_id, 'device_id': 'c' * 32, 'device_name': 'different',
            'records': [{**first, 'text': 'common NEW HUB WRONG ORIGINAL'}]}); assert reply.status_code == 200
        def request(cfg, route, payload=None):
            if cfg['address'] != address: return original(cfg, route, payload)
            target_calls.append(route)
            reply = client.get('/v1' + route) if payload is None else client.post('/v1' + route, json=payload)
            if reply.status_code >= 400: raise federation.HubUnavailable(str(reply.json()), status=reply.status_code)
            return reply.json()
        monkeypatch.setattr(federation, '_request', request)
        assert federation.configure_hub(pair.local, address, 'different', str(pair.token_file))['connected']
        assert federation.hub_config(pair.local)['bound_hub_id'] == different_id
        target_calls.clear()
        with pytest.raises(federation.HubUnavailable, match='切换|重新'):
            federation.read_archive(pair.local, reference=hit['reference'])
        assert '/read' not in target_calls
        assert bodies(other) == ['common NEW HUB WRONG ORIGINAL']
        assert bodies(pair.local) == ['common LOCAL WRONG ARCHIVE']
        evidence('reference-hub-switched', {'old_hub': pair.hub_id, 'new_hub': different_id, 'old_reference': hit['reference'], 'read_calls_to_new_hub': target_calls})


def test_allow_stop_allow_commits_and_delayed_requests_and_replies_keep_the_latest_head(pair, monkeypatch):
    """TC-005-policy-triple-order: three choices, old responses and old requests."""
    item = add_local(pair, 'triple', 'A', 'triple final permitted body'); config = connect(pair)
    original = federation._request; stage = 0; commits = []; returns = []; states = []
    def request(cfg, route, payload=None):
        nonlocal stage
        reply = original(cfg, route, payload)
        if route == '/upload-policy/set':
            commits.append({'request': payload, 'receipt': reply})
            if stage == 0:
                assert payload['policy']['mode'] == 'all'; stage = 1
                states.append(federation.choose_upload(pair.local, 'none', []))
            elif stage == 1:
                assert payload['policy']['mode'] == 'none'; stage = 2
                states.append(federation.choose_upload(pair.local, 'all', []))
            returns.append(reply['revision'])
        return reply
    monkeypatch.setattr(federation, '_request', request)
    final = federation.choose_upload(pair.local, 'all', [])
    assert [c['receipt']['policy']['mode'] for c in commits] == ['all', 'none', 'all']
    assert [c['receipt']['revision'] for c in commits] == [1, 2, 3] and returns == [3, 2, 1]
    assert final['state'] == 'confirmed' and final['policy']['mode'] == 'all' and final['generation'] == 3
    head_before = pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']}).json()
    assert head_before['revision'] == 3 and head_before['policy']['mode'] == 'all'
    latest = commits[-1]['receipt']
    assert final['hub_revision'] == 3 and final['control_epoch'] == latest['control_epoch']
    assert final['remote']['submission_id'] == latest['submission_id'] and final['remote']['revision'] == 3
    row = federation.upload_control(pair.local).row()
    assert row['submission_id'] == latest['submission_id']
    assert row['ack_generation'] == row['generation'] == 3 and row['ack_revision'] == 3
    assert row['ack_epoch'] == latest['control_epoch']
    for old in reversed(commits[:2]):
        replay = pair.client.post('/v1/upload-policy/set', json=old['request']); assert replay.status_code == 200
        assert replay.json()['revision'] == old['receipt']['revision']
        assert pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']}).json() == head_before
    delayed = {**commits[1]['request'], 'submission_id': 'late-uncommitted-stop'}
    assert pair.client.post('/v1/upload-policy/set', json=delayed).status_code == 409
    assert pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']}).json() == head_before
    assert federation.upload_status(pair.local)['generation'] == 3
    federation.push_pending(pair.local); assert bodies(pair.remote) == ['triple final permitted body']
    federation.push_pending(pair.local); assert bodies(pair.remote) == ['triple final permitted body']
    evidence('policy-triple-order', {'commits': commits, 'return_revisions': returns, 'nested_states': states, 'final': federation.upload_status(pair.local), 'hub_head': head_before})


@pytest.mark.parametrize('fault', ['before-commit', 'partial-receipt'])
def test_uncommitted_whole_batch_and_partially_invalid_receipt_never_acknowledge_rows(pair, monkeypatch, fault):
    """TC-005-batch-failure: unknown is not accepted, then retry is complete/idempotent."""
    add_local(pair, 'batch-a1', 'A', 'batch first original'); add_local(pair, 'batch-a2', 'A', 'batch second original')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    original = federation._request; attempts = []
    def request(cfg, route, payload=None):
        if route == '/upload' and payload.get('records'):
            attempts.append(payload); assert len(payload['records']) == 2
            if fault == 'before-commit': raise federation.HubUnavailable('synthetic whole batch failed before server commit')
            reply = original(cfg, route, payload)
            return {**reply, 'accepted': 1}
        return original(cfg, route, payload)
    monkeypatch.setattr(federation, '_request', request)
    if fault == 'before-commit':
        result = federation.push_pending(pair.local); assert result['errors'] and result['uploaded'] == 0
    else:
        with pytest.raises(ControlConflict): federation.push_pending(pair.local)
    status = federation.upload_status(pair.local)
    assert attempts and status['confirmed_messages'] == 0 and status['allowed_pending_messages'] == 2
    assert status['inflight_messages'] == 2
    assert bodies(pair.remote) == ([] if fault == 'before-commit' else ['batch first original', 'batch second original'])
    monkeypatch.setattr(federation, '_request', original)
    federation.push_pending(pair.local); done = federation.upload_status(pair.local)
    assert done['confirmed_messages'] == 2 and done['allowed_pending_messages'] == done['inflight_messages'] == 0
    assert bodies(pair.remote) == ['batch first original', 'batch second original']
    federation.push_pending(pair.local); assert bodies(pair.remote) == ['batch first original', 'batch second original']
    evidence('batch-' + fault, {'attempts': attempts, 'failed_state': status, 'recovered_state': done, 'hub_body': bodies(pair.remote)})


@pytest.mark.parametrize('order', ['allowed-first', 'forbidden-first'])
def test_current_revision_mixed_allowed_forbidden_batch_is_rejected_as_a_whole(pair, order):
    """TC-005-mixed-batch: no permitted prefix may commit from an invalid batch."""
    a = add_local(pair, 'forbidden-a', 'A', 'forbidden batch A'); b = add_local(pair, 'allowed-b', 'B', 'allowed batch B')
    config = connect(pair); state = federation.choose_upload(pair.local, 'only', [b['project_id']])
    federation.push_pending(pair.local, control_only=True)
    projects = {p['id']: p['stable_key'] for p in pair.local.projects()}
    registered = {p['source_key'] for p in HubProjects(pair.remote).list() if p['owner'] == config['device_id']}
    assert {projects[a['project_id']], projects[b['project_id']]} <= registered
    def record(item, session, text):
        return {'source': 'codex', 'source_session_id': session, 'started_at': None, 'source_key': session + '-message',
                'position': 1, 'source_order': 1, 'role': 'user', 'text': text, 'timestamp': None, 'project_id': projects[item['project_id']]}
    allowed = record(b, 'allowed-b', 'allowed batch B'); forbidden = record(a, 'forbidden-a', 'forbidden batch A')
    records = [allowed, forbidden] if order == 'allowed-first' else [forbidden, allowed]
    status = pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']}).json()
    batch = {'hub_id': pair.hub_id, 'device_id': config['device_id'], 'device_name': 'synthetic-device',
        'policy_revision': status['revision'], 'control_epoch': status['control_epoch'], 'batch_id': 'mixed-' + order, 'records': records}
    before = bodies(pair.remote); reply = pair.client.post('/v1/upload', json=batch)
    assert reply.status_code == 403 and reply.json()['detail']['code'] == 'project_disabled'
    assert bodies(pair.remote) == before == []
    receipts = pair.client.post('/v1/upload-receipts', json={'hub_id': pair.hub_id, 'device_id': config['device_id'], 'batch_ids': [batch['batch_id']]}).json()
    assert receipts['receipts'] == []
    positive = pair.client.post('/v1/upload', json={**batch, 'batch_id': 'valid-' + order, 'records': [allowed]})
    assert positive.status_code == 200 and positive.json()['accepted'] == 1
    assert bodies(pair.remote) == ['allowed batch B']
    evidence('mixed-batch-' + order, {'request': batch, 'rejection': {'status': reply.status_code, 'body': reply.json()}, 'receipts_after_rejection': receipts, 'permitted_control': positive.json(), 'final_body': bodies(pair.remote)})

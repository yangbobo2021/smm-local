"""Independent oracles added after final candidate preparation review."""
import json
import sqlite3

import pytest

from smm_local import federation
from smm_local.core import Archive
from smm_local.upload import LocalUpload
from smm_local.archive_protocol import ControlConflict
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect
from test_upload_project_moves import move, project_hits


def message_rows(pair):
    with pair.remote.connect() as con:
        return [tuple(r) for r in con.execute('SELECT c.source_session_id,m.id,m.source_key,m.position,m.role,m.text,m.timestamp FROM messages m JOIN conversations c ON c.id=m.conversation_id ORDER BY m.id')]


def add_second(pair, session, text):
    row = {'type': 'response_item', 'ordinal': 2, 'payload': {'type': 'message',
        'id': session + '-second', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': text}]}}
    with (pair.histories / (session + '.jsonl')).open('a') as f: f.write(json.dumps(row) + '\n')
    pair.local.sync_codex()


@pytest.mark.parametrize('operation', ['assign', 'map', 'merge'])
def test_all_affected_messages_and_conversations_receive_the_allowed_project(pair, operation):
    """TC-005-move-batch: no first-message or first-conversation shortcut."""
    a1 = add_local(pair, 'batch-a1', 'A', 'moving first A user')
    a2 = add_local(pair, 'batch-a2', 'A', 'moving second A user')
    add_second(pair, 'batch-a1', 'moving first A assistant')
    add_second(pair, 'batch-a2', 'moving second A assistant')
    b = add_local(pair, 'batch-b', 'B', 'moving B user')
    config = connect(pair); federation.choose_upload(pair.local, 'only', [a1['project_id']])
    assert federation.push_pending(pair.local)['uploaded'] == 4
    keys = {p['name']: p['source_key'] for p in HubProjects(pair.remote).list()}
    old = project_hits(pair, config, keys['A']); assert set(old) == {'batch-a1', 'batch-a2'}
    expected = {'batch-a1': ['moving first A user', 'moving first A assistant'],
                'batch-a2': ['moving second A user', 'moving second A assistant']}
    physical = message_rows(pair); assert len(physical) == 4
    move(pair, a1, b, operation)
    moved = {'batch-a1'} if operation == 'assign' else {'batch-a1', 'batch-a2'}
    marker = len(pair.calls); assert federation.push_pending(pair.local)['uploaded'] == 0
    assert not any(route == '/known-upload-messages' or (route == '/upload' and payload['records'])
                   for route, payload in pair.calls[marker:])
    assert not project_hits(pair, config, keys['B'])
    federation.choose_upload(pair.local, 'only', [b['project_id']]); marker = len(pair.calls)
    assert federation.push_pending(pair.local)['uploaded'] == 1  # B's original only.
    destination = project_hits(pair, config, keys['B'])
    assert set(destination) == moved | {'batch-b'}
    for session in moved:
        read = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': destination[session]['reference']})
        assert read.status_code == 200
        assert [m['text'] for m in read.json()['messages']] == expected[session]
        assert [m['role'] for m in read.json()['messages']] == ['user', 'assistant']
    assert set(project_hits(pair, config, keys['A'])) == set(expected)
    for session in expected:
        read = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': old[session]['reference']})
        assert read.status_code == 200
        assert [m['text'] for m in read.json()['messages']] == expected[session]
    assert [r for r in message_rows(pair) if r[0] != 'batch-b'] == physical
    assert not any(r['text'].startswith(('moving first A', 'moving second A'))
                   for route, payload in pair.calls[marker:] if route == '/upload' for r in payload['records'])
    assert federation.upload_status(pair.local)['allowed_pending_messages'] == 0
    before = message_rows(pair); assert federation.push_pending(pair.local)['uploaded'] == 0
    assert message_rows(pair) == before


def test_unreconciled_restored_allow_never_dispatches_before_an_explicit_decision(pair, tmp_path):
    """TC-005-unreconciled-send: exercise actual send attempts, not just status."""
    add_local(pair, 'restore-a', 'A', 'restored private original')
    config = connect(pair); federation.choose_upload(pair.local, 'all', [])
    backup = tmp_path / 'old-allow.sqlite3'
    with pair.local.connect() as source, sqlite3.connect(backup) as target: source.backup(target)
    federation.choose_upload(pair.local, 'none', [])
    controller = LocalUpload(pair.local, config, config['bound_hub_id']); controller.prepare_restore()
    with sqlite3.connect(backup) as source, pair.local.connect() as target: source.backup(target)
    pair.local = Archive(pair.local.db_path)
    add_local(pair, 'restore-new', 'A', 'restored private new')
    assert {h['source_session_id'] for h in pair.local.search('restored', limit=50)['results']} == {'restore-a', 'restore-new'}
    controller = LocalUpload(pair.local, config, config['bound_hub_id'])
    before = controller.row()['desired']; assert before['mode'] == 'all'
    physical = message_rows(pair); assert physical == []
    for view_first in [False, True]:
        if view_first:
            diff = controller.reconcile(federation._request)
            assert diff['hub']['policy']['mode'] == 'none'
            assert controller.row()['desired'] == before
        marker = len(pair.calls)
        try:
            result = federation.push_pending(pair.local)
        except ControlConflict:
            pass
        else:
            assert result['uploaded'] == 0
        assert not any(route == '/known-upload-messages' or (route == '/upload' and payload['records'])
                       for route, payload in pair.calls[marker:])
        assert message_rows(pair) == physical
        assert controller.status()['state'] == 'conflict'
        assert controller.row()['desired'] == before
        remote = pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']})
        assert remote.status_code == 200 and remote.json()['policy']['mode'] == 'none'


def test_bm25_formula_and_exact_retained_content_versions():
    """TC-005-bm25: retain prior formula/turn checks and assert version identities."""
    from test_combined_search import candidate, test_bm25_matches_independent_formula_and_ignores_archive_scores
    from smm_local.search_merge import merge_candidates
    test_bm25_matches_independent_formula_and_ignores_archive_scores()
    a = candidate('versioned-a', 'amber amber original', version='v1')
    b = candidate('versioned-a', 'amber amber changed', scope='hub', version='v2')
    versions = merge_candidates([a], [b], 'amber', 5)
    assert len(versions) == 1
    assert {(m['canonical_id'], m['content_version'], m['text']) for m in versions[0]['matched_messages']} == {
        ('versioned-a-m1', 'v1', 'amber amber original'), ('versioned-a-m1', 'v2', 'amber amber changed')}
    assert len(versions[0]['matched_messages']) == 2

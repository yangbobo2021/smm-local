"""Durable controls, restore fencing, crash windows and project previews."""
import json
import sqlite3

import pytest

from smm_local import federation, project_control
from smm_local.archive_protocol import ControlConflict
from smm_local.upload import LocalUpload
from smm_hub.upload import HubUpload
from test_005_contracts import pair, add_local, connect, bodies


def backup(db, path):
    with db.connect() as source, sqlite3.connect(path) as target:
        source.backup(target)


def restore(db, path):
    with sqlite3.connect(path) as source, db.connect() as target:
        source.backup(target)


def test_hub_old_database_and_joint_restore_never_reopen_stopped_rule(pair, tmp_path):
    add_local(pair, 'a', 'A', 'old history')
    config = connect(pair)
    federation.choose_upload(pair.local, 'all', [])
    federation.push_pending(pair.local)
    old_local, old_hub = tmp_path / 'local.bak', tmp_path / 'hub.bak'
    backup(pair.local, old_local); backup(pair.remote, old_hub)
    federation.choose_upload(pair.local, 'none', [])
    hub = HubUpload(pair.remote, pair.hub_id)
    local = LocalUpload(pair.local, config, pair.hub_id)
    hub.prepare_restore(); local.prepare_restore()
    restore(pair.remote, old_hub); restore(pair.local, old_local)
    local = LocalUpload(pair.local, config, pair.hub_id)
    assert local.status()['state'] == 'conflict'
    diff = local.reconcile(federation._request)
    assert diff['hub']['policy']['mode'] == 'none'
    assert diff['hub']['conflict']
    legacy = {'hub_id': pair.hub_id, 'device_id': config['device_id'], 'device_name': 'legacy',
              'records': [{'source': 'codex', 'source_session_id': 'forbidden', 'started_at': None,
                           'source_key': 'm', 'position': 1, 'source_order': 1,
                           'role': 'user', 'text': 'forbidden', 'timestamp': None}]}
    assert pair.client.post('/v1/upload', json=legacy).status_code == 409
    result = local.reconcile(federation._request, use='hub')
    assert result['state'] == 'confirmed' and result['policy']['mode'] == 'none'
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert bodies(pair.remote) == ['old history']


def test_hub_loss_of_receipts_rebuilds_from_exact_existing_messages(pair, tmp_path):
    a = add_local(pair, 'a', 'A', 'first exact')
    config = connect(pair); federation.choose_upload(pair.local, 'all', [])
    empty = tmp_path / 'empty.bak'; backup(pair.remote, empty)
    federation.push_pending(pair.local)
    assert bodies(pair.remote) == ['first exact']
    hub = HubUpload(pair.remote, pair.hub_id); hub.prepare_restore(); restore(pair.remote, empty)
    local = LocalUpload(pair.local, config, pair.hub_id)
    assert local.sync_policy(federation._request)['conflict']
    assert local.status()['state'] == 'conflict'
    local.reconcile(federation._request, use='local', expected_hub_revision=hub.status(config['device_id'])['revision'])
    assert local.status()['confirmed_messages'] == 0
    assert federation.push_pending(pair.local)['uploaded'] == 1
    assert bodies(pair.remote) == ['first exact']
    assert federation.push_pending(pair.local)['uploaded'] == 0


def test_database_without_managed_flag_still_rejects_old_client(pair, tmp_path):
    config = connect(pair)
    before = tmp_path / 'pre-adoption.bak'; backup(pair.remote, before)
    federation.choose_upload(pair.local, 'none', [])
    hub = HubUpload(pair.remote, pair.hub_id); hub.prepare_restore(); restore(pair.remote, before)
    state = hub.status(config['device_id'])
    assert state['policy']['mode'] == 'none' and state['conflict']
    assert hub.guard.read()['devices'][config['device_id']]['legacy_locked']


def test_missing_control_never_defaults_to_allow_and_can_be_explicitly_repaired(pair):
    add_local(pair, 'a', 'A', 'not sent')
    config = connect(pair); federation.choose_upload(pair.local, 'none', [])
    local = LocalUpload(pair.local, config, pair.hub_id)
    local.guard.path.unlink()
    with pytest.raises(ControlConflict):
        federation.push_pending(pair.local)
    assert local.status()['state'] == 'conflict'
    assert local.reconcile(federation._request, use='hub')['state'] == 'confirmed'
    assert federation.push_pending(pair.local)['uploaded'] == 0
    hub = HubUpload(pair.remote, pair.hub_id); hub.guard.path.unlink()
    assert pair.client.post('/v1/upload-policy/status', json={'hub_id': pair.hub_id, 'device_id': config['device_id']}).status_code == 409
    hub.prepare_restore()
    assert local.reconcile(federation._request, use='hub')['state'] == 'confirmed'
    assert bodies(pair.remote) == []


def test_hub_checkpoint_crash_recovers_only_committed_submission(pair, monkeypatch):
    config = connect(pair)
    hub = HubUpload(pair.remote, pair.hub_id)
    original = hub.guard.write
    writes = 0
    def crash(value):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError('synthetic checkpoint interruption')
        return original(value)
    monkeypatch.setattr(hub.guard, 'write', crash)
    with pytest.raises(OSError):
        hub.set(config['device_id'], {'mode': 'none', 'projects': []}, 0, 'committed-crash')
    assert hub.guard.read()['devices'][config['device_id']]['pending']
    monkeypatch.setattr(hub.guard, 'write', original)
    state = hub.status(config['device_id'])
    assert state['revision'] == 1 and not state['conflict']
    assert 'pending' not in hub.guard.read()['devices'][config['device_id']]
    # A different rule at the same revision is also a restore conflict.
    with pair.remote.connect() as con:
        con.execute("UPDATE hub_upload_policies SET policy=?", (json.dumps({'mode': 'all', 'projects': []}),))
    assert hub.status(config['device_id'])['conflict']


def test_stale_diff_and_target_changes_require_explicit_new_choice(pair):
    add_local(pair, 'a', 'A', 'private')
    config = connect(pair); federation.choose_upload(pair.local, 'none', [])
    local = LocalUpload(pair.local, config, pair.hub_id)
    revision = local.reconcile(federation._request)['hub']['revision']
    HubUpload(pair.remote, pair.hub_id).set(config['device_id'], {'mode': 'none', 'projects': []}, revision, 'other-controller')
    with pytest.raises(ControlConflict, match='已改变'):
        local.reconcile(federation._request, use='local', expected_hub_revision=revision)
    assert local.row()['desired']['mode'] == 'none'
    assert federation.configure_hub(pair.local, config['address'], 'renamed device', str(pair.token_file))['connected']
    assert federation.upload_status(pair.local)['policy']['mode'] == 'none'


def test_expanding_project_change_requires_bound_preview_and_preserves_assignment(pair):
    a = add_local(pair, 'a', 'A', 'A private')
    b = add_local(pair, 'b', 'B', 'B allowed')
    connect(pair); federation.choose_upload(pair.local, 'only', [b['project_id']])
    def persisted_affiliation():
        with pair.local.connect() as con:
            return (con.execute('SELECT project_id FROM conversations WHERE id=?', (a['id'],)).fetchone()[0],
                    [tuple(r) for r in con.execute('SELECT * FROM conversation_assignments WHERE conversation_id=?', (a['id'],))])
    original_affiliation = persisted_affiliation()
    data = {'conversation_id': a['id'], 'target_id': b['project_id']}
    preview = project_control.change(pair.local, 'assign', data, always_preview=True)
    assert not preview['applied'] and preview['newly_allowed_conversations'] == [a['id']]
    assert persisted_affiliation() == original_affiliation
    federation.choose_upload(pair.local, 'none', [])
    with pytest.raises(ValueError, match='重新预览'):
        project_control.change(pair.local, 'assign', data, preview['confirmation'])
    assert persisted_affiliation() == original_affiliation
    fresh = project_control.change(pair.local, 'assign', data, always_preview=True)
    assert persisted_affiliation() == original_affiliation
    assert project_control.change(pair.local, 'assign', data, fresh['confirmation'])['applied']
    pair.local.sync_codex(pair.histories)
    assert pair.local.read(a['id'])['project_id'] == b['project_id']
    global_project = pair.local.ensure_global_project()
    with pytest.raises(ValueError, match='不能合并'):
        project_control.change(pair.local, 'merge', {'source_id': b['project_id'], 'target_id': global_project['id']})


def test_failed_project_does_not_starve_another_allowed_project(pair, monkeypatch):
    a = add_local(pair, 'a', 'A', 'A blocked at transport')
    b = add_local(pair, 'b', 'B', 'B accepted')
    config = connect(pair); federation.choose_upload(pair.local, 'all', [])
    a_key = federation._remote_project_key(pair.local, a['project_id'])
    original = federation._request
    def request(config, route, payload=None):
        if route == '/known-upload-messages' and payload['records'][0]['project_id'] == a_key:
            raise federation.HubUnavailable('synthetic per-project failure')
        return original(config, route, payload)
    monkeypatch.setattr(federation, '_request', request)
    result = federation.push_pending(pair.local)
    assert result['errors'] and result['uploaded'] == 1
    assert bodies(pair.remote) == ['B accepted']


def test_existing_legacy_upload_migrates_on_background_restart_without_reconfigure(pair):
    add_local(pair, 'legacy', 'A', 'legacy verified history')
    device = 'd' * 32
    old = {'device_id': device, 'device_name': 'legacy device', 'token': pair.token_file.read_text(),
           'address': 'http://localhost:18770'}
    pair.local.db_path.with_suffix('.sqlite3.hub.json').write_text(json.dumps(old))
    with pair.local.connect() as con:
        con.execute('INSERT INTO settings VALUES(?,?)', (f'hub_cursor:{pair.hub_id}:{device}', '1'))
    assert federation.push_pending(pair.local)['uploaded'] == 1
    state = federation.upload_status(pair.local)
    assert state['policy']['mode'] == 'all' and state['state'] == 'confirmed'
    assert bodies(pair.remote) == ['legacy verified history']


def test_late_policy_reply_cannot_replace_a_newer_local_stop(pair, monkeypatch):
    add_local(pair, 'a', 'A', 'private')
    config = connect(pair)
    original = federation._request
    intercepted = False
    def request(config, route, payload=None):
        nonlocal intercepted
        result = original(config, route, payload)
        if route == '/upload-policy/set' and payload['policy']['mode'] == 'all' and not intercepted:
            intercepted = True
            state = federation.choose_upload(pair.local, 'none', [])
            assert state['state'] == 'confirmed'
        return result
    monkeypatch.setattr(federation, '_request', request)
    result = federation.choose_upload(pair.local, 'all', [])
    assert result['state'] == 'confirmed' and result['policy']['mode'] == 'none'
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert bodies(pair.remote) == []


def test_pause_does_not_block_control_or_resume_imports(pair):
    add_local(pair, 'a', 'A', 'private')
    config = connect(pair)
    pair.local.set_settings(sync_paused=True)
    result = federation.choose_upload(pair.local, 'all', [])
    assert result['state'] == 'confirmed'
    assert federation.push_pending(pair.local, control_only=True)['uploaded'] == 0
    result = federation.choose_upload(pair.local, 'none', [])
    assert result['state'] == 'confirmed' and pair.local.get_settings()['sync_paused']
    assert bodies(pair.remote) == []


def test_cross_process_save_and_dispatch_share_one_durable_fence(pair):
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path
    from smm_local.archive_protocol import control_lock
    a = add_local(pair, 'a', 'A', 'private')
    config = connect(pair); federation.choose_upload(pair.local, 'all', [])
    local = LocalUpload(pair.local, config, pair.hub_id); local.catalog()
    rows = local.candidates(local.row()['ack_epoch'])
    script = "from smm_local.core import Archive; from smm_local.federation import hub_config; from smm_local.upload import LocalUpload; import sys; db=Archive(sys.argv[1]); c=hub_config(db); LocalUpload(db,c,c['bound_hub_id']).choose('none',[]); print('saved',flush=True)"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / 'src'))
    with control_lock(local.guard.lock):
        process = subprocess.Popen([sys.executable, '-c', script, str(pair.local.db_path)], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(.15)
        assert process.poll() is None  # The second process cannot commit its save across our boundary.
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0 and stdout.strip() == 'saved', stderr
    assert local.row()['desired']['mode'] == 'none'
    assert local.dispatch(rows) is None
    local.sync_policy(federation._request)
    assert local.status()['state'] == 'confirmed'
    assert bodies(pair.remote) == []


def test_lost_policy_confirmation_is_pending_until_head_is_rechecked(pair, monkeypatch):
    add_local(pair, 'a', 'A', 'private')
    config = connect(pair); original = federation._request; lost = False
    def request(config, route, payload=None):
        nonlocal lost
        result = original(config, route, payload)
        if route == '/upload-policy/set' and not lost:
            lost = True; raise federation.HubUnavailable('synthetic policy reply lost')
        return result
    monkeypatch.setattr(federation, '_request', request)
    status = federation.choose_upload(pair.local, 'none', [])
    assert status['state'] == 'pending'
    assert bodies(pair.remote) == []
    federation.push_pending(pair.local)
    assert federation.upload_status(pair.local)['state'] == 'confirmed'
    assert federation.upload_status(pair.local)['policy']['mode'] == 'none'


@pytest.mark.parametrize('side,write_number', [('local', 1), ('local', 2), ('hub', 1), ('hub', 2)])
def test_control_interruption_recovers_only_a_proven_complete_local_choice(pair, monkeypatch, side, write_number):
    from uuid import uuid4
    add_local(pair, 'a', 'A', 'private')
    config = connect(pair); federation.choose_upload(pair.local, 'none', [])
    controller = LocalUpload(pair.local, config, pair.hub_id) if side == 'local' else HubUpload(pair.remote, pair.hub_id)
    original = controller.guard.write; writes = 0
    def interrupted(value):
        nonlocal writes
        writes += 1
        original(value)
        if writes == write_number: raise OSError('synthetic interruption after durable file write')
    monkeypatch.setattr(controller.guard, 'write', interrupted)
    with pytest.raises(OSError):
        if side == 'local': controller.choose('all', [])
        else: controller.set(config['device_id'], {'mode': 'all', 'projects': []}, controller.status(config['device_id'])['revision'], uuid4().hex)
    monkeypatch.setattr(controller.guard, 'write', original)
    local = LocalUpload(pair.local, config, pair.hub_id)
    # Even if a committed Hub update can checkpoint, local's prior epoch/version
    # or unfinished new allow is not silently promoted to a confirmed dispatch.
    try: federation.push_pending(pair.local)
    except (ControlConflict, federation.HubUnavailable): pass
    if side == 'local' and write_number == 2:
        # Both SQL and the final protected checkpoint are durable: recovering
        # this explicit allow is permitted, despite losing the caller reply.
        assert local.status()['state'] == 'confirmed'
        assert local.row()['desired']['mode'] == 'all'
        assert bodies(pair.remote) == ['private']
    else:
        assert bodies(pair.remote) == []
        assert local.status()['state'] != 'confirmed' or local.row()['desired']['mode'] == 'none'


def test_invalid_batch_receipt_remains_unknown_then_resolves_exactly(pair, monkeypatch):
    add_local(pair, 'a', 'A', 'committed once')
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    original = federation._request; corrupted = False
    def request(config, route, payload=None):
        nonlocal corrupted
        result = original(config, route, payload)
        if route == '/upload' and payload.get('records') and not corrupted:
            corrupted = True; return {**result, 'accepted': 0}
        return result
    monkeypatch.setattr(federation, '_request', request)
    with pytest.raises(ControlConflict): federation.push_pending(pair.local)
    status = federation.upload_status(pair.local)
    assert status['confirmed_messages'] == 0 and status['inflight_messages'] == 1
    assert bodies(pair.remote) == ['committed once']
    federation.push_pending(pair.local)
    assert federation.upload_status(pair.local)['confirmed_messages'] == 1
    assert bodies(pair.remote) == ['committed once']


def test_bounded_backfill_keeps_search_and_other_project_available(pair, monkeypatch):
    a = add_local(pair, 'a', 'A', 'common A initial')
    b = add_local(pair, 'b', 'B', 'common B progress')
    path = pair.histories / 'a.jsonl'
    with path.open('a') as stream:
        for n in range(2, 34):
            stream.write(json.dumps({'type': 'response_item', 'ordinal': n, 'payload': {'type': 'message', 'id': f'a-m{n}', 'role': 'user', 'content': [{'type': 'input_text', 'text': f'common A backlog {n}'}]}}) + '\n')
    pair.local.sync_codex(pair.histories)
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    monkeypatch.setattr(federation, 'BATCH_SIZE', 1)  # Exercise the same bounded 25-dispatch branch with a small fixture.
    first = federation.push_pending(pair.local)
    assert first['uploaded'] == 25 and first['pending']
    assert 'common B progress' in bodies(pair.remote)
    add_local(pair, 'a-later', 'A', 'common A later import')
    assert any(h['source_session_id'] == 'a-later' for h in federation.search_archive(pair.local, 'later', local=True)['results'])
    assert federation.push_pending(pair.local)['uploaded'] == 10
    assert len(bodies(pair.remote)) == 35
    expected = {('a', 1, 'user', 'common A initial', None),
                ('b', 1, 'user', 'common B progress', None),
                ('a-later', 1, 'user', 'common A later import', None)}
    expected.update(('a', n, 'user', f'common A backlog {n}', None) for n in range(2, 34))
    with pair.remote.connect() as con:
        actual = {tuple(r) for r in con.execute('SELECT c.source_session_id,m.position,m.role,m.text,m.timestamp FROM messages m JOIN conversations c ON c.id=m.conversation_id')}
        snapshot = [tuple(r) for r in con.execute('SELECT * FROM messages ORDER BY id')]
    assert actual == expected
    status = federation.upload_status(pair.local)
    assert status['allowed_pending_messages'] == 0 and status['inflight_messages'] == 0
    assert status['confirmed_messages'] == 35
    repeated = federation.push_pending(pair.local)
    assert repeated['uploaded'] == 0 and repeated['pending'] is False
    with pair.remote.connect() as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM messages ORDER BY id')] == snapshot

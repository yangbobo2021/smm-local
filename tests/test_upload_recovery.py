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
    data = {'conversation_id': a['id'], 'target_id': b['project_id']}
    preview = project_control.change(pair.local, 'assign', data, always_preview=True)
    assert not preview['applied'] and preview['newly_allowed_conversations'] == [a['id']]
    federation.choose_upload(pair.local, 'none', [])
    with pytest.raises(ValueError, match='重新预览'):
        project_control.change(pair.local, 'assign', data, preview['confirmation'])
    fresh = project_control.change(pair.local, 'assign', data, always_preview=True)
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

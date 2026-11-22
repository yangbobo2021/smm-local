"""Complete persistent project-oracle coverage from independent preparation review."""
import pytest

from smm_local import federation, project_control
from test_005_contracts import pair, add_local, connect
from test_upload_policy import test_global_assignment_survives_reimport_and_unknown_stays_local as global_contract


def test_global_assignment_also_preserves_exactly_one_persistent_global(pair):
    """TC-005-global: retain original checks and inspect the actual global set."""
    global_contract(pair)
    first = pair.local.ensure_global_project(); second = pair.local.ensure_global_project()
    expected = (first['id'], first['stable_key'])
    assert (second['id'], second['stable_key']) == expected
    globals_now = [(p['id'], p['stable_key']) for p in pair.local.projects() if p['kind'] == 'global']
    assert globals_now == [expected]
    with pair.local.connect() as con:
        assert [tuple(row) for row in con.execute("SELECT p.id,k.remote_key FROM projects p JOIN hub_local_project_keys k ON k.id=p.id WHERE p.kind='global'")] == [expected]


@pytest.mark.parametrize('operation', ['assign', 'map', 'merge'])
def test_all_expanding_operations_preview_and_reject_stale_without_persistent_changes(pair, operation):
    """TC-005-project-preview: all three expansion paths keep preview side-effect-free."""
    a = add_local(pair, 'preview-a1', 'A', 'private A one')
    a2 = add_local(pair, 'preview-a2', 'A', 'private A two')
    b = add_local(pair, 'preview-b', 'B', 'allowed B')
    connect(pair); federation.choose_upload(pair.local, 'only', [b['project_id']])
    data = ({'conversation_id': a['id'], 'target_id': b['project_id']} if operation == 'assign' else
            {'path': str(pair.histories.parent / 'A'), 'target_id': b['project_id']} if operation == 'map' else
            {'source_id': a['project_id'], 'target_id': b['project_id']})
    affected = {a['id']} if operation == 'assign' else {a['id'], a2['id']}
    def snapshot():
        with pair.local.connect() as con:
            return {table: [tuple(row) for row in con.execute('SELECT * FROM '+table+' ORDER BY 1,2')]
                    for table in ['projects', 'project_paths', 'project_links', 'conversations', 'conversation_assignments']}
    before = snapshot()
    preview = project_control.change(pair.local, operation, data)
    assert not preview['applied'] and preview['requires_confirmation']
    assert set(preview['affected_conversations']) == set(preview['newly_allowed_conversations']) == affected
    assert snapshot() == before
    # Change the generation while retaining an actually allowed B. The old
    # token must not be usable even when the resulting rule remains identical.
    federation.choose_upload(pair.local, 'only', [b['project_id']])
    with pytest.raises(ValueError, match='重新预览'):
        project_control.change(pair.local, operation, data, preview['confirmation'])
    assert snapshot() == before
    fresh = project_control.change(pair.local, operation, data, always_preview=True)
    assert not fresh['applied'] and set(fresh['newly_allowed_conversations']) == affected
    assert snapshot() == before
    applied = project_control.change(pair.local, operation, data, fresh['confirmation'])
    assert applied['applied'] and set(applied['affected_conversations']) == affected
    with pair.local.connect() as con:
        assigned = {row['id']: row['project_id'] for row in con.execute('SELECT id,project_id FROM conversations')}
    assert assigned[a['id']] == assigned[b['id']] == b['project_id']
    assert assigned[a2['id']] == (a['project_id'] if operation == 'assign' else b['project_id'])
    # Change the synthetic header to force actual parsing and replay.
    source_files = list(pair.histories.glob('*.jsonl'))
    for source in source_files:
        lines = source.read_text().splitlines()
        header = __import__('json').loads(lines[0])
        header['acceptance_replay'] = True
        lines[0] = __import__('json').dumps(header)
        source.write_text('\n'.join(lines) + '\n')
    imported = pair.local.sync_codex(pair.histories)
    assert imported['files_changed'] == len(source_files) == 3
    with pair.local.connect() as con:
        reimported = {row['id']: row['project_id'] for row in con.execute('SELECT id,project_id FROM conversations')}
    assert reimported == assigned
    global_project = pair.local.ensure_global_project()
    with pytest.raises(ValueError, match='不能合并'):
        project_control.change(pair.local, 'merge', {'source_id': b['project_id'], 'target_id': global_project['id']})

"""Project kinds and newly discovered projects obey exactly the same rules."""
import pytest
from smm_local import federation
from test_005_contracts import pair, add_local, connect, bodies


@pytest.mark.parametrize('mode,selected,expected', [
    ('all', [], {'A', 'B', 'G', 'NEW'}), ('none', [], set()),
    ('only', ['A'], {'A'}), ('only', ['G'], {'G'}),
    ('except', ['A'], {'B', 'G', 'NEW'}), ('except', ['G'], {'A', 'B', 'NEW'}),
])
def test_modes_treat_global_and_future_projects_as_regular_peer_projects(pair, mode, selected, expected):
    a = add_local(pair, 'a', 'A', 'A')
    b = add_local(pair, 'b', 'B', 'B')
    g = add_local(pair, 'g', 'placeholder', 'G')
    global_project = pair.local.ensure_global_project()
    pair.local.assign_conversation(g['id'], global_project['id'])
    config = connect(pair)
    ids = {'A': a['project_id'], 'B': b['project_id'], 'G': global_project['id']}
    federation.choose_upload(pair.local, mode, [ids[name] for name in selected])
    add_local(pair, 'new', 'NEW', 'NEW')
    before = {p['id']: p['stable_key'] for p in pair.local.projects()}
    pair.local.rename_project(a['project_id'], 'A renamed')
    after = {p['id']: p['stable_key'] for p in pair.local.projects()}
    assert before == after
    federation.push_pending(pair.local)
    assert set(bodies(pair.remote)) == expected
    assert federation.upload_status(pair.local)['policy']['mode'] == mode

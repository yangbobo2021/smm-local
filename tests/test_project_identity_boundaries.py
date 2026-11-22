"""Project names, global peers and metadata survive independent Hub linking."""
import json

from smm_local import federation, project_control
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect


def test_same_names_and_even_same_device_local_keys_remain_distinct_after_rename(pair):
    a = add_local(pair, 'a', 'A', 'identity boundary original')
    config = connect(pair)
    federation.choose_upload(pair.local, 'only', [a['project_id']])
    federation.push_pending(pair.local)
    key = federation._remote_project_key(pair.local, a['project_id'])
    other = 'd' * 32
    response = pair.client.post('/v1/project-metadata', json={'hub_id': pair.hub_id,
        'device_id': other, 'device_name': 'other device',
        'projects': [{'id': key, 'name': 'A'}], 'memberships': []})
    assert response.status_code == 200
    projects = HubProjects(pair.remote)
    same_names = [p for p in projects.list() if p['name'] == 'A']
    assert len(same_names) == 2 and len({p['id'] for p in same_names}) == 2
    own = next(p['id'] for p in same_names if p['owner'] == config['device_id'])
    remote = next(p['id'] for p in same_names if p['owner'] == other)
    projects.link(own, remote)
    links = projects.links()
    old_policy = federation.upload_status(pair.local)['policy']
    pair.local.rename_project(a['project_id'], 'renamed A')
    assert federation.push_pending(pair.local)['uploaded'] == 0
    assert projects.links() == links
    assert federation.upload_status(pair.local)['policy'] == old_policy
    current = next(p for p in projects.list() if p['id'] == own)
    assert current['name'] == 'renamed A' and current['source_key'] == key
    scope = pair.client.post('/v1/query-scope', json={'hub_id': pair.hub_id,
        'device_id': config['device_id'], 'project_id': key}).json()
    assert {p['id'] for p in scope['effective_projects']} == {own, remote}


def test_project_query_includes_global_only_after_explicit_hub_link(pair):
    a = add_local(pair, 'a', 'A', 'peerquery ordinary original')
    g = add_local(pair, 'g', 'placeholder', 'peerquery explicit global')
    global_project = pair.local.ensure_global_project()
    data = {'conversation_id': g['id'], 'target_id': global_project['id']}
    preview = project_control.change(pair.local, 'assign', data, always_preview=True)
    assert not preview['applied']
    assert project_control.change(pair.local, 'assign', data, preview['confirmation'])['applied']
    unknown = [{'type': 'session_meta', 'payload': {'id': 'unknown'}},
               {'type': 'response_item', 'ordinal': 1, 'payload': {'type': 'message', 'id': 'unknown-1',
                'role': 'user', 'content': [{'type': 'input_text', 'text': 'peerquery unknown'}]}}]
    (pair.histories / 'unknown.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in unknown))
    pair.local.sync_codex(pair.histories)
    config = connect(pair)
    def query():
        return federation.search_archive(pair.local, 'peerquery', scope='project', project_id=a['project_id'])
    assert {h['source_session_id'] for h in query()['results']} == {'a'}
    assert {h['source_session_id'] for h in federation.search_archive(pair.local, 'peerquery')['results']} == {'a', 'g', 'unknown'}
    projects = HubProjects(pair.remote)
    own = {p['source_key']: p['id'] for p in projects.list() if p['owner'] == config['device_id']}
    projects.link(own[federation._remote_project_key(pair.local, a['project_id'])],
                  own[federation._remote_project_key(pair.local, global_project['id'])])
    assert {h['source_session_id'] for h in query()['results']} == {'a', 'g'}
    assert {h['source_session_id'] for h in federation.search_archive(pair.local, 'peerquery',
        scope='project', project_id=a['project_id'], local=True)['results']} == {'a'}

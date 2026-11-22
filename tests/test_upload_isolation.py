"""A device restriction leaves other projects, devices and VibeInsight active."""
import json

from smm_local import federation
from smm_hub.vibeinsight import VibeInsightSync
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote, bodies
from test_vibeinsight_sync import FixtureSource, event


def test_restricting_a_keeps_old_reference_b_other_device_and_vibe_progress(pair):
    a = add_local(pair, 'a', 'A', 'isolation original A')
    b = add_local(pair, 'b', 'B', 'isolation original B')
    seed_remote(pair, 'isolation other device old', 'other-old')
    source = FixtureSource([event(1, 'vibe-isolation', 'user', text='isolation Vibe old')],
                           ['git.example/team/alpha'])
    sync = VibeInsightSync(pair.remote, 'isolated-test-source', batch_size=2)
    sync.run(source)
    connect(pair); federation.choose_upload(pair.local, 'all', [])
    federation.push_pending(pair.local)
    pair.local.link_projects(a['project_id'], b['project_id'])
    projects = HubProjects(pair.remote)
    ids = {p['name']: p['id'] for p in projects.list()}
    projects.link(ids['A'], ids['B'])
    assert projects.links()
    old = next(h for h in pair.client.post('/v1/search', json={'query': 'isolation'}).json()['results']
               if h['source_session_id'] == 'a')
    federation.choose_upload(pair.local, 'only', [b['project_id']])
    marker = len(pair.calls)
    appended = {'type': 'response_item', 'ordinal': 2, 'payload': {'type': 'message',
        'id': 'private-a-append', 'role': 'assistant',
        'content': [{'type': 'output_text', 'text': 'isolation forbidden A append'}]}}
    with (pair.histories / 'a.jsonl').open('a') as f: f.write(json.dumps(appended) + '\n')
    add_local(pair, 'a-private-new', 'A', 'isolation forbidden A new session')
    add_local(pair, 'b-new', 'B', 'isolation allowed B new')
    seed_remote(pair, 'isolation other device new', 'other-new')
    source.rows.append(event(2, 'vibe-isolation', 'assistant', text='isolation Vibe appended'))
    sync.run(source)
    federation.push_pending(pair.local)
    assert set(bodies(pair.remote)) == {'isolation original A', 'isolation original B',
        'isolation allowed B new', 'isolation other device old', 'isolation other device new',
        'isolation Vibe old', 'isolation Vibe appended'}
    transmitted = json.dumps(pair.calls[marker:])
    for private in ['a-private-new', 'private-a-append', 'isolation forbidden A']:
        assert private not in transmitted
    read = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': old['reference']})
    assert read.status_code == 200
    assert [m['text'] for m in read.json()['messages']] == ['isolation original A']
    assert [m['text'] for m in pair.local.read(a['id'])['messages']] == [
        'isolation original A', 'isolation forbidden A append']
    assert federation.upload_status(pair.local)['allowed_pending_messages'] == 0

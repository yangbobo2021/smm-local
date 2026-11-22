"""Scoped read metadata must not reintroduce excluded message bodies."""
import pytest

from smm_local import federation
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote


@pytest.mark.parametrize('entry', ['hub-api', 'federated'])
def test_scoped_read_title_comes_only_from_permitted_messages(pair, entry):
    """TC-005-scoped-title: a hidden first message cannot leak via title."""
    a = add_local(pair, 'a', 'A', 'common local A'); connect(pair)
    record = seed_remote(pair, 'OUTSIDE Y ONLY SECRET TITLE', session='shared')
    device = 'b' * 32
    response = pair.client.post('/v1/upload', json={'hub_id': pair.hub_id, 'device_id': device,
        'device_name': 'other-device', 'records': [{**record, 'source_key': 'inside', 'position': 2,
        'source_order': 2, 'text': 'common allowed X'}]})
    assert response.status_code == 200
    federation.push_pending(pair.local); projects = HubProjects(pair.remote)
    with pair.remote.connect() as con:
        x = projects.upsert(con, 'device', device, 'x', 'X')
        y = projects.upsert(con, 'device', device, 'y', 'Y')
        cid = con.execute("SELECT id FROM conversations WHERE source_session_id='shared'").fetchone()[0]
        con.executemany("INSERT INTO hub_project_memberships VALUES(?,'device',?,?)", [(cid, device, x), (cid, device, y)])
        mids = con.execute('SELECT id FROM messages WHERE conversation_id=? ORDER BY position', (cid,)).fetchall()
        con.execute('INSERT INTO hub_message_projects VALUES(?,?,?)', (mids[0][0], device, y))
        con.execute('INSERT INTO hub_message_projects VALUES(?,?,?)', (mids[1][0], device, x))
        projects.reindex(con, cid)
    aid = next(p['id'] for p in projects.list() if p['name'] == 'A'); projects.link(aid, x)
    hit = next(h for h in federation.search_archive(pair.local, 'common', scope='project',
        project_id=a['project_id'])['results'] if h['source_session_id'] == 'shared')
    assert hit['title'] == 'common allowed X'
    if entry == 'hub-api':
        response = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'reference': hit['reference']})
        assert response.status_code == 200; read = response.json()
    else:
        read = federation.read_archive(pair.local, reference=hit['reference'])
    assert [m['text'] for m in read['messages']] == ['common allowed X']
    assert 'OUTSIDE Y ONLY SECRET TITLE' not in read['title'], 'excluded body leaked through whole-conversation title'
    assert read['title'] == 'common allowed X'
    # Existing unscoped reads still return the original whole-conversation title.
    legacy = pair.client.post('/v1/read', json={'hub_id': pair.hub_id, 'conversation_id': cid})
    assert legacy.status_code == 200
    assert legacy.json()['title'] == 'OUTSIDE Y ONLY SECRET TITLE'
    assert [m['text'] for m in legacy.json()['messages']] == ['OUTSIDE Y ONLY SECRET TITLE', 'common allowed X']

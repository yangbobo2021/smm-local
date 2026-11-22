"""Citation content/version/scope is independent of presentation and integer IDs."""
import copy
import json

import pytest

from smm_local import federation, references
from smm_local.archive_protocol import message_version
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote


def test_tampering_cross_archive_and_conflicting_parameters_are_rejected(pair):
    add_local(pair, 'a', 'A', 'common local')
    seed_remote(pair, 'common remote'); connect(pair)
    hits = federation.search_archive(pair.local, 'common')['results']
    for hit in hits:
        ref = hit['reference']
        with pytest.raises((ValueError, federation.HubUnavailable)):
            federation.read_archive(pair.local, reference=ref[:-1] + ('a' if ref[-1] != 'a' else 'b'))
        with pytest.raises(ValueError):
            federation.read_archive(pair.local, reference=ref, conversation_id=9999)
        with pytest.raises(ValueError):
            federation.read_archive(pair.local, reference=ref, hub_message_id=1)
    local = next(h for h in hits if h['archive_scope'] == 'local')
    from smm_local.core import Archive
    other = Archive(pair.local.db_path.parent / 'other.sqlite3')
    with pytest.raises(ValueError):
        federation.read_archive(other, reference=local['reference'])


def test_local_content_change_between_recall_and_signing_fails_closed(pair):
    add_local(pair, 'a', 'A', 'common old')
    result = pair.local.search('common', include_message_ids=True)['results'][0]
    messages = result['matched_messages']
    for m in messages:
        m['content_version'] = message_version(m)
    with pair.local.connect() as con:
        con.execute("UPDATE messages SET text='new content' WHERE conversation_id=?", (result['id'],))
    with pytest.raises(ValueError, match='已改变'):
        references.issue(pair.local, result['id'], messages)


def test_shared_conversation_reference_cannot_expand_to_outside_project(pair):
    a = add_local(pair, 'a', 'A', 'common local A')
    config = connect(pair)
    # One remote conversation, split by message provenance across X and Y.
    record = seed_remote(pair, 'common allowed X', session='shared')
    device = 'b' * 32
    response = pair.client.post('/v1/upload', json={'hub_id': pair.hub_id, 'device_id': device,
        'device_name': 'other-device', 'records': [{**record, 'source_key': 'outside', 'position': 2, 'source_order': 2, 'text': 'common forbidden Y'}]})
    assert response.status_code == 200
    federation.push_pending(pair.local)
    projects = HubProjects(pair.remote)
    with pair.remote.connect() as con:
        con.execute('BEGIN IMMEDIATE')
        x = projects.upsert(con, 'device', device, 'x', 'X')
        y = projects.upsert(con, 'device', device, 'y', 'Y')
        conversation = con.execute("SELECT id FROM conversations WHERE source_session_id='shared'").fetchone()[0]
        con.executemany("INSERT INTO hub_project_memberships VALUES(?,'device',?,?)", [(conversation, device, x), (conversation, device, y)])
        mids = con.execute('SELECT id FROM messages WHERE conversation_id=? ORDER BY position', (conversation,)).fetchall()
        con.execute('INSERT INTO hub_message_projects VALUES(?,?,?)', (mids[0][0], device, x))
        con.execute('INSERT INTO hub_message_projects VALUES(?,?,?)', (mids[1][0], device, y))
        projects.reindex(con, conversation)
    aid = next(p['id'] for p in projects.list() if p['name'] == 'A'); projects.link(aid, x)
    result = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'])
    hit = next(h for h in result['results'] if h['source_session_id'] == 'shared')
    assert [m['text'] for m in hit['matched_messages']] == ['common allowed X']
    read = federation.read_archive(pair.local, reference=hit['reference'], start=0, end=100000)
    assert [m['text'] for m in read['messages']] == ['common allowed X']
    assert {p['id'] for p in read['projects']} == {x}
    # An appended outside message remains outside this frozen citation as well.
    assert federation.read_archive(pair.local, reference=hit['reference'], start=2)['messages'] == []


def test_old_read_parameters_still_work_without_new_reference(pair):
    a = add_local(pair, 'a', 'A', 'common local')
    record = seed_remote(pair, 'common remote'); connect(pair)
    assert federation.read_archive(pair.local, a['id'])['messages'][0]['text'] == 'common local'
    hit = pair.client.post('/v1/search', json={'query': 'common'}).json()['results'][0]
    message = hit['matched_messages'][0]
    original = federation.read_archive(pair.local, hit['id'], hub_id=pair.hub_id, hub_message_id=message['hub_message_id'])
    assert original['messages'][0]['text'] == 'common remote'

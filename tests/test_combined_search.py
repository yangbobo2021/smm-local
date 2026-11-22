"""Independent ranking, common scope, and partial archive contracts."""
import copy
import math

import pytest

from smm_local import federation, references
from smm_local.search_merge import merge_candidates
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote


def candidate(session, body, *, scope='local', version='v1', score=-999, stamp=None):
    return {'id': len(session), 'source': 'codex', 'source_session_id': session,
            'archive_scope': scope, 'reference': scope + session, 'bm25_score': score,
            'matched_messages': [{'text': body, 'position': 1, 'role': 'user',
                                  'canonical_id': session + '-m1', 'content_version': version,
                                  'timestamp': stamp, 'reference': scope + session}]}


def test_bm25_matches_independent_formula_and_ignores_archive_scores():
    # Documents [2 x amber, 1 x other] and [1 x amber, 4 x other], avg length 4.
    a = candidate('a', 'amber amber other', score=-1000)
    b = candidate('b', 'amber other other other other', scope='hub', score=1000)
    result = merge_candidates([a], [b], 'amber', 5)
    idf = math.log(1 + .5 / 2.5)
    expected_a = idf * 2 * 2.2 / (2 + 1.2 * (.25 + .75 * 3 / 4))
    expected_b = idf * 1 * 2.2 / (1 + 1.2 * (.25 + .75 * 5 / 4))
    assert [h['source_session_id'] for h in result] == ['a', 'b']
    assert [h['rerank_score'] for h in result] == pytest.approx([expected_a, expected_b])
    duplicate = copy.deepcopy(a)
    duplicate.update(archive_scope='hub', reference='hub-a')
    assert [h['rerank_score'] for h in merge_candidates([a], [duplicate, b], 'amber', 5)] == pytest.approx([expected_a, expected_b])
    assert len(merge_candidates([a], [duplicate, b], 'amber', 5)[0]['matched_messages']) == 1
    duplicate['matched_messages'][0]['content_version'] = 'v2'
    assert len(merge_candidates([a], [duplicate], 'amber', 5)[0]['matched_messages']) == 2


def test_ties_use_latest_timestamp_then_stable_identity():
    a = candidate('a', 'amber', stamp='2026-01-01T01:00:00+01:00')
    b = candidate('b', 'amber', stamp='2026-01-01T00:00:00Z')
    c = candidate('c', 'amber', stamp='2026-01-02T00:00:00Z')
    assert [h['source_session_id'] for h in merge_candidates([b], [c, a], 'amber', 5)] == ['c', 'a', 'b']


def test_long_preview_does_not_change_rank_or_original(pair):
    text = 'amber ' + 'longword ' * 2000 + ' amber final original'
    add_local(pair, 'long', 'A', text)
    seed_remote(pair, 'amber short original')
    connect(pair)
    full = federation.search_archive(pair.local, 'amber', preview_chars=0)
    short = federation.search_archive(pair.local, 'amber', preview_chars=100)
    assert [(h['source_session_id'], h['rerank_score']) for h in full['results']] == [(h['source_session_id'], h['rerank_score']) for h in short['results']]
    long = next(h for h in short['results'] if h['source_session_id'] == 'long')
    assert len(long['matched_messages'][0]['preview']) < len(text)
    assert federation.read_archive(pair.local, reference=long['reference'])['messages'][0]['text'] == text


def test_common_scope_is_one_hub_hop_without_local_reexpansion(pair):
    a = add_local(pair, 'a', 'A', 'common A')
    b = add_local(pair, 'b', 'B', 'common B')
    c = add_local(pair, 'c', 'C', 'common C')
    d = add_local(pair, 'd', 'D', 'common D')
    connect(pair)
    federation.push_pending(pair.local)
    projects = HubProjects(pair.remote)
    ids = {p['name']: p['id'] for p in projects.list()}
    projects.link(ids['A'], ids['B']); projects.link(ids['B'], ids['C'])
    pair.local.link_projects(a['project_id'], d['project_id'])
    result = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'])
    assert {h['source_session_id'] for h in result['results']} == {'a', 'b'}
    assert len(result['effective_projects']) == 2
    local = federation.search_archive(pair.local, 'common', local=True, scope='project', project_id=a['project_id'])
    assert {h['source_session_id'] for h in local['results']} == {'a', 'd'}


def test_partial_hub_failure_preserves_valid_local_snapshot(pair, monkeypatch):
    a = add_local(pair, 'a', 'A', 'common A')
    b = add_local(pair, 'b', 'B', 'common B')
    connect(pair); federation.push_pending(pair.local)
    projects = HubProjects(pair.remote)
    ids = {p['name']: p['id'] for p in projects.list()}; projects.link(ids['A'], ids['B'])
    original = federation._request
    def request(config, route, payload=None):
        if route == '/search':
            raise federation.HubUnavailable('synthetic search failure')
        return original(config, route, payload)
    monkeypatch.setattr(federation, '_request', request)
    result = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'])
    assert {h['source_session_id'] for h in result['results']} == {'a', 'b'}
    assert result['coverage'] == {'local': 'complete', 'hub': 'unavailable'}
    assert len(result['effective_projects']) == 2


def test_local_error_still_returns_readable_hub_candidates(pair, monkeypatch):
    connect(pair); seed_remote(pair, 'common remote')
    monkeypatch.setattr(federation, '_local_search', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('synthetic local failure')))
    result = federation.search_archive(pair.local, 'common')
    assert result['coverage'] == {'local': 'partial', 'hub': 'complete'}
    assert federation.read_archive(pair.local, reference=result['results'][0]['reference'])['messages'][0]['text'] == 'common remote'
    monkeypatch.setattr(federation, '_request', lambda *a, **k: (_ for _ in ()).throw(federation.HubUnavailable('offline')))
    with pytest.raises(RuntimeError, match='synthetic local failure'):
        federation.search_archive(pair.local, 'common')


def test_legacy_hub_global_search_is_readable_but_project_search_stays_local(pair, monkeypatch):
    a = add_local(pair, 'a', 'A', 'common local')
    seed_remote(pair, 'common remote')
    connect(pair)
    original = federation._request
    def legacy(config, route, payload=None):
        result = original(config, route, payload)
        if route == '/info':
            result['capabilities'] = ['projects']
        if route == '/search':
            for hit in result['results']:
                hit.pop('reference', None)
                for message in hit['matched_messages']:
                    message.pop('canonical_id', None); message.pop('content_version', None)
        return result
    monkeypatch.setattr(federation, '_request', legacy)
    assert federation.push_pending(pair.local)['uploaded'] == 0
    all_result = federation.search_archive(pair.local, 'common')
    assert {h['source_session_id'] for h in all_result['results']} == {'a', 'remote'}
    hit = next(h for h in all_result['results'] if h['source_session_id'] == 'remote')
    assert federation.read_archive(pair.local, reference=hit['reference'])['messages'][0]['text'] == 'common remote'
    scoped = federation.search_archive(pair.local, 'common', scope='project', project_id=a['project_id'])
    assert {h['source_session_id'] for h in scoped['results']} == {'a'}
    assert scoped['fallback_reason']


def test_current_session_excludes_both_copies_only_in_the_same_source(pair):
    add_local(pair, 'same-session', 'A', 'common current copy')
    config = connect(pair); federation.choose_upload(pair.local, 'all', []); federation.push_pending(pair.local)
    record = {'source': 'claude-code', 'source_session_id': 'same-session', 'started_at': None,
              'source_key': 'different-agent-message', 'position': 1, 'source_order': 1,
              'role': 'user', 'text': 'common other agent', 'timestamp': None}
    response = pair.client.post('/v1/upload', json={'hub_id': pair.hub_id, 'device_id': 'f' * 32,
        'device_name': 'other agent device', 'records': [record]})
    assert response.status_code == 200
    result = federation.search_archive(pair.local, 'common', current_source='codex', current_session_id='same-session')
    assert [(h['source'], h['source_session_id']) for h in result['results']] == [('claude-code', 'same-session')]
    included = federation.search_archive(pair.local, 'common', current_source='codex', current_session_id='same-session', include_current=True)
    assert {(h['source'], h['source_session_id']) for h in included['results']} == {('codex', 'same-session'), ('claude-code', 'same-session')}


def test_each_endpoint_receives_only_normal_n_without_topup_and_invalid_n_never_calls_hub(pair):
    for session in ('a', 'b', 'c'):
        add_local(pair, session, 'A', 'common identical words')
    connect(pair); federation.choose_upload(pair.local, 'all', []); federation.push_pending(pair.local)
    before = len(pair.calls)
    result = federation.search_archive(pair.local, 'common', limit=2)
    searches = [payload for route, payload in pair.calls[before:] if route == '/search']
    assert len(searches) == 1 and searches[0]['limit'] == 2
    assert result['rerank']['local_count'] == result['rerank']['hub_count'] == 2
    assert len(result['results']) <= 2
    before = len(pair.calls)
    for n in (0, 51):
        with pytest.raises(ValueError): federation.search_archive(pair.local, 'common', limit=n)
    assert len(pair.calls) == before
    assert len(federation.search_archive(pair.local, 'common', limit=50)['results']) == 3

"""Explicit SPEC conditions found while completing native scene records."""
import json
import math
import os
from pathlib import Path

import pytest
from smm_local import federation, project_control
from smm_local.search_merge import merge_candidates
from smm_hub.projects import HubProjects
from test_005_contracts import pair, add_local, connect, seed_remote, bodies
from test_combined_search import candidate
from test_upload_project_moves import move, physical_rows, project_hits


def evidence(name, value):
    directory = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
    if directory:
        Path(directory, name + '.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


@pytest.mark.parametrize('mode', ['all', 'only', 'except', 'none'])
def test_every_policy_save_preserves_paused_and_disabled_sources(pair, monkeypatch, mode):
    """TC-005-pause-source: inspect each save before any later rule can mask it."""
    a = add_local(pair, 'pause-a', 'A', 'paused private body')
    connect(pair)
    pair.local.set_source_enabled('codex', False)
    pair.local.set_source_enabled('claude-code', False)
    pair.local.set_settings(sync_paused=True)
    settings = pair.local.get_settings(); sources = pair.local.configured_sources()
    with pair.local.connect() as con:
        before = [tuple(r) for r in con.execute('SELECT * FROM messages ORDER BY id')]
    def forbidden_import(*args, **kwargs):
        pytest.fail('saving an upload rule must not start import')
    monkeypatch.setattr(pair.local, 'sync_all', forbidden_import)
    start = len(pair.calls)
    saved = federation.choose_upload(pair.local, mode, [a['project_id']] if mode in ('only', 'except') else [])
    assert saved['state'] == 'confirmed'
    assert pair.local.get_settings() == settings
    assert pair.local.configured_sources() == sources
    assert pair.local.get_settings()['sync_paused'] is True
    assert all(pair.local.configured_sources()[s]['enabled'] is False for s in ('codex', 'claude-code'))
    # Normal upload dispatch, not the control_only bypass used by the earlier test.
    dispatched = federation.push_pending(pair.local)
    assert dispatched['uploaded'] == 0 and bodies(pair.remote) == []
    assert not any(route == '/upload' and payload.get('records') for route, payload in pair.calls[start:])
    with pair.local.connect() as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM messages ORDER BY id')] == before
    evidence('pause-source-' + mode, {'saved': saved, 'settings': settings, 'sources': sources,
                                    'normal_dispatch': dispatched, 'requests': pair.calls[start:], 'hub_bodies': bodies(pair.remote)})


@pytest.mark.parametrize('scope', ['all', 'project'])
def test_empty_success_is_distinct_from_unexecuted_hub(pair, monkeypatch, scope):
    """TC-005-empty-coverage: identical empty result lists have different coverage."""
    a = add_local(pair, 'empty-a', 'A', 'presentpositive local')
    seed_remote(pair, 'presentpositive remote')
    connect(pair)
    kwargs = {'scope': scope, **({'project_id': a['project_id']} if scope == 'project' else {})}
    positive = federation.search_archive(pair.local, 'presentpositive', **kwargs)
    assert any(h['source_session_id'] == 'empty-a' for h in positive['results'])
    start = len(pair.calls)
    success = federation.search_archive(pair.local, 'uniquelyabsentquery', **kwargs)
    assert success['results'] == []
    assert success['coverage'] == {'local': 'complete', 'hub': 'complete'} and success.get('fallback_reason') is None
    assert any(route == '/search' for route, _ in pair.calls[start:])
    def unavailable(*args, **kwargs):
        raise federation.HubUnavailable('synthetic Hub unavailable for empty search')
    monkeypatch.setattr(federation, '_request', unavailable)
    failed = federation.search_archive(pair.local, 'uniquelyabsentquery', **kwargs)
    assert failed['results'] == []
    assert failed['coverage'] == {'local': 'complete', 'hub': 'unavailable'}
    assert 'synthetic Hub unavailable' in failed['fallback_reason']
    local = federation.search_archive(pair.local, 'uniquelyabsentquery', local=True, **kwargs)
    assert local['results'] == [] and local['coverage'] == {'local': 'complete', 'hub': 'not_requested'}
    evidence('empty-coverage-' + scope, {'success': success, 'failed': failed, 'explicit_local': local, 'positive': positive})


@pytest.mark.parametrize('operation', ['assign', 'map', 'merge'])
@pytest.mark.parametrize('change', ['target', 'affiliation'])
def test_confirmation_rejects_changed_target_or_existing_affiliation(pair, operation, change):
    """TC-005-confirmation-bindings: fresh generation alone cannot validate old consent."""
    a = add_local(pair, 'binding-a1', 'A', 'private a1')
    a2 = add_local(pair, 'binding-a2', 'A', 'private a2')
    b = add_local(pair, 'binding-b', 'B', 'allowed b')
    c = add_local(pair, 'binding-c', 'C', 'allowed c')
    connect(pair); federation.choose_upload(pair.local, 'only', [b['project_id'], c['project_id']])
    data = ({'conversation_id': a['id'], 'target_id': b['project_id']} if operation == 'assign' else
            {'path': str(pair.histories.parent / 'A'), 'target_id': b['project_id']} if operation == 'map' else
            {'source_id': a['project_id'], 'target_id': b['project_id']})
    preview = project_control.change(pair.local, operation, data, always_preview=True)
    generation = federation.upload_status(pair.local)['generation']
    submitted = dict(data)
    if change == 'target':
        submitted['target_id'] = c['project_id']
    else:
        # A real supported affiliation change, with a separate consent, after the old preview.
        other = {'conversation_id': a['id'], 'target_id': c['project_id']}
        consent = project_control.change(pair.local, 'assign', other, always_preview=True)
        assert project_control.change(pair.local, 'assign', other, consent['confirmation'])['applied']
    def snapshot():
        with pair.local.connect() as con:
            return {t: [tuple(r) for r in con.execute('SELECT * FROM '+t+' ORDER BY 1,2')]
                    for t in ['projects','project_paths','project_links','conversations','conversation_assignments']}
    before = snapshot()
    assert federation.upload_status(pair.local)['generation'] == generation
    with pytest.raises(ValueError, match='重新预览'):
        project_control.change(pair.local, operation, submitted, preview['confirmation'])
    assert snapshot() == before
    fresh = project_control.change(pair.local, operation, submitted, always_preview=True)
    assert not fresh['applied'] and snapshot() == before
    assert project_control.change(pair.local, operation, submitted, fresh['confirmation'])['applied']
    evidence('confirmation-'+operation+'-'+change, {'old_preview':preview, 'submitted':submitted, 'before_rejected':before,
                                                  'fresh_preview':fresh,'after_fresh':snapshot(),'generation':generation})


@pytest.mark.parametrize('operation', ['assign', 'map', 'merge'])
def test_old_reference_reads_while_destination_is_still_forbidden(pair, operation):
    """TC-005-forbidden-move-read: every old session/message ref before B is allowed."""
    a = add_local(pair, 'move-a', 'A', 'moving A first original')
    a2 = add_local(pair, 'move-a2', 'A', 'moving A second original')
    b = add_local(pair, 'move-b', 'B', 'moving B forbidden original')
    expected = {'move-a': [(1, 'user', 'moving A first original', None),
                            (2, 'assistant', 'moving A first appended', None)],
                'move-a2': [(1, 'user', 'moving A second original', None),
                             (2, 'assistant', 'moving A second appended', None)]}
    for session, rows in expected.items():
        event = {'type': 'response_item', 'ordinal': 2, 'payload': {'type': 'message',
                 'id': session+'-appended', 'role': 'assistant',
                 'content': [{'type': 'output_text', 'text': rows[1][2]}]}}
        with (pair.histories/(session+'.jsonl')).open('a') as stream:
            stream.write(json.dumps(event)+'\n')
    assert pair.local.sync_codex(pair.histories)['files_changed'] == 2
    config=connect(pair); federation.choose_upload(pair.local,'only',[a['project_id']])
    assert federation.push_pending(pair.local)['uploaded']==4
    keys={p['name']:p['source_key'] for p in HubProjects(pair.remote).list()}
    old_hits=project_hits(pair,config,keys['A']); assert set(old_hits)==set(expected)
    checks=[]
    for session, hit in old_hits.items():
        assert len(hit['matched_messages'])==2
        checks.append((session,hit['reference'],expected[session],None))
        for message in hit['matched_messages']:
            checks.append((session,hit['reference'],[next(row for row in expected[session] if row[0]==message['position'])],message['position']))
    def physical():
        with pair.remote.connect() as con:
            return [tuple(r) for r in con.execute("SELECT c.source_session_id,m.id,m.source_key,m.position,m.role,m.text,m.timestamp FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.source_session_id IN ('move-a','move-a2') ORDER BY m.id")]
    before=physical(); assert len(before)==4 and len(checks)==6
    assert len({reference for _,reference,_,_ in checks})==2
    move(pair,a,b,operation)
    if operation=='assign': move(pair,a2,b,operation)
    start=len(pair.calls)
    assert federation.push_pending(pair.local)['uploaded']==0
    assert not any(route=='/known-upload-messages' or (route=='/upload' and data['records']) for route,data in pair.calls[start:])
    assert not set(expected).intersection(project_hits(pair,config,keys['B']))
    assert set(project_hits(pair,config,keys['A']))==set(expected)
    reads=[]
    # No policy save occurs between the move and any of the six old reads.
    for session,reference,rows,position in checks:
        payload={'hub_id':pair.hub_id,'reference':reference,**({'start':position,'end':position} if position is not None else {})}
        response=pair.client.post('/v1/read',json=payload)
        assert response.status_code==200
        read=response.json(); assert read['source_session_id']==session and read['source']=='codex'
        assert [(m['position'],m['role'],m['text'],m['timestamp']) for m in read['messages']]==rows
        reads.append({'session':session,'expected':rows,'read':read})
    assert physical()==before
    assert federation.upload_status(pair.local)['policy']['projects']==[keys['A']]
    evidence('forbidden-move-read-'+operation,{'reads':reads,'policy':federation.upload_status(pair.local)['policy'],
                                             'physical_rows':before,'requests_while_forbidden':pair.calls[start:]})


def test_multiword_bm25_uses_each_terms_document_frequency_once():
    """TC-005-multiterm-ranking: unequal df and repeated query term have independent expected scores."""
    documents=[candidate('m1','amber amber blue'),candidate('m2','blue other other other',scope='hub'),candidate('m3','blue green')]
    # N=3, avglen=3, df(amber)=1, df(blue)=3; counts and lengths are independent literals.
    idf_amber=math.log1p(2.5/1.5);idf_blue=math.log1p(.5/3.5)
    expected={'m1': idf_amber*2*2.2/(2+1.2) + idf_blue*2.2/(1+1.2),
              'm2': idf_blue*2.2/(1+1.2*(.25+.75*4/3)),
              'm3': idf_blue*2.2/(1+1.2*(.25+.75*2/3))}
    actual=merge_candidates(documents[:1],documents[1:],'amber blue amber',10)
    assert {h['source_session_id'] for h in actual}==set(expected)
    for hit in actual:assert hit['rerank_score']==pytest.approx(expected[hit['source_session_id']],rel=1e-12)
    assert [h['source_session_id'] for h in actual]==[s for s in sorted(expected,key=lambda s:(-expected[s],s))]
    evidence('multiterm-ranking',{'query':'amber blue amber','expected':expected,'actual':actual})


def test_repeated_project_failure_does_not_block_new_peer_work(pair,monkeypatch):
    """TC-005-repeated-fairness: fresh B work progresses in every failed-A round."""
    a=add_local(pair,'failure-a','A','A unresolved backlog');b=add_local(pair,'peer-b0','B','B round 0')
    connect(pair);federation.choose_upload(pair.local,'all',[])
    key=federation._remote_project_key(pair.local,a['project_id']);original=federation._request;rounds=[]
    def request(config,route,payload=None):
        if route=='/known-upload-messages' and payload['records'][0]['project_id']==key:
            raise federation.HubUnavailable('synthetic persistent A failure')
        return original(config,route,payload)
    monkeypatch.setattr(federation,'_request',request)
    for number in range(3):
        if number:add_local(pair,'peer-b'+str(number),'B','B round '+str(number))
        result=federation.push_pending(pair.local)
        assert result['errors'] and result['uploaded']==1
        assert sorted(bodies(pair.remote))==['B round '+str(n) for n in range(number+1)]
        status=federation.upload_status(pair.local);assert status['allowed_pending_messages']>=1
        rounds.append({'round':number,'result':result,'status':status,'hub_bodies':bodies(pair.remote)})
    evidence('repeated-fairness',rounds)

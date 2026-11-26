"""Real unsynced creator reprocessing must not blend processing snapshots."""
import copy
import hashlib
import json
import pytest
from document_formats_remote_fixture import remote_world
from document_formats_remote_observer import controller_queries
from document_helpers import Fixture, observe
from test_document_formats_installed_minimum import assert_complete_source_text
from test_document_formats_management import native_input
from test_document_formats_retry import ENGINE, DATA, retry_args, keep


def assert_source(value, item):
    assert value['origin'] == item['origin']
    assert value['sha256'] == item['sha256'] and value['version'] == 1
    assert all(value['text'].count(word) == 1 for word in item['truth']['words'])
    assert all(word not in value['text'] for word in item['truth']['excluded'])
    assert_complete_source_text(value['text'], {**item['truth'], 'ordered_groups': [[item['key']+'Before',item['key']+'Inserted',item['key']+'After']]})
    assert len(value['tables']) == len(item['truth']['tables'])
    assert len({t['table_id'] for t in value['tables']}) == len(value['tables'])


@pytest.mark.skipif(not all((ENGINE, DATA)), reason='requires explicitly prepared creator processing configuration')
def test_union_isolates_processing_versions_and_rejects_old_mixed_bundles(tmp_path, monkeypatch):
    # TC-008-processing-version-isolation
    from smm_local import references, federation, document_search
    from smm_local.document_sync import DocumentSync
    from smm_local.archive_protocol import sign
    with remote_world(tmp_path, monkeypatch, formats=('docx',)) as w:
        targets = [i for i in w.items if i['kind'] == 'device']
        assert len(targets) == 4
        w.sender.start()
        project = targets[0]['project']
        control_raw, control_truth = native_input('docx', 'mirrorcontrol')
        receipt = w.send(w.sender, project, control_raw, 'docx', 'mirrorcontrol')
        entries = w.settled(w.sender, 5)
        control = next(r for r in entries if r['id'] == receipt['document_id'])
        DocumentSync(w.sender_db).sync()
        assert not DocumentSync(w.sender_db).status()['pending']
        w.protected.append(__import__('pathlib').Path(control['path']));w.protected[-1].unlink()
        status = w.cli(w.sender, 'processing-status')
        configured = w.cli(w.sender, 'processing-configure', '--expected-revision', status['config']['revision'], '--ocr-executable', ENGINE, '--ocr-data-dir', DATA, '--languages', 'chi_sim+eng')
        assert configured['config']['revision'] == status['config']['revision'] + 1 and configured['ocr']['ready']
        for item in targets:
            entry = next(r for r in w.sender.call('GET', '/documents/library').json() if r['id'] == item['source_document_id'])
            w.cli(w.sender, *retry_args(entry, entry['retry_target']))
            local = w.sender.call('POST', '/documents/search', {'query': item['query'], 'scope': 'all', 'local': True, 'limit': 50}).json()['results']
            remote = w.hub.call('POST', '/documents/search', {**w.hub.context, 'query': item['query'], 'scope': 'all', 'limit': 50}).json()['results']
            assert len(local) == len(remote) == 1
            a, b = local[0], remote[0]
            assert a['origin'] == b['origin'] == item['origin']
            assert a['version'] == b['version'] == 1 and a['sha256'] == b['sha256'] == item['sha256']
            assert a['text_sha256'] == b['text_sha256'] and a['text_length'] == b['text_length']
            assert (a['processing_version'], b['processing_version']) == (2, 1) and a['result_sha256'] != b['result_sha256']
            item['snapshots'] = {2: a, 1: b}
            item['canonical'] = {}
            for p,server,hit in ((2,w.sender,a),(1,w.hub,b)):
                value=server.call('POST','/documents/read',{**server.context,'reference':hit['reference'],'start':0,'end':hit['text_length']}).json()
                assert_source(value,item)
                assert len(value['text'])==hit['text_length'] and hashlib.sha256(value['text'].encode()).hexdigest()==hit['text_sha256']
                assert value['start']==0 and value['end']==hit['text_length']
                assert value['profile']==hit['profile'] and value['profile']['config_revision']==(configured['config']['revision'] if p==2 else 0)
                item['canonical'][p]=value
            w.save('version-preconditions/' + item['key'] + '.json', {'local': a, 'hub': b})
        assert w.sender.stop()['forced'] is False
        w.freeze_query_services()
        w.sender.start(deny=w.protected)
        w.enroll_query_server(w.sender)
        env, log, before = w.query_environment(w.sender)

        for item in targets:
            result = w.cli(w.sender, 'search', item['query'], '--scope', 'all', '--limit', '50', env=env)
            api = w.sender.call('POST', '/documents/search', {'query': item['query'], 'scope': 'all', 'limit': 50}).json()
            for found in (result, api):
                assert len(found['results']) == 2
                assert {h['processing_version'] for h in found['results']} == {1, 2}
                assert all(h['archive_scope'] in {'local', 'hub'} and references.routing_metadata(h['reference'])['kind'] != 'bundle' for h in found['results'])
                for hit in found['results']:
                    p = hit['processing_version'];expected = item['snapshots'][p]
                    assert hit['origin'] == item['origin'] and hit['result_sha256'] == expected['result_sha256']
                    assert hit['version'] == 1 and hit['sha256'] == item['sha256']
                    body = {'reference': hit['reference'], 'start': 0, 'end': hit['text_length']}
                    cli = w.cli(w.sender, 'read', '--reference', hit['reference'], '--start', 0, '--end', hit['text_length'], env=env)
                    http = w.sender.call('POST', '/documents/read', body).json()
                    for value in (cli, http):
                        assert_source(value, item)
                        assert value['processing_version'] == p and value['result_sha256'] == expected['result_sha256']
                        assert value['text']==item['canonical'][p]['text'] and value['profile']==expected['profile']
                        assert value['text_sha256']==expected['text_sha256']==hashlib.sha256(value['text'].encode()).hexdigest()
                        assert value['start']==0 and value['end']==value['text_length']==len(value['text'])==expected['text_length']
                        matched = set()
                        for summary in value['tables']:
                            view = w.sender.call('POST', '/documents/read', {'reference': hit['reference'], 'view': 'table', 'table_id': summary['table_id'], 'row_start': 1, 'row_end': summary['rows'] + 1, 'column_start': 1, 'column_end': summary['columns'] + 1}).json()
                            cli_view=w.cli(w.sender,'read','--reference',hit['reference'],'--view','table','--table-id',summary['table_id'],'--row-start',1,'--row-end',summary['rows']+1,'--column-start',1,'--column-end',summary['columns']+1,env=env)
                            selected=None
                            for table in (view,cli_view):
                                assert table['table_id']==summary['table_id'] and table['location']==summary['location']
                                assert table['processing_version'] == p and table['result_sha256'] == expected['result_sha256'] and table['profile']==expected['profile']
                                cells = [(c['row'], c['column'], c['text'], c['row_span'], c['column_span']) for c in table['cells']]
                                matches = [j for j, t in enumerate(item['truth']['tables']) if (table['rows'], table['columns']) == (t['rows'], t['columns']) and len(cells) == len(t['cells']) and set(cells) == set(t['cells']) and table['location'] == t['location']]
                                assert len(matches) == 1
                                if selected is None:selected=matches[0]
                                else:assert selected==matches[0]
                            assert matches[0] not in matched;matched.add(matches[0])
                        assert matched == set(range(len(item['truth']['tables'])))
                    info = w.cli(w.sender, 'read', '--reference', hit['reference'], '--view', 'original-info', env=env)
                    assert info['origin'] == item['origin'] and info['processing_version'] == p and info['result_sha256'] == expected['result_sha256'] and info['bytes'] == len(item['raw'])
                    api_info=w.sender.call('POST','/documents/read',{'reference':hit['reference'],'view':'original-info'}).json()
                    for metadata in (info,api_info):
                        assert metadata['origin']==item['origin'] and metadata['sha256']==item['sha256'] and metadata['bytes']==len(item['raw']) and metadata['version']==1 and metadata['processing_version']==p and metadata['result_sha256']==expected['result_sha256'] and metadata['profile']==expected['profile'] and metadata['available'] is True
                    output = w.root / ('version-' + item['key'] + '-' + str(p) + '-' + ('cli' if found is result else 'http') + '.docx')
                    w.cli(w.sender, 'read', '--reference', hit['reference'], '--original-output', output, env=env)
                    assert output.read_bytes() == item['raw']
                    assert w.sender.call('POST', '/documents/original', {'reference': hit['reference']}).content == item['raw']
            local_ref = item['snapshots'][2]['reference']
            remote_ref = references.wrap_hub(w.sender_db, w.hub.context['hub_id'], item['snapshots'][1]['reference'])
            mixed = references.bundle(w.sender_db, [local_ref, remote_ref])
            # Signed by the normal constructor just as an old version did.
            for view in ('text', 'table', 'original-info'):
                options = {'view': view}
                if view == 'table':
                    full = w.sender.call('POST','/documents/read',{'reference':local_ref,'start':0,'end':item['snapshots'][2]['text_length']}).json()
                    options['table_id'] = full['tables'][0]['table_id']
                with pytest.raises(ValueError, match='重新检索'):
                    with controller_queries(w):document_search.read(w.sender_db, mixed, **options)
                response = w.sender.client.post('/api/documents/read', json={'reference': mixed, **options})
                assert 400 <= response.status_code < 500 and '重新检索' in response.text
            with pytest.raises(ValueError, match='重新检索'):
                with controller_queries(w):document_search.original(w.sender_db, mixed)
            response = w.sender.client.post('/api/documents/original', json={'reference': mixed})
            assert 400 <= response.status_code < 500 and '重新检索' in response.text
            for p,ref in ((2,local_ref),(1,remote_ref)):
                reread=w.sender.call('POST','/documents/read',{'reference':ref,'start':0,'end':item['snapshots'][p]['text_length']}).json()
                assert reread['text']==item['canonical'][p]['text'] and reread['profile']==item['canonical'][p]['profile'] and reread['processing_version']==p and reread['result_sha256']==item['snapshots'][p]['result_sha256']
                assert w.sender.call('POST','/documents/original',{'reference':ref}).content==item['raw']
            observe('version-isolation-target-complete', {'key': item['key'], 'processing_versions': [1, 2], 'old_mixed_reference_rejected': True})
            w.query_unchanged(log, before)

        mirror = w.cli(w.sender, 'search', control_truth['words'][0].split()[0], '--scope', 'all', '--limit', '50', env=env)['results']
        assert len(mirror) == 1 and mirror[0]['archive_scope'] == 'combined' and mirror[0]['processing_version'] == 1
        assert references.decode(w.sender_db, mirror[0]['reference'])['kind'] == 'bundle'
        with controller_queries(w):mirror_read = document_search.read(w.sender_db, mirror[0]['reference'], start=0, end=mirror[0]['text_length'])
        assert all(mirror_read['text'].count(t) == 1 for t in control_truth['words'])
        with controller_queries(w):assert document_search.original(w.sender_db, mirror[0]['reference']) == control_raw

        # Explicit malformed-protocol negative controls. Positive business above
        # always uses actual persisted creators and real network exchanges.
        genuine = federation._request
        for item in targets:
            response = genuine(federation.hub_config(w.sender_db), '/documents/search', {**w.hub.context, 'query': item['query'], 'scope': 'all', 'limit': 50})
            for mismatch in ('same-p-conflict', 'hit-ref-p', 'hit-ref-result'):
                bad = copy.deepcopy(response);h = bad['results'][0]
                if mismatch == 'same-p-conflict':
                    h['processing_version'] = 2
                    payload = references.decode(w.hub_db, h['reference']);payload['processing_version'] = 2
                    h['reference'] = sign(payload, references.material(w.hub_db)[1])
                elif mismatch == 'hit-ref-p':h['processing_version'] = 2
                else:h['result_sha256'] = '0' * 64
                with monkeypatch.context() as m:
                    m.setattr(federation, '_request', lambda cfg, route, body=None: copy.deepcopy(bad) if route == '/documents/search' else genuine(cfg, route, body))
                    with controller_queries(w):merged = document_search.search(w.sender_db, item['query'], scope='all', limit=50)
                assert merged['coverage']['hub'] == 'partial' and merged['candidate_failures']
                assert len(merged['results']) == 1 and merged['results'][0]['archive_scope'] == 'local'
                assert merged['results'][0]['processing_version'] == 2 and merged['results'][0]['result_sha256'] == item['snapshots'][2]['result_sha256']
                w.save('protocol-negatives/' + item['key'] + '-' + mismatch + '.json', {'input': bad, 'output': merged})
        w.query_unchanged(log, before)

    legacy = Fixture(tmp_path / 'legacy')
    project = legacy.project();path = legacy.file('legacy.txt', 'legacy preserved text')
    legacy.refresh(legacy.add(path, [project]))
    hit = legacy.search('preserved', scope='project', project_id=project, local=True)['results'][0]
    reference = references.bundle(legacy.db, [hit['reference']])
    path.unlink()
    assert document_search.read(legacy.db, reference, start=0, end=hit['text_length'])['text'] == 'legacy preserved text'

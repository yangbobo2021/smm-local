"""Saved-capture lifecycle probes using installed CLI and authenticated HTTP.

This complements, rather than replaces, the complete content/entry replay.
All files, projects, component configuration and process faults are task-owned.
"""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import ssl
import sys
import time
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parent))
from document_formats_upload_transport import rows, wait, upload as transport_upload
from document_formats_lifecycle_privacy import remember, inspect_default_off


def upload(probe, item, raw, **kwargs):
    remember(probe, item, raw)
    entry = transport_upload(probe, item, raw, **kwargs)
    if kwargs.get('await_terminal', True):
        remember(probe, item, raw, entry)
    return entry


def unchanged_publication(actual, expected):
    assert actual['reference'] == expected['reference']
    def without_issued_references(value):
        if isinstance(value, dict):
            return {key: without_issued_references(item) for key, item in value.items() if key != 'reference'}
        if isinstance(value, list):return [without_issued_references(item) for item in value]
        return value
    # A new search may issue a new opaque string. The explicit old reference
    # was read above, and every identity/content/qualification field is kept.
    assert without_issued_references(actual) == without_issued_references(expected)






def configure(probe, role, *, ready=True):
    import shutil
    current = probe.cli(role, 'documents', 'processing-status')
    data = Path(probe.materials['ocr_data_dir'])
    if not ready:
        data = probe.out / (role + '-private-language-data')
        data.mkdir(exist_ok=True)
        for language in ('eng', 'chi_sim'):
            shutil.copyfile(Path(probe.materials['ocr_data_dir']) / (language + '.traineddata'), data / (language + '.traineddata'))
    previous_phase = probe.phase
    probe.phase = 'prepare'
    result = probe.cli(role, 'documents', 'processing-configure',
        '--expected-revision', current['config']['revision'],
        '--ocr-executable', probe.materials['ocr_executable'],
        '--ocr-data-dir', data, '--languages', 'chi_sim+eng')
    if not ready:
        # Configuration correctly rejects missing languages. First configure
        # real, readable private files, then reproduce later component loss.
        (data / 'chi_sim.traineddata').unlink()
    actual_dependency_loss = not ready and getattr(probe, 'native_actual_dependency_loss', False)
    checked = probe.cli(role, 'documents', 'processing-status', *([] if actual_dependency_loss else ['--check']))
    assert checked['config']['revision'] == result['config']['revision']
    if actual_dependency_loss:
        # Retain the valid pre-loss probe so the actual service worker itself
        # encounters the missing private file, rather than rejecting a cached
        # failed CLI probe before attempting the component boundary.
        assert checked['ocr']['ready'] is True and not (data / 'chi_sim.traineddata').exists()
    else:
        assert checked['ocr']['ready'] is ready, checked
    probe.phase = previous_phase
    return result




def library_entry(probe, role, ident):
    library = probe.request(role, probe.path(role, '/documents/library'))
    own = [row for row in library if row['id'] == ident]
    assert len(own) == 1
    return own[0]


def retry(probe, role, entry):
    target = entry['retry_target']
    assert target and target['capture_id'] == entry['latest_attempt']['capture_id']
    args = ['documents', 'reprocess', '--document-id', entry['id'],
            '--capture-id', target['capture_id'], '--expected-attempt-id', target['expected_attempt_id'],
            '--expected-version', target['expected_version'],
            '--expected-processing-version', target['expected_processing_version']]
    probe.phase = 'resume-captured'
    probe.cli(role, *args)
    current = wait(probe, role, entry['id'])
    probe.phase = 'archive-only'
    assert current['latest_attempt']['capture_id'] == target['capture_id']
    assert current['latest_attempt']['attempt_id'] != target['expected_attempt_id']
    before = rows(probe, role)
    probe.cli(role, *args, code=2)
    assert rows(probe, role) == before, 'Stale retry changed a document'
    return current


def snapshot(probe, item, *, reference=None):
    role = item.get('read_role', item['role'])
    project = item.get('read_project', item['project'])
    found = probe.request(role, probe.path(role, '/documents/search'), probe.body(role,
        query=item['query'], scope='project', project_id=project['id'], limit=50,
        **({'local': True} if role == 'a' else {})))
    own = [hit for hit in found['results'] if hit['origin'] == probe.expected_origin(item)]
    assert len(own) == 1
    hit = own[0]
    assert hit['version'] == item['version'] and hit['processing_version'] == item['processing_version']
    assert hit['sha256'] == item['sha256'] and hit['processing_status'] == item.get('status', 'ready')
    assert hit['format'] == item['format']
    ref = reference or hit['reference']
    value = probe.request(role, probe.path(role, '/documents/read'), probe.body(role,
        reference=ref, start=0, end=hit['text_length']))
    for key in ('origin', 'format', 'sha256', 'text_sha256', 'result_sha256', 'version', 'processing_version', 'processing_status'):
        assert value[key] == hit[key]
    assert value['text'] and value['text_length'] == len(value['text'])
    assert (value['start'], value['end']) == (0, len(value['text']))
    assert (value['start_line'], value['end_line']) == (1, 1 + value['text'].count('\n', 0, len(value['text']) - 1))
    assert hit['text'] == value['text'][hit['start']:hit['end']]
    assert hit['start_line'] == 1 + value['text'].count('\n', 0, hit['start'])
    assert hit['end_line'] == 1 + value['text'].count('\n', 0, hit['end'] - 1)
    if item.get('status') == 'partial':
        assert value['text'] == item['truth']['anchor']
        assert {unit['page'] for unit in value['coverage']['units']} == {1, 2}
        assert any(error.get('page') == 2 and '1600' in error['reason'] for error in value['coverage']['errors'])
    else:
        probe.text_oracle(value['text'], item['truth'], item['kind'] == 'ocrpdf')
        assert value['coverage']['errors'] == []
        from document_formats_protocol_positions import text_positions
        text_positions(value, item['truth'])
    expected = item['truth'].get('tables', [])
    tables = []
    for summary in value['tables']:
        table = probe.request(role, probe.path(role, '/documents/read'), probe.body(role,
            reference=ref, view='table', table_id=summary['table_id'], row_start=1,
            row_end=summary['rows'] + 1, column_start=1, column_end=summary['columns'] + 1))
        assert table['origin'] == value['origin'] and table['version'] == value['version']
        assert table['processing_version'] == value['processing_version'] and table['sha256'] == value['sha256']
        assert table['table_id'] == summary['table_id'] and table['location'] == summary['location']
        for field in ('format', 'text_sha256', 'result_sha256'):
            assert table[field] == value[field]
        from document_formats_protocol_positions import table_positions
        table_positions(table, item['truth'])
        tables.append(table)
    assert len(tables) == len({table['table_id'] for table in tables}) == len(expected)
    for truth in expected:
        assert sum(probe.table_oracle(table, truth) and
            all(table['location'].get(k) == v for k, v in truth['location'].items()) for table in tables) == 1
    info = probe.request(role, probe.path(role, '/documents/read'), probe.body(role, reference=ref, view='original-info'))
    assert info['origin'] == value['origin'] and info['available'] is True
    assert info['format'] == item['format'] and info['version'] == item['version']
    assert info['processing_version'] == item['processing_version'] and info['result_sha256'] == value['result_sha256']
    assert info['sha256'] == item['sha256'] and info['bytes'] == len(item['raw'])
    assert probe.raw_original(role, ref) == item['raw']
    remember(probe, item, publication=value)
    return {'reference': ref, 'hit': hit, 'text': value, 'tables': tables, 'info': info}


def reject_old(probe, role, saved):
    for fields in ({}, {'view': 'original-info'}, *[{'view': 'table', 'table_id': t['table_id']} for t in saved['tables']]):
        probe.request(role, probe.path(role, '/documents/read'), probe.body(role,
            reference=saved['reference'], **fields), code=400)
    probe.request(role, probe.path(role, '/documents/original'), probe.body(role,
        reference=saved['reference']), code=400)


def first_and_replacement_retry(probe, *, failure_controls=None):
    """Both creator roles, two independent failed saved candidates per role."""
    from document_formats_lifecycle_readback import failed_detail
    result = []
    for role in ('a', 'hub'):
        configure(probe, role, ready=False)
        first = []
        for index in range(2):
            item = probe.material('ocrpdf', ('LOCAL' if role == 'a' else 'HUB') + 'FIRST' + ('ALPHA' if index == 0 else 'BETA'))
            # The saved-capture test uses the predeclared numeric source word.
            # OCR may legitimately join label/RETRY whitespace; identity is
            # still selected by the full independently known origin below.
            item.update(role=role, project=probe.projects[role][index], version=1, processing_version=1, query='73428')
            entry = upload(probe, item, item['raw'])
            assert entry['published_snapshot'] is None and entry['version'] == entry['processing_version'] == 0
            assert entry['latest_attempt']['status'] == 'failed' and entry['retry_target']['sha256'] == item['sha256']
            item['id'] = entry['id']
            failed_detail(probe, item, entry, 'first-failed')
            if failure_controls:
                failure_controls(probe, role, entry)
            first.append((item, entry))
        configure(probe, role)
        for item, entry in first:
            item['path'] = Path(entry['path'])
            assert item['path'].is_file()
            item['path'].unlink()
            current = retry(probe, role, entry)
            assert current['latest_attempt']['status'] == 'ready'
            assert current['published_snapshot']['capture_id'] == entry['retry_target']['capture_id']
            saved = snapshot(probe, item)
            # Replacement upload changes the capture while retaining the old
            # publication. No fixture path is used by upload or saved retry.
            configure(probe, role, ready=False)
            newer = probe.material('ocrpdf', item['label'] + 'NEW')
            previous = library_entry(probe, role, item['id'])
            failed = upload(probe, item, newer['raw'], replacement=previous)
            assert failed['latest_attempt']['status'] == 'failed'
            assert failed['published_snapshot']['capture_id'] != failed['latest_attempt']['capture_id']
            assert failed['version'] == failed['processing_version'] == 1
            assert failed['retry_target']['sha256'] == newer['sha256']
            failed_detail(probe, item, failed, 'replacement-failed')
            if failure_controls:
                failure_controls(probe, role, failed)
            unchanged_publication(snapshot(probe, item, reference=saved['reference']), saved)
            configure(probe, role)
            assert item['path'].is_file()
            item['path'].unlink()
            finished = retry(probe, role, failed)
            assert finished['version'] == finished['processing_version'] == 2
            item.update({k: newer[k] for k in ('raw', 'truth', 'sha256')})
            item.update(version=2, processing_version=2)
            current = snapshot(probe, item)
            reject_old(probe, role, saved)
            result.append({'role': role, 'document_id': item['id'], 'first_capture': entry['retry_target'],
                'replacement_capture': failed['retry_target'], 'current_reference': current['reference']})
            probe.items.append(item)
    probe.register_source_paths()
    probe.save('lifecycle-saved-retries', result)


def update_each_format(probe):
    result = []
    for role in ('a', 'hub'):
        selected = [item for item in probe.items if item['role'] == role and item['acquisition'] == 'path'
                    and item['project']['id'] == probe.projects[role][0]['id']]
        controls = [item for item in probe.items if item['role'] == role and item['acquisition'] == 'path'
                    and item['project']['id'] == probe.projects[role][1]['id']]
        assert len(selected) == len(controls) == 4
        stable = {item['id']: snapshot(probe, {**item, 'version': 1, 'processing_version': 1}) for item in controls}
        # These files share one source; one refresh must update all four.
        sources = probe.cli(role, 'documents', 'sources')
        source = next(s for s in sources if Path(s['path']) == selected[0]['path'].parent)
        old = {item['id']: snapshot(probe, {**item, 'version': 1, 'processing_version': 1}) for item in selected}
        for item in selected:
            label = ('L' if role == 'a' else 'H') + 'U' if item['kind'] == 'nativepdf' else item['label'] + 'UPDATED'
            material = probe.material(item['kind'], label)
            item['path'].write_bytes(material['raw'])
            item.update({key: material[key] for key in ('raw', 'truth', 'query', 'sha256')})
            item.update(version=2, processing_version=2)
            remember(probe, item)
        probe.phase = 'explicit-refresh'
        probe.cli(role, 'documents', 'refresh', '--source-id', source['id'])
        probe.phase = 'archive-only'
        for item in selected:
            current = snapshot(probe, item)
            reject_old(probe, role, old[item['id']])
            result.append({'role': role, 'id': item['id'], 'old_reference': old[item['id']]['reference'],
                           'new_reference': current['reference']})
        for item in controls:
            unchanged_publication(snapshot(probe, {**item, 'version': 1, 'processing_version': 1},
                reference=stable[item['id']]['reference']), stable[item['id']])
    probe.save('lifecycle-format-updates', result)


def sync_and_project_boundaries(probe):
    """Actual policy/sync, independent device identities and receiver guards."""
    from document_formats_partial_fixture import partial_pdf
    from document_formats_protocol_guards import events
    # A partial native+oversized-scan capture must retain its coverage at Hub.
    raw, truth = partial_pdf('PARTIALSYNC', probe.materials['font']['path'])
    item = {'role': 'a', 'project': probe.projects['a'][0], 'label': 'partial-sync',
        'kind': 'partial', 'format': 'pdf', 'raw': raw, 'truth': truth, 'query': truth['anchor'].split()[0],
        'sha256': hashlib.sha256(raw).hexdigest(), 'status': 'partial', 'version': 1, 'processing_version': 1}
    probe.keep('lifecycle-inputs/partial-sync.pdf', raw)
    probe.keep('lifecycle-truth/partial-sync.json', json.dumps(truth).encode())
    entry = upload(probe, item, raw)
    assert entry['latest_attempt']['status'] == 'partial'
    item['id'] = entry['id']
    item['path'] = Path(entry['path'])
    probe.items.append(item)
    probe.register_source_paths()
    before = snapshot(probe, item)
    private = [i for i in probe.items if i['role'] == 'a' and i['project']['id'] == probe.projects['a'][1]['id']]
    assert private
    initial = probe.request('hub', '/v1/documents/files')
    assert not [row for row in initial if row.get('origin', {}).get('device_id') == probe.device_identities['a']]
    from document_formats_lifecycle_cache import inventory
    existing = inventory(probe.hub_state)
    probe.save('lifecycle-receiver-cache-before-authorization', existing)
    for document in probe.items:
        snapshot(probe, {**document, 'version': document.get('version', 1),
            'processing_version': document.get('processing_version', 1)})
    probe.cli('a', 'documents', 'sync')
    outgoing = inspect_default_off(probe, events(probe))
    current_rows = rows(probe, 'a')
    assert probe.request('hub', '/v1/documents/files') == initial
    # All source paths are removed before sending stored captures/results.
    for document in probe.items:
        if document.get('acquisition') == 'path':
            document['path'].unlink()
    probe.phase = 'archive-only'
    start = len(events(probe))
    probe.policy('a', probe.projects['a'][0])
    acknowledgement = probe.cli('a', 'documents', 'sync')
    assert acknowledgement['pending'] is False and acknowledgement['errors'] == []
    after = events(probe)[start:]
    assert any(e['kind'] == 'http-send' and e['bytes'] for e in after), 'No real outgoing HTTP observation'
    assert not [e for e in after if e['kind'] in {'content-processing', 'source-open'}]
    assert not [e for e in after if e['kind'] == 'child-start' and not e['allowed']]
    projected = next(p for p in probe.cli('hub', 'project', 'list') if p['owner'] == probe.device_identities['a']
        and p['source_key'] == probe.projects['a'][0]['stable_key'])
    allowed = [i for i in probe.items if i['role'] == 'a' and i['project']['id'] == probe.projects['a'][0]['id']]
    payloads = [(probe.out / 'actual-outbound-http' / e['sha256']).read_bytes()
                for e in after if e['kind'] == 'http-send']
    raw_controls, result_controls, reuse = [], [], []
    known_raw, known_results = set(existing['raw']), set(existing['results'])
    for document in allowed:
        result_sha = current_rows[document['id']]['published_snapshot']['result_sha256']
        result_raw = (probe.db['a'].parent / '.document-snapshots/results' / result_sha).read_bytes()
        assert len(document['raw']) <= 1024 * 1024 and len(result_raw) <= 1024 * 1024
        if document['sha256'] not in known_raw:
            assert any(document['raw'] in payload for payload in payloads)
            raw_controls.append(document['sha256'])
        else:
            reuse.append({'document_id': document['id'], 'kind': 'raw', 'sha256': document['sha256']})
        if result_sha not in known_results:
            assert any(result_raw in payload for payload in payloads)
            result_controls.append(result_sha)
        else:
            reuse.append({'document_id': document['id'], 'kind': 'results', 'sha256': result_sha})
        assert any(document['id'].encode() in payload for payload in payloads)
        known_raw.add(document['sha256'])
        known_results.add(result_sha)
    assert raw_controls and result_controls, 'Wire observer needs actual new raw and result body positive controls'
    probe.save('lifecycle-positive-wire-and-cache-reuse', {'new_raw_bodies': raw_controls,
        'new_result_bodies': result_controls, 'preexisting_or_prior_transfer_reuse': reuse,
        'semantics': 'Existing receiver byte-verified blobs may be resumed from their full received offset; repeated body transmission is not required. Every new origin is still sent and every received original/result is read independently below.'})
    received = probe.request('hub', '/v1/documents/files')
    own = [row for row in received if row.get('origin', {}).get('device_id') == probe.device_identities['a']]
    assert len(own) == len({row['id'] for row in own}) == len(allowed)
    assert {row['origin']['document_id'] for row in own} == {i['id'] for i in allowed}
    saved = {}
    for document in allowed:
        projected_item = {**document, 'version': document.get('version', 1),
            'processing_version': document.get('processing_version', 1), 'read_role': 'hub', 'read_project': projected}
        saved[document['id']] = snapshot(probe, projected_item)
        local = snapshot(probe, {**document, 'version': document.get('version', 1),
            'processing_version': document.get('processing_version', 1)})
        for key in ('text', 'locations', 'coverage', 'profile', 'result_sha256', 'processing_status'):
            assert saved[document['id']]['text'][key] == local['text'][key]
        structure = {'table_id', 'location', 'rows', 'columns', 'header_rows', 'sheet_state', 'cells',
            'window', 'window_origin', 'header_context', 'format', 'sha256', 'text_sha256', 'version',
            'processing_version', 'result_sha256', 'profile', 'coverage', 'processing_status'}
        assert [{k: v for k, v in t.items() if k in structure} for t in saved[document['id']]['tables']] == [
            {k: v for k, v in t.items() if k in structure} for t in local['tables']]
    assert saved[item['id']]['text']['processing_status'] == 'partial'
    # Pause only stops future transmission. The acknowledged snapshot remains
    # readable. An explicit source removal still withdraws it while paused.
    probe.policy('a', probe.projects['a'][0], False)
    probe.cli('a', 'documents', 'sync')
    def publication(value):
        # Pause changes visible provenance, while preserving the exact stored
        # content, structural metadata, identity, qualification and reference.
        value = dict(value)
        value.pop('reference', None)
        if 'origin_references' in value:
            value['origin_references'] = [{k: v for k, v in origin.items() if k != 'reference'}
                                          for origin in value['origin_references']]
        value.pop('snapshot_kind', None)
        value.pop('retained_snapshot', None)
        if 'sync_states' in value:
            value['sync_states'] = [{k: v for k, v in state.items() if k not in {'state', 'retained_snapshot'}}
                                    for state in value['sync_states']]
        return value
    for document in allowed:
        paused = snapshot(probe, {**document, 'version': document.get('version', 1),
            'processing_version': document.get('processing_version', 1), 'read_role': 'hub', 'read_project': projected},
            reference=saved[document['id']]['reference'])
        previous = saved[document['id']]
        assert paused['reference'] == previous['reference']
        assert paused['hit']['retained_snapshot'] is True
        assert paused['hit']['sync_states'] and all(state['state'] == 'paused' and state['retained_snapshot']
                                                  for state in paused['hit']['sync_states'])
        for view in ('hit', 'text', 'info'):
            assert publication(paused[view]) == publication(previous[view])
        assert [publication(table) for table in paused['tables']] == [publication(table) for table in previous['tables']]
    # Save independent identity before the source endpoint is stopped.
    probe.stop('a')
    for document in allowed:
        snapshot(probe, {**document, 'version': document.get('version', 1),
            'processing_version': document.get('processing_version', 1), 'read_role': 'hub', 'read_project': projected},
            reference=saved[document['id']]['reference'])
    probe.start('a')
    probe.save('lifecycle-sync-boundaries', {'allowed_ids': [i['id'] for i in allowed],
        'private_ids': [i['id'] for i in private], 'projected_project': projected,
        'default_disabled_wire_events': outgoing, 'successful_sync_ack': acknowledgement, 'source_paths_removed': True,
        'source_process_stopped_and_read': True, 'partial_reference': saved[item['id']]['reference'],
        'not_covered': ['second Local origin', 'conversation association', 'offline withdrawal']})
    return item, projected, saved


def independent_origins_and_associations(probe, projected):
    import sqlite3
    original = next(i for i in probe.items if i['role'] == 'a' and i['kind'] == 'docx'
                    and i['project']['id'] == probe.projects['a'][0]['id'])
    probe.phase = 'prepare'
    probe.start('b')
    assert probe.cli('b', 'configure-hub', probe.address['hub'], '008 independent B', '--token-file', probe.token_file)['connected']
    probe.wait_idle('b')
    bproject = probe.cli('b', 'project', 'create', '008 ordinary')
    directory = probe.fixtures / 'independent-b'
    directory.mkdir()
    path = directory / 'same.docx'
    path.write_bytes(original['raw'])
    source = probe.cli('b', 'documents', 'add', path, '--project-id', bproject['id'])
    probe.phase = 'explicit-refresh'
    probe.cli('b', 'documents', 'refresh', '--source-id', source['id'])
    probe.phase = 'archive-only'
    entries = probe.cli('b', 'documents', 'files', '--source-id', source['id'])
    assert len(entries) == 1 and entries[0]['latest_attempt']['status'] == 'ready'
    device = json.loads(probe.db['b'].with_suffix('.sqlite3.hub.json').read_text())['device_id']
    with sqlite3.connect(probe.db['b'].as_uri() + '?mode=ro', uri=True) as connection:
        archive = json.loads(connection.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    assert archive != probe.archive_identities['a'] and device != probe.device_identities['a']
    probe.archive_identities['b'] = archive
    probe.device_identities['b'] = device
    twin = {**original, 'role': 'b', 'project': bproject, 'id': entries[0]['id'],
            'version': 1, 'processing_version': 1, 'path': path}
    path.unlink()
    probe.policy('b', bproject)
    probe.cli('b', 'documents', 'sync')
    hub_b = next(p for p in probe.cli('hub', 'project', 'list') if p['owner'] == device
                 and p['source_key'] == bproject['stable_key'])
    twin_remote = {**twin, 'read_role': 'hub', 'read_project': hub_b}
    snapshot(probe, twin_remote)
    hub_native = {**original, 'role': 'hub', 'project': probe.projects['hub'][0],
                  'label': 'hub-independent-copy', 'version': 1, 'processing_version': 1}
    entry = upload(probe, hub_native, hub_native['raw'])
    hub_native['id'] = entry['id']
    hub_native['path'] = Path(entry['path'])
    probe.items.append(hub_native)
    probe.register_source_paths()
    snapshot(probe, hub_native)
    probe.cli('hub', 'project', 'link', projected['id'], hub_b['id'])
    probe.cli('hub', 'project', 'link', projected['id'], hub_native['project']['id'])
    result = probe.request('hub', '/v1/documents/search', probe.body('hub', query=original['query'],
        scope='project', project_id=projected['id'], limit=50))
    expected = {tuple(probe.expected_origin(i)[k] for k in ('device_id', 'archive_id', 'document_id'))
                for i in (original, twin, hub_native)}
    actual = [tuple(h['origin'][k] for k in ('device_id', 'archive_id', 'document_id')) for h in result['results']]
    assert len(actual) == len(set(actual)) == 3 and set(actual) == expected
    # Import a genuine synthetic Codex conversation, then link C->A. B and
    # native Hub projects are second-layer and must not appear from C.
    root = probe.fixtures / 'conversation'
    root.mkdir()
    cwd = root / 'Conversation C'
    cwd.mkdir()
    session = 'smm008-' + uuid4().hex
    messages = [{'type': 'session_meta', 'payload': {'id': session, 'cwd': str(cwd)}},
        {'type': 'response_item', 'ordinal': 1, 'payload': {'type': 'message', 'id': 'first',
            'role': 'user', 'content': [{'type': 'input_text', 'text': 'lifecyclechatneedle actual conversation'}]}}]
    (root / 'session.jsonl').write_text(''.join(json.dumps(m) + '\n' for m in messages), encoding='utf-8')
    probe.phase = 'conversation-import'
    probe.cli('a', 'sync', '--source', 'codex', '--root', root)
    probe.phase = 'archive-only'
    hits = probe.cli('a', 'search', 'lifecyclechatneedle', '--local', '--include-current')['results']
    assert len(hits) == 1 and hits[0]['source_session_id'] == session
    cproject = next(p for p in probe.cli('a', 'projects') if p['id'] == hits[0]['project_id'])
    probe.cli('a', 'upload', 'set', '--mode', 'only', '--project-id', cproject['id'])
    probe.phase = 'conversation-import'
    probe.request('a', '/api/sync?wait=true', {})
    probe.wait_idle('a')
    probe.phase = 'archive-only'
    hub_c = next(p for p in probe.cli('hub', 'project', 'list') if p['owner'] == probe.device_identities['a']
                 and p['source_key'] == cproject['stable_key'])
    probe.cli('hub', 'project', 'link', hub_c['id'], projected['id'])
    result = probe.cli('a', 'documents', 'search', original['query'], '--scope', 'project',
        '--project-id', cproject['id'], '--limit', 50)
    assert len(result['results']) == 1 and result['results'][0]['origin'] == probe.expected_origin(original)
    chat = probe.cli('a', 'search', 'lifecyclechatneedle', '--scope', 'project', '--hub-project-id', projected['id'], '--include-current')
    assert len(chat['results']) == 1 and chat['results'][0]['source_session_id'] == session
    assert [m['text'] for m in probe.cli('a', 'read', '--reference', chat['results'][0]['reference'])['messages']] == ['lifecyclechatneedle actual conversation']
    # Paused B retains its copy, but explicit removal offline must remain
    # pending across a real Local restart, then withdraw after reconnect.
    prior = snapshot(probe, twin_remote)
    probe.policy('b', bproject, False)
    probe.stop('hub')
    probe.cli('b', 'documents', 'remove', source['id'])
    pending = probe.cli('b', 'documents', 'sync')
    assert pending['pending'] and pending['errors']
    probe.stop('b')
    probe.start('b')
    assert probe.cli('b', 'documents', 'sync-status')['pending']
    probe.start('hub')
    assert probe.request('hub', '/v1/info')['document_epoch'] == probe.hub_context['document_epoch']
    probe.cli('b', 'documents', 'sync')
    reject_old(probe, 'hub', prior)
    for kept in ({**original, 'read_role': 'hub', 'read_project': projected}, hub_native):
        snapshot(probe, kept)
    probe.save('lifecycle-independent-origins', {'origins': [probe.expected_origin(i) for i in (original, twin, hub_native)],
        'same_bytes_sha256': original['sha256'], 'three_independent_hits': True,
        'conversation_project': hub_c, 'first_layer': projected, 'excluded_second_layer': [hub_b, hub_native['project']],
        'offline_pending': pending, 'withdrawn_after_reconnect': True})


def install_task_gate(probe):
    """Observe a real worker at its saved-raw read, without parser mocks."""
    import subprocess
    from document_formats_fixtures import docx_fixture
    from document_formats_installed_protocols import ROOT
    probe.gate_root = probe.out / 'fault-gate'
    probe.gate_root.mkdir()
    probe.fault_raw = docx_fixture('FAULTGATE')[0]
    probe.fault_sha = hashlib.sha256(probe.fault_raw).hexdigest()
    probe.gate_raw_paths = [str(parent / '.document-snapshots/raw' / probe.fault_sha)
                           for parent in (probe.db['a'].parent, probe.hub_state)]
    probe.keep('fault-input.docx', probe.fault_raw)
    code = (ROOT / 'tests/document_formats_lifecycle_hook.py').read_bytes()
    receipts = []
    for role in ('local', 'hub'):
        python = Path(probe.config[role + '_python'])
        process = subprocess.run([python, '-I', '-X', 'utf8', '-c',
            'import sysconfig;print(sysconfig.get_path("purelib"))'],
            capture_output=True, env=probe.env('a' if role == 'local' else 'hub'), timeout=20)
        assert process.returncode == 0, process.stderr
        site = Path(process.stdout.decode().strip())
        assert site.resolve().is_relative_to(python.parent.parent.resolve())
        module = site / '_smm_008_fault_gate.py'
        startup = site / '_smm_008_fault_gate.pth'
        assert not module.exists() and not startup.exists()
        module.write_bytes(code)
        startup.write_text('import _smm_008_fault_gate; _smm_008_fault_gate.install(' +
            repr(str(probe.gate_root)) + ',' + repr(probe.gate_raw_paths) + ',[])\n', encoding='utf-8')
        receipts.append({'role': role, 'module': str(module), 'sha256': hashlib.sha256(code).hexdigest(),
            'raw_paths': probe.gate_raw_paths, 'source': 'tests/document_formats_lifecycle_hook.py',
            'purpose': 'task-only raw-read barrier; actual worker process is terminated, no product return values changed'})
    probe.save('lifecycle-fault-gate-installation', receipts)


def actual_worker_exception(probe):
    import psutil
    from document_formats_platform import spawn_identity, matching_process
    observations = []
    for role in ('a', 'hub'):
        probe.phase = 'explicit-upload'
        armed = probe.gate_root / 'armed'
        armed.write_text(probe.fault_sha, encoding='utf-8')
        item = {'role': role, 'project': probe.projects[role][0], 'label': role + '-fault', 'format': 'docx'}
        receipt = upload(probe, item, probe.fault_raw, await_terminal=False)
        deadline = time.monotonic() + 30
        while True:
            files = [p for p in probe.gate_root.glob('*.json')]
            candidates = [json.loads(p.read_text()) for p in files]
            own = [entry for entry in candidates if entry['token'] == receipt['attempt_id']]
            if own:
                assert len(own) == 1
                worker = own[0]
                break
            assert time.monotonic() < deadline, receipt
            time.sleep(.02)
        process = psutil.Process(worker['pid'])
        assert process.create_time() == worker['created']
        assert process.exe() == worker['exe'] and process.cmdline() == worker['argv']
        assert worker['token'] in process.cmdline()
        expected_module = 'smm_hub._archive.document_worker' if role == 'hub' else 'smm_local.document_worker'
        assert expected_module in process.cmdline()
        stamp = spawn_identity(process)
        children = [spawn_identity(child) for child in process.children(recursive=True)]
        parent = probe.hub_state if role == 'hub' else probe.db['a'].parent
        root = parent / '.document-snapshots/tasks'
        while True:
            state = json.loads((root / 'active.json').read_text())
            if state.get('peak_rss', 0) > 0:
                break
            assert time.monotonic() < deadline
            time.sleep(.02)
        assert state['worker'] == {'pid': worker['pid'], 'created': worker['created']}
        assert state['rss_limit'] == 1024 * 1024 * 1024 and state['temp_limit'] == 256 * 1024 * 1024
        assert state['seconds_limit'] == 300 and state['gate_open'] is True
        if psutil.WINDOWS:
            assert state['windows_job']['atomic'] is True
        control = next(i for i in probe.items if i['role'] == role and i['kind'] == 'docx' and i.get('version') == 2)
        probe.phase = 'archive-only'
        saved = snapshot(probe, control)
        started = time.monotonic()
        process.kill()
        try:
            entry = wait(probe, role, receipt['document_id'], timeout=5)
            assert entry['latest_attempt']['status'] == 'failed'
            assert entry['published_snapshot'] is None
            until = started + 5
            proof = root / worker['token'] / 'cleanup.json'
            while not proof.exists() or (root / 'active.json').exists():
                assert time.monotonic() < until
                time.sleep(.02)
            assert time.monotonic() - started <= 5
            for member in [stamp, *children]:
                while matching_process(member) is not None:
                    assert time.monotonic() < until
                    time.sleep(.02)
            terminal_elapsed = time.monotonic() - started
            remaining = {p.name for p in proof.parent.iterdir()}
            assert remaining <= {'supervision.json', 'worker.stdout', 'worker.stderr', 'watchdog.stderr', 'cleanup.json'}
            unchanged_publication(snapshot(probe, control, reference=saved['reference']), saved)
            armed.unlink()
            # A new, legal document actually consumes the released slot.
            next_item = probe.material('docx', role + 'NEXTLEGAL')
            next_item.update(role=role, project=probe.projects[role][0], version=1, processing_version=1)
            ready = upload(probe, next_item, next_item['raw'])
            assert ready['latest_attempt']['status'] == 'ready'
            next_item['id'] = ready['id']
            next_item['path'] = Path(ready['path'])
            snapshot(probe, next_item)
            probe.items.append(next_item)
            probe.register_source_paths()
            observations.append({'role': role, 'worker': worker, 'actual_enrollment': stamp,
                'children': children, 'supervision': state, 'failed_attempt': entry['latest_attempt'],
                'cleanup': json.loads(proof.read_text()), 'seconds_to_terminal_cleanup': terminal_elapsed,
                'subsequent_document_id': next_item['id'], 'old_document_read_while_held_and_after': True})
        finally:
            (probe.gate_root / (worker['token'] + '.release')).touch()
            armed.unlink(missing_ok=True)
    probe.save('lifecycle-actual-worker-exception', observations)


def execute(config_path, output, *, native_service=False):
    import os
    import traceback
    from document_formats_installed_protocols import FormatProbe, ROOT
    from document_formats_wheel_preflight import verify_wheel_inputs
    from hub_documents_platform import now
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    verify_wheel_inputs(config, config_path.parent)
    if native_service:
        from document_formats_native_service import NativePosixProbe
        base_probe = NativePosixProbe
    else:
        base_probe = FormatProbe
    class LifecycleProbe(base_probe):
        def env(self, role='a'):
            value = super().env(role)
            if hasattr(self, 'gate_root'):
                value.update(SMM_008_ACTIVE_GATE=str(self.gate_root),
                    SMM_008_ACTIVE_RAW=json.dumps(self.gate_raw_paths), SMM_008_ACTIVE_SOURCES='[]')
            return value
    probe = LifecycleProbe(config, output)
    probe.native_actual_dependency_loss = native_service
    install_task_gate(probe)
    cwd = output / 'non-source-cwd'
    cwd.mkdir()
    os.chdir(cwd)
    bindings = probe.version_bindings()
    for name, expected in bindings.items():
        raw = (ROOT / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        probe.keep('source-snapshot/' + name, raw)
    probe.save('lifecycle-source-bindings', bindings)
    result = None
    try:
        probe.prepare_formats()
        probe.browser_uploads()
        if native_service:
            from document_formats_native_business import web_project
            web_project(probe)
        for item in probe.items:
            remember(probe, item, entry=item['entry'])
        from document_formats_protocol_guards import controls, events, assert_read_only
        controls(probe)
        update_each_format(probe)
        if not native_service:
            first_and_replacement_retry(probe)
        _, projected, _ = sync_and_project_boundaries(probe)
        probe.native_projected_project = projected
        independent_origins_and_associations(probe, projected)
        if native_service:
            from document_formats_native_business import dependency_isolation
            first_and_replacement_retry(probe, failure_controls=dependency_isolation)
        from document_formats_lifecycle_ownership import verify as ownership
        ownership(probe, projected)
        actual_worker_exception(probe)
        if native_service:
            from document_formats_native_business import interrupted_ocr
            interrupted_ocr(probe)
        from document_formats_lifecycle_readback import targets, replay
        probe.phase = 'read-only'
        observed = len(events(probe))
        cases = targets(probe)
        references = replay(probe, cases, 'lifecycle-before-restart')
        assert_read_only(probe, observed)
        probe.phase = 'service-control'
        for role in ('b', 'a', 'hub'):
            probe.stop(role)
        # Source bytes are no longer available, including managed copies.
        # Every post-restart read must use durable captured raw/results.
        for item in probe.items:
            item['path'].unlink(missing_ok=True)
        observed = len(events(probe))
        for role in ('hub', 'a', 'b'):
            probe.start(role)
        probe.phase = 'read-only'
        assert probe.request('hub', '/v1/info')['document_epoch'] == probe.hub_context['document_epoch']
        replay(probe, cases, 'lifecycle-after-restart', references)
        if native_service:probe.assert_restart_read_only(observed)
        else:assert_read_only(probe, observed)
        assert probe.version_bindings() == bindings
        result = {'status': 'passed', 'scope': 'installed lifecycle candidate subset',
            'actual_actor': probe.actor(), 'format_updates': 8, 'saved_candidate_retries': 8,
            'lifecycle_checks': ['eight format updates', 'eight saved retries', 'partial direct sync',
                'default-off observed HTTP', 'source deletion and offline source reads',
                'independent archive origins', 'one-layer conversation/document associations',
                'paused and offline withdrawal', 'two actual worker exceptions and next legal tasks',
                'failed publication visible Web details', 'lifecycle CLI/stdio/Web reads before and after actual restart'],
            'readback_cases': len(cases),
            'native_service': native_service,
            'not_covered': ['cross-OS directions', 'other E platforms',
                'complete management state combinations'], 'finished_at': now()}
    except BaseException:
        probe.save('failure', {'traceback': traceback.format_exc(), 'at': now()})
        raise
    finally:
        probe.cleanup()
    probe.save('result', result)


if __name__ == '__main__':
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-service', action='store_true')
    args = parser.parse_args()
    execute(args.target_config.resolve(), args.output.resolve(), native_service=args.native_service)

"""Explicit path refresh must finish a rejected publication and preserve retry."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import pytest
import psutil
from document_helpers import ROOT, fingerprint, observe
from document_formats_platform import utf8_environment, spawn_identity, process_tree, terminate_verified
from document_formats_partial_fixture import partial_pdf
from test_document_formats_management import native_input
from test_document_formats_installed_minimum import (
    assert_complete_source_text,
    test_complete_text_oracle_accepts_layouts_and_rejects_wrong_content as calibrate_text,
)
from test_document_formats_retry import ENGINE, DATA, FONT, keep
from test_document_formats_upload_restart import Server


@pytest.mark.skipif(not all((ENGINE, DATA, FONT)), reason='requires explicitly prepared real creator OCR assets')
@pytest.mark.parametrize('owner', ['local', 'hub'])
def test_path_refresh_configuration_rejection_finishes_and_retries_saved_capture(tmp_path, owner, monkeypatch):
    # TC-008-path-refresh-config-finalization; no cancellation/restart claim.
    calibrate_text()
    server = Server(tmp_path / owner, owner)
    if owner == 'hub':
        server.db = server.root / 'smm-hub.sqlite3'
    gate = server.root / 'publication-gate'
    gate.mkdir()
    monkeypatch.setenv('SMM_008_PUBLICATION_GATE', str(gate))
    for name in ('SMM_008_WEB_PROCESSING_GATE', 'SMM_008_WEB_READ_ONLY', 'SMM_008_RESTART_PAUSE'):
        monkeypatch.delenv(name, raising=False)
    (server.hooks / 'sitecustomize.py').write_text(
        'from document_formats_restart_server import install_audit\ninstall_audit()\n'
        'from document_formats_publication_hook import install\ninstall()\n', encoding='utf-8')
    prefix = ([sys.executable, '-B', '-m', 'smm_local.cli', '--db', str(server.db)] if owner == 'local'
              else [sys.executable, '-B', '-m', 'smm_hub.cli', 'hub', '--state-dir', str(server.root)]) + ['documents']
    env = utf8_environment(os.environ, PYTHONPATH=os.pathsep.join([str(server.hooks), str(ROOT / 'tests'), str(ROOT / 'src')]),
                           SMM_008_RESTART_AUDIT=str(server.root / 'cli-audit.jsonl'))
    items, children = [], []

    def save(name, value):
        keep('path-finalization/' + owner + '/' + name, json.dumps(value, ensure_ascii=False, indent=2).encode())

    def cli(*args, success=True):
        command = prefix + list(map(str, args))
        result = subprocess.run(command, cwd=server.root, env=env, capture_output=True, timeout=40)
        tag = uuid4().hex
        keep('path-finalization/' + owner + '/cli/' + tag + '.stdout', result.stdout)
        keep('path-finalization/' + owner + '/cli/' + tag + '.stderr', result.stderr)
        observe('path-cli', {'command': command, 'exit': result.returncode, 'stdout': result.stdout.decode('utf-8'), 'stderr': result.stderr.decode('utf-8')})
        assert (result.returncode == 0) if success else result.returncode != 0, result.stderr
        return json.loads(result.stdout) if success else result

    def configure():
        revision = cli('processing-status')['config']['revision']
        value = cli('processing-configure', '--expected-revision', revision, '--ocr-executable', ENGINE,
                    '--ocr-data-dir', DATA, '--languages', 'eng+chi_sim' if revision % 2 else 'chi_sim+eng')
        assert value['config']['revision'] == revision + 1 and value['ocr']['ready'] is True
        return revision + 1

    def files(item):
        return server.call('GET', '/documents/files?source_id=' + item['source']['id']).json()

    def entry(item):
        rows = files(item)
        assert len(rows) == 1 and rows[0]['path'] == str(item['path'])
        if 'id' in item:
            assert rows[0]['id'] == item['id']
        else:
            item['id'] = rows[0]['id']
        with sqlite3.connect('file:' + str(server.db) + '?mode=ro', uri=True) as connection:
            stored = connection.execute('SELECT id FROM documents WHERE path_key=?',
                                        (os.path.normcase(str(item['path'].resolve())),)).fetchone()
            archive_id = json.loads(connection.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        assert stored is not None and rows[0]['id'] == stored[0]
        item['archive_id'] = archive_id
        return rows[0]

    def source(item):
        return next(s for s in server.call('GET', '/documents/sources').json() if s['id'] == item['source']['id'])

    def make(key, project, status):
        format = 'pdf' if status == 'partial' else 'docx'
        versions = {}
        for version in (1, 2):
            if status == 'partial':
                raw, truth = partial_pdf(key + 'v' + str(version), FONT)
                truth = {'words': [truth['anchor']], 'excluded': [], 'tables': [], 'partial_reason': truth['known_failure']}
            else:
                raw, truth = native_input(format, key + 'v' + str(version))
                truth['ordered_groups'] = [[key + 'v' + str(version) + name for name in ('Before', 'Inserted', 'After')]]
            versions[version] = (raw, truth)
            keep('path-finalization/' + owner + '/inputs/' + key + str(version) + '.' + format, raw)
            save('truth/' + key + str(version) + '.json', truth)
        directory = server.root / 'sources' / key
        directory.mkdir(parents=True)
        path = directory / (key + '.' + format)
        path.write_bytes(versions[1][0])
        s = add_source(path, project)
        return {'key': key, 'project': project, 'path': path, 'source': s, 'status': status, 'versions': versions}

    def add_source(path, project, directory=False):
        if owner == 'hub':
            return cli('add', path, '--project-id', project['id'], *(['--no-recursive'] if directory else []))
        return server.call('POST', '/documents/sources', {**server.context, 'path': str(path),
            'project_ids': [project['id']], 'recursive': not directory}).json()

    def refresh(item):
        if owner == 'hub':
            return cli('refresh', '--source-id', item['source']['id'])
        return server.call('POST', '/documents/refresh', {**server.context, 'source_id': item['source']['id']}).json()

    def current_sources(value, item, allowed=None, envelope=None):
        expected = set(allowed) if allowed is not None else {item['source']['id']} | ({item['overlap']['id']} if 'overlap' in item else set())
        assert len(value['source_ids']) == len(set(value['source_ids'])) == len(expected)
        assert set(value['source_ids']) == expected
        if owner == 'hub':
            assert all((value if envelope is None else envelope)[key] == wanted for key, wanted in server.context.items())
            assert value['origin'] == {'device_id': server.context['hub_id'], 'archive_id': item['archive_id'], 'document_id': item['id']}
            assert value['project_ids'] == [item['project']['id']] and value['retained_snapshot'] is False
            assert isinstance(value['snapshot_kind'], str) and re.search(r'Hub|汇总|captur|receiv|native', value['snapshot_kind'], re.I)
            assert not re.search(r'暂停|paused', value['snapshot_kind'], re.I)
            states = value['sync_states']
            assert len(states) == len({state['source_id'] for state in states}) == len(expected)
            assert {state['source_id'] for state in states} == expected
            for state in states:
                ident = state['source_id']
                assert state == {'source_id': ident, 'origin': {'kind': 'hub', 'hub_id': server.context['hub_id'], 'source_id': ident},
                                 'project_key': None, 'project_ids': [item['project']['id']], 'state': 'native', 'retained_snapshot': False}
            if envelope is not None:
                configurations = {item['source']['id']: item['source']}
                if 'overlap' in item:
                    configurations[item['overlap']['id']] = item['overlap']
                provenance = value['provenance']
                assert len(provenance) == len({s['source_id'] for s in provenance}) == len(expected)
                assert {s['source_id'] for s in provenance} == expected
                for source in provenance:
                    assert source == {'source_id': source['source_id'], 'project_key': None,
                                      'source_revision': configurations[source['source_id']]['revision']}

    def full(item, version, reference=None, allowed=None):
        current = entry(item)
        raw, truth = item['versions'][version]
        reference = reference or current['original_reference']
        body = {**server.context, 'reference': reference}
        value = server.call('POST', '/documents/read', {**body, 'start': 0, 'end': current['text_length']}).json()
        current_sources(value, item, allowed)
        assert value['id'] == item['id'] and value['sha256'] == hashlib.sha256(raw).hexdigest()
        assert value['processing_status'] == item['status']
        assert value['format'] == item['path'].suffix[1:]
        assert value['version'] == current['version'] and value['processing_version'] == current['processing_version']
        assert value['result_sha256'] == current['published_snapshot']['result_sha256']
        assert_complete_source_text(value['text'], truth)
        assert not any(word in value['text'] for word in truth['excluded'])
        assert len(value['tables']) == len(truth['tables'])
        views, matched = [], set()
        for table in value['tables']:
            view = server.call('POST', '/documents/read', {**body, 'view': 'table', 'table_id': table['table_id'],
                'row_start': 1, 'row_end': table['rows'] + 1, 'column_start': 1, 'column_end': table['columns'] + 1}).json()
            current_sources(view, item, allowed)
            assert view['table_id'] == table['table_id'] and view['result_sha256'] == current['published_snapshot']['result_sha256']
            cells = [(c['row'], c['column'], c['text'], c['row_span'], c['column_span']) for c in view['cells']]
            indexes = [i for i, t in enumerate(truth['tables']) if (view['rows'], view['columns']) == (t['rows'], t['columns'])
                       and len(cells) == len(t['cells']) and set(cells) == set(t['cells'])
                       and all(view['location'].get(k) == v for k, v in t['location'].items())]
            assert len(indexes) == 1 and indexes[0] not in matched
            wanted = truth['tables'][indexes[0]]
            for cell in view['cells']:
                assert cell['location'] == {**wanted['location'],
                    'path': wanted['location']['path'] + '/row[' + str(cell['row']) + ']/cell[' + str(cell['column']) + ']'}
            matched.add(indexes[0])
            # Current providers may shrink while the referenced snapshot stays
            # valid. Those fields were checked against the independent phase
            # expectation above; retain every other snapshot/read field.
            views.append({key: value for key, value in view.items() if key not in
                          {'source_ids', 'sync_states', 'project_ids', 'retained_snapshot', 'snapshot_kind'}})
        if item['status'] == 'partial':
            assert any(e['page'] == 2 and truth['partial_reason']['reason_contains'] in e['reason'] for e in value['coverage']['errors'])
        original = server.call('POST', '/documents/original', body).content
        assert original == raw
        keep('path-finalization/' + owner + '/downloads/' + hashlib.sha256(raw).hexdigest(), original)
        search = server.call('POST', '/documents/search', {**server.context, 'query': truth['words'][0].split()[0],
            'scope': 'project', 'project_id': item['project']['id'], 'limit': 50, **({'local': True} if owner == 'local' else {})}).json()
        hits = search['results']
        assert [hit['id'] for hit in hits] == [item['id']]
        current_sources(hits[0], item, allowed, envelope=search)
        return {'reference': reference, 'text': value['text'], 'tables': views, 'coverage': value['coverage'],
                'profile': value['profile'], 'sha256': value['sha256'], 'version': value['version'], 'processing_version': value['processing_version']}

    def state():
        with sqlite3.connect(server.db) as connection:
            connection.row_factory = sqlite3.Row
            names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='documents' OR name LIKE 'document_%' OR name LIKE 'hub_document_%' OR name LIKE 'hub_processed_%')")]
            return {name: sorted([dict(row) for row in connection.execute('SELECT * FROM "' + name + '"')], key=lambda row: json.dumps(row, sort_keys=True, default=str)) for name in names}

    def others(current):
        assert full(control, 1, control['saved']['reference']) == control['saved'] and entry(control) == control['entry']
        for item in items:
            if item is current:
                continue
            if 'saved' in item:
                assert full(item, item['v'], item['saved']['reference']) == item['saved'] and entry(item) == item['entry']
            elif 'old' in item:
                assert full(item, 1, item['old']['reference']) == item['old'] and entry(item) == item['old_entry']

    try:
        server.start(); configure()
        projects = ([server.call('POST', '/projects', {'name': 'path ordinary'}).json(), server.call('POST', '/projects/global').json()] if owner == 'local'
                    else [server.call('POST', '/projects', {**server.context, 'name': 'path ' + kind, 'kind': kind}).json() for kind in ('ordinary', 'global')])
        control = make(owner + 'pathcontrol', projects[0], 'ready')
        refresh(control); control['saved'] = full(control, 1); control['entry'] = entry(control)
        for group, project in enumerate(projects):
            for before in ('none', 'ready', 'partial'):
                for index in (1, 2):
                    item = make(owner + 'path' + str(group) + before + str(index), project, 'partial' if before == 'partial' else 'ready')
                    item['before'] = before
                    if before != 'none':
                        refresh(item)
                        if index == 2:
                            overlap = add_source(item['path'].parent, project, directory=True)
                            item['overlap'] = overlap
                            refresh({**item, 'source': overlap})
                        item['old'] = full(item, 1); item['old_entry'] = entry(item)
                    items.append(item)
        assert len(items) == 12
        for item in items:
            version = 1 if item['before'] == 'none' else 2
            raw, truth = item['versions'][version]
            item['path'].write_bytes(raw); physical = fingerprint(item['path'])
            (gate / 'armed').write_text(hashlib.sha256(raw).hexdigest(), encoding='utf-8')
            with ThreadPoolExecutor(max_workers=1) as threads:
                future = child = stamp = None
                if owner == 'local':
                    future = threads.submit(server.client.post, server.prefix + '/documents/refresh', json={**server.context, 'source_id': item['source']['id']})
                else:
                    command = prefix + ['refresh', '--source-id', item['source']['id']]
                    output, errors = server.root / (item['key'] + '.stdout'), server.root / (item['key'] + '.stderr')
                    with output.open('wb') as out, errors.open('wb') as err:
                        child = subprocess.Popen(command, cwd=server.root, env=env, stdout=out, stderr=err, start_new_session=os.name != 'nt')
                    stamp = spawn_identity(psutil.Process(child.pid)); children.append((child, stamp))
                marker = None
                try:
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        for path in gate.glob('*.json'):
                            candidate = json.loads(path.read_bytes())
                            if candidate['raw_sha256'] == hashlib.sha256(raw).hexdigest() and not (gate / (candidate['attempt_id'] + '.release')).exists():
                                marker = candidate; break
                        if marker is not None:
                            break
                        if child is None:
                            assert not future.done(), future.result().text
                        else:
                            assert child.poll() is None, errors.read_text(encoding='utf-8')
                        time.sleep(.02)
                    assert marker and marker['result_status'] == item['status']
                    if marker['pid'] == server.serving_pid:
                        assert marker['created'] == server.serving_stamp['created'] and marker['argv'] == server.actual_argv
                        controller = 'HTTP service'
                    else:
                        assert child is not None
                        assert any(p['pid'] == marker['pid'] and p['created'] == marker['created'] for p in process_tree(stamp))
                        assert marker['argv'][1:] == command[1:]
                        controller = 'foreground CLI; service-handoff acceptance remains incomplete'
                    saved = (server.root / '.document-snapshots/results' / marker['result_sha256']).read_bytes()
                    assert hashlib.sha256(saved).hexdigest() == marker['result_sha256']
                    decoded = json.loads(saved)
                    assert decoded['raw_sha256'] == marker['raw_sha256'] and decoded['profile'] == marker['profile']
                    assert_complete_source_text(decoded['text'], truth)
                    keep('path-finalization/' + owner + '/results/' + marker['result_sha256'] + '.json', saved)
                    save('gates/' + marker['attempt_id'] + '.json', {**marker, 'actual_controller': controller})
                    revision = configure()
                    assert revision == marker['config_revision'] + 1
                    others(item)
                finally:
                    if marker:
                        (gate / (marker['attempt_id'] + '.release')).touch()
                    else:
                        (gate / 'abort').touch()
                    (gate / 'armed').unlink(missing_ok=True)
                if child is None:
                    response = future.result(timeout=25)
                    assert response.status_code == 200 or 400 <= response.status_code < 500, response.text
                    save('responses/' + marker['attempt_id'] + '.json', {'status': response.status_code, 'body': response.json()})
                else:
                    child.wait(timeout=25)
                    keep('path-finalization/' + owner + '/cli/' + item['key'] + '.stdout', output.read_bytes())
                    keep('path-finalization/' + owner + '/cli/' + item['key'] + '.stderr', errors.read_bytes())
                    if child.returncode != 0:
                        assert re.search(r'配置|发布|config|publish|revision|失效|profile|stale', errors.read_text(encoding='utf-8'), re.I)
                    else:
                        json.loads(output.read_bytes())
                    save('responses/' + marker['attempt_id'] + '.json', {'cli_exit': child.returncode, 'actual_controller': controller})
            current_source = source(item)
            assert current_source['status'] in {'failed', 'partial'}, current_source
            assert current_source['counts']['failed'] == current_source['counts']['candidates'] == 1 and current_source['counts']['ready'] == 0
            current = entry(item)
            latest = current['latest_attempt']
            assert current['status'] == 'failed' and latest['status'] == 'failed' and not current['publication_pending']
            assert latest['attempt_id'] == marker['attempt_id'] and latest['capture_id'] == marker['capture_id']
            assert isinstance(latest['error'], str) and latest['error'].strip()
            assert re.search(r'配置|发布|config|publish|revision|失效|profile|stale', latest['error'], re.I)
            assert isinstance(current['error'], str) and current['error'].strip()
            assert latest['finished_at'] and fingerprint(item['path']) == physical
            expected = 0 if item['before'] == 'none' else 1
            assert current['version'] == current['processing_version'] == expected
            assert current['published_snapshot'] == (None if expected == 0 else item['old_entry']['published_snapshot'])
            target = current['retry_target']
            assert target == {'capture_id': marker['capture_id'], 'sha256': marker['raw_sha256'], 'expected_attempt_id': marker['attempt_id'], 'expected_version': expected, 'expected_processing_version': expected}
            hidden_search = server.call('POST', '/documents/search', {**server.context, 'query': truth['words'][0].split()[0],
                'scope': 'project', 'project_id': item['project']['id'], 'limit': 50, **({'local': True} if owner == 'local' else {})}).json()
            if owner == 'hub':
                assert all(hidden_search[key] == wanted for key, wanted in server.context.items())
            assert hidden_search['results'] == []
            if 'overlap' in item:
                assert current['original_reference'] and current['original_available'] is True
                assert server.call('POST', '/documents/original', {**server.context, 'reference': current['original_reference']}).content == item['versions'][1][0]
            else:
                assert current['original_reference'] is None and current['original_available'] is False
            if 'old' in item:
                if 'overlap' in item:
                    assert full(item, 1, item['old']['reference'], allowed={item['overlap']['id']}) == item['old']
                else:
                    for body in [{'start': 0, 'end': item['old_entry']['text_length']}, {'view': 'original-info'}] + [
                        {'view': 'table', 'table_id': table['table_id']} for table in item['old']['tables']]:
                        rejected = server.client.post(server.prefix + '/documents/read', json={**server.context, 'reference': item['old']['reference'], **body})
                        observe('path-oldref-rejected', {'owner': owner, 'id': item['id'], 'view': body, 'status': rejected.status_code, 'body': rejected.json()})
                        assert 400 <= rejected.status_code < 500
                    rejected = server.client.post(server.prefix + '/documents/original', json={**server.context, 'reference': item['old']['reference']})
                    assert 400 <= rejected.status_code < 500
            others(item)
            item['path'].unlink()
            args = ['reprocess', '--document-id', item['id']] + [x for key in ('capture_id', 'expected_attempt_id', 'expected_version', 'expected_processing_version') for x in ('--' + key.replace('_', '-'), target[key])]
            cli(*args)
            now = entry(item)
            assert now['latest_attempt']['capture_id'] == marker['capture_id'] and now['latest_attempt']['attempt_id'] != marker['attempt_id']
            assert now['latest_attempt']['config_revision'] == revision and now['latest_attempt']['status'] == item['status'] and not now['publication_pending']
            assert now['version'] == now['processing_version'] == expected + 1
            item['v'] = version; item['saved'] = full(item, version); item['entry'] = entry(item)
            assert item['saved']['profile']['config_revision'] == revision
            # Publishing a new content/processing version must never lend
            # the new snapshot to a pre-failure reference, including one that
            # an overlapping continuous source kept readable during failure.
            if 'old' in item:
                for body in [{'start':0,'end':item['old_entry']['text_length']},{'view':'original-info'}]+[
                        {'view':'table','table_id':table['table_id']} for table in item['old']['tables']]:
                    rejected=server.client.post(server.prefix+'/documents/read',json={**server.context,'reference':item['old']['reference'],**body})
                    observe('path-recovered-oldref-rejected',{'owner':owner,'id':item['id'],'view':body,'status':rejected.status_code,'body':rejected.json()})
                    assert 400<=rejected.status_code<500
                rejected=server.client.post(server.prefix+'/documents/original',json={**server.context,'reference':item['old']['reference']})
                observe('path-recovered-old-original-rejected',{'owner':owner,'id':item['id'],'status':rejected.status_code})
                assert 400<=rejected.status_code<500
            before = state()
            if owner=='hub':assert 'hub_document_processing_jobs' in before
            rejected = cli(*args, success=False)
            assert re.search(r'过期|撤销|stale|expired|撤回|不一致', rejected.stderr.decode('utf-8'), re.I)
            assert state() == before
            others(item)
            save('completed/' + marker['attempt_id'] + '.json', {'source': current_source, 'failed': current, 'recovered': item['entry'], 'retry': target})
        assert len({item['id'] for item in [control, *items]}) == 13
        stored = server.call('GET', '/documents/files').json()
        assert {row['id'] for row in stored} == {item['id'] for item in [control, *items]}
        expected_pairs = {(item['id'], item['source']['id']) for item in [control, *items]}
        expected_pairs |= {(item['id'], item['overlap']['id']) for item in items if 'overlap' in item}
        assert len(stored) == len(expected_pairs) == 17
        assert {(row['id'], row['source_id']) for row in stored} == expected_pairs
    finally:
        (gate / 'abort').touch()
        for child, stamp in children:
            if child.poll() is None:
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    terminate_verified(process_tree(stamp), owner=child)
        if server.process is not None:
            server.stop()

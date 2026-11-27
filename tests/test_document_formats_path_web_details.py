"""Path sources expose the same saved-attempt details as managed uploads."""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from document_helpers import ROOT, observe
from document_formats_partial_fixture import partial_pdf
from document_formats_web_helpers import Browser
from test_document_formats_management import native_input
from test_document_formats_retry import FONT, keep, scan_pdf
from test_document_formats_upload_restart import Server


@pytest.mark.skipif(not (FONT and os.environ.get('PLAYWRIGHT_BROWSERS_PATH')),
                    reason='requires prepared real font and browser')
def test_path_files_web_details_match_each_saved_capture(tmp_path, monkeypatch):
    # TC-008-path-web-details
    from playwright.sync_api import expect
    server = Server(tmp_path / 'local', 'local')
    audit = server.root / 'read-only-events.jsonl'
    items = []
    evidence = Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR', str(tmp_path / 'evidence')))
    evidence.mkdir(exist_ok=True)
    try:
        server.start()
        projects = [server.call('POST', '/projects', {'name': 'path details'}).json(),
                    server.call('POST', '/projects/global', {}).json()]
        sources = []
        for number, project in enumerate(projects):
            directory = tmp_path / ('materials-' + str(number))
            directory.mkdir()
            for status in ('ready', 'partial', 'failed'):
                for index in range(2):
                    key = 'pathdetail' + str(number) + status + str(index)
                    if status == 'ready':
                        raw, _ = native_input('docx', key)
                    elif status == 'partial':
                        raw, _ = partial_pdf(key, FONT)
                    else:
                        raw = scan_pdf(key)
                    path = directory / (key + ('.docx' if status == 'ready' else '.pdf'))
                    path.write_bytes(raw)
                    items.append({'path': path, 'raw': raw, 'mtime': path.stat().st_mtime_ns,
                                  'status': status, 'project': project})
            source = server.call('POST', '/documents/sources',
                                 {'path': str(directory), 'project_ids': [project['id']]}).json()
            sources.append(source)
            server.call('POST', '/documents/refresh', {'source_id': source['id']})
            rows = server.call('GET', '/documents/files?source_id=' + source['id']).json()
            expected = [i for i in items if i['project'] == project]
            assert len(rows) == len({r['id'] for r in rows}) == len(expected)
            assert {r['path'] for r in rows} == {str(i['path']) for i in expected}
            for item in expected:
                row = next(r for r in rows if r['path'] == str(item['path']))
                item['entry'] = row
                latest = row['latest_attempt']
                assert latest['status'] == item['status']
                with sqlite3.connect(server.db) as con:
                    con.row_factory=sqlite3.Row
                    docs=[dict(v) for v in con.execute('SELECT pk,id,path,version FROM documents WHERE path=?',(str(item['path']),))]
                    assert len(docs)==1
                    doc=docs[0];state=dict(con.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(doc['pk'],)).fetchone())
                    capture=dict(con.execute('SELECT * FROM document_captures WHERE id=?',(state['current_capture'],)).fetchone())
                    attempt=dict(con.execute('SELECT * FROM document_processing_attempts WHERE id=?',(state['latest_attempt'],)).fetchone())
                    published=dict(con.execute('SELECT * FROM document_captures WHERE id=?',(state['published_capture'],)).fetchone()) if state['published_capture'] else None
                assert row['id']==doc['id'] and doc['path']==str(item['path'])
                assert capture['raw_sha256']==hashlib.sha256(item['raw']).hexdigest() and capture['raw_bytes']==len(item['raw'])
                assert latest=={'attempt_id':state['latest_attempt'],'capture_id':attempt['capture_id'],
                    'status':item['status'],'config_revision':attempt['config_revision'],'error':attempt['error'],
                    'created_at':attempt['created_at'],'finished_at':attempt['finished_at']}
                assert attempt['capture_id']==capture['id'] and attempt['state']==item['status']
                expected_version=0 if item['status']=='failed' else 1
                assert row['version']==doc['version']==row['processing_version']==state['processing_version']==expected_version
                retry={'capture_id':capture['id'],'sha256':hashlib.sha256(item['raw']).hexdigest(),
                    'expected_attempt_id':state['latest_attempt'],'expected_version':expected_version,
                    'expected_processing_version':expected_version}
                assert row['retry_target']==retry
                saved=None
                if item['status']=='failed':
                    assert published is None and row['published_snapshot'] is None and latest['error']
                else:
                    assert published['id']==capture['id'] and published['raw_sha256']==hashlib.sha256(item['raw']).hexdigest()
                    result_raw=(server.root/'.document-snapshots/results'/state['result_sha256']).read_bytes()
                    assert hashlib.sha256(result_raw).hexdigest()==state['result_sha256']
                    item['expected_coverage']=json.loads(result_raw)['coverage']
                    saved={'capture_id':published['id'],'sha256':hashlib.sha256(item['raw']).hexdigest(),
                        'raw_bytes':len(item['raw']),'version':1,'processing_version':1,
                        'result_sha256':hashlib.sha256(result_raw).hexdigest(),'status':item['status']}
                    assert row['published_snapshot']==saved and state['published_status']==item['status']
                item['expected_fields']={'published_snapshot':saved,
                    'latest_attempt':{k:latest[k] for k in ('capture_id','attempt_id','status','config_revision','error')},
                    'retry_target':retry}
            observe('path-web-source-truth', {'source': source, 'files': rows})
        # A read-only serving fixture makes any source read or processing
        # attempt fail in the actual server, not just in a browser mock.
        server.stop()
        monkeypatch.setenv('SMM_008_WEB_READ_ONLY', str(audit))
        server.start(deny=[i['path'] for i in items])
        response = server.client.post('/__test_processing_probe', json={})
        assert response.status_code == 200
        probe = response.json()
        assert probe['blocked'] == ['processing', 'subprocess']
        audit_before = audit.read_bytes()
        before = {}
        with sqlite3.connect(server.db) as con:
            for table in ('document_captures', 'document_processing_attempts', 'document_capture_authorizations'):
                before[table] = con.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall()
        with Browser(server, evidence) as browser:
            browser.page.route('**/api/documents/refresh', lambda route: (_ for _ in ()).throw(AssertionError('details triggered refresh')))
            browser.page.route('**/api/documents/reprocess', lambda route: (_ for _ in ()).throw(AssertionError('details triggered reprocess')))
            box = browser.page.locator('#doc-file-list')
            for source, project in zip(sources, projects):
                browser.page.locator('[data-doc-files="' + source['id'] + '"]').click()
                expected = [i for i in items if i['project'] == project]
                for item in expected:
                    row = box.locator('p.paths, .result').filter(has_text=str(item['path']))
                    expect(row).to_have_count(1)
                    expect(row).to_contain_text(item['status'])
                    row.get_by_text('查看处理详情与重试比较值', exact=True).click()
                    fields = {}
                    for field in ('published_snapshot', 'latest_attempt', 'retry_target'):
                        node = row.locator('pre[data-native-detail="' + field + '"]')
                        expect(node).to_be_visible()
                        value = json.loads(node.inner_text())
                        wanted = item['expected_fields'][field]
                        assert value == wanted
                        fields[field] = value
                    if item['status'] == 'partial':
                        coverage = row.locator('pre[data-native-detail="coverage"]')
                        expect(coverage).to_be_visible()
                        expect(coverage).to_contain_text('组件探测')
                        value = json.loads(coverage.inner_text())
                        assert value==item['expected_coverage']
                        assert any(e['page'] == 2 and e['method'] == 'ocr' and '组件探测' in e['reason'] for e in value['errors'])
                    name = item['path'].stem + '.png'
                    row.screenshot(path=str(evidence / name))
                    observe('path-web-visible-details', {'document_id': item['entry']['id'],
                            'path': str(item['path']), 'fields': fields, 'screenshot': name})
                assert box.locator('pre[data-native-detail="latest_attempt"]').count() == len(expected)
                for other in (i for i in items if i['project'] != project):
                    expect(box).not_to_contain_text(str(other['path']))
        with sqlite3.connect(server.db) as con:
            assert all(con.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall() == values for table, values in before.items())
        assert audit.read_bytes() == audit_before and not any(e.get('event') == 'open' for e in server.events())
        assert all(i['path'].read_bytes() == i['raw'] and i['path'].stat().st_mtime_ns == i['mtime'] for i in items)
    finally:
        server.stop()

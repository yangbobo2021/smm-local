"""Real delayed HTTP refresh must retain same-project rows and reject stale replies."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from uuid import uuid4

import pytest
from document_helpers import observe
from document_formats_web_helpers import Browser
from test_document_formats_retry import keep
from test_document_formats_upload_restart import Server

pytestmark = pytest.mark.skipif(not os.environ.get('PLAYWRIGHT_BROWSERS_PATH'), reason='requires prepared actual Chromium')


@pytest.mark.parametrize('owner', ['local', 'hub'])
def test_library_refresh_keeps_current_rows_but_never_another_project(tmp_path, owner):
    from playwright.sync_api import expect
    server = Server(tmp_path / owner, owner)
    if owner == 'hub':
        server.db = server.root / 'smm-hub.sqlite3'
    evidence = Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR', tmp_path / 'evidence')) / ('refresh-' + owner)
    evidence.mkdir(parents=True)
    held = []
    try:
        server.start()
        projects, assets = [], []
        for name in ('alpha', 'beta'):
            project = server.call('POST', '/projects', {**server.context, 'name': name, **({'kind': 'ordinary'} if owner == 'hub' else {})}).json()
            raw = ('independent library ' + name + '\n').encode()
            asset = server.call('POST', '/documents/library', {**server.context, 'project_id': project['id'],
                'project_key': project['stable_key'] if owner == 'local' else project['source_key'],
                'name': name + '.md', 'submission_id': uuid4().hex,
                'content_base64': base64.b64encode(raw).decode()}).json()
            projects.append(project)
            assets.append(asset)
        with Browser(server, evidence) as web:
            web.project(projects[0], library=True)
            rows = web.page.locator('#' + web.prefix + '-library-list .result')
            expect(rows).to_have_count(1)
            expect(rows).to_contain_text(assets[0]['id'])
            def delay(route):
                # Fetch the actual service response unchanged, then delay only
                # its delivery. No fabricated rows, status or business payload.
                response = route.fetch()
                raw = response.body()
                keep('delayed-library/' + hashlib.sha256(raw).hexdigest() + '.json', raw)
                held.append({'route': route, 'response': response, 'url': route.request.url, 'released': False})
            web.context.route('**/documents/library?project_id=*', delay)
            select = web.page.locator('#doc-library-project' if owner == 'local' else '#hub-project')
            select.select_option(str(projects[0]['id']))
            deadline = time.monotonic() + 10
            while not held:
                assert time.monotonic() < deadline
                web.page.wait_for_timeout(20)
            before = rows.all_text_contents()
            web.screenshot('same-project-response-pending')
            observe('same-project-library-refresh-held', {'owner': owner, 'expected_id': assets[0]['id'],
                'actual_rows': before, 'response_status': held[0]['response'].status, 'url': held[0]['url']})
            assert len(before) == 1 and assets[0]['id'] in before[0], 'same-project refresh hid its current document while awaiting HTTP'
            select.select_option(str(projects[1]['id']))
            while len(held) < 2:
                assert time.monotonic() < deadline
                web.page.wait_for_timeout(20)
            assert rows.all_text_contents() == [], 'project switch leaked previous project rows'
            held[1]['route'].fulfill(response=held[1]['response']);held[1]['released'] = True
            expect(rows).to_have_count(1)
            expect(rows).to_contain_text(assets[1]['id'])
            held[0]['route'].fulfill(response=held[0]['response']);held[0]['released'] = True
            web.page.wait_for_load_state('networkidle')
            after = rows.all_text_contents()
            assert len(after) == 1 and assets[1]['id'] in after[0] and assets[0]['id'] not in after[0]
            web.screenshot('new-project-after-stale-old-response')
            observe('library-refresh-project-fence', {'owner': owner, 'project_ids': [p['id'] for p in projects],
                'document_ids': [a['id'] for a in assets], 'same_project_rows': before, 'final_rows': after,
                'old_response_cannot_overwrite': True, 'response_release_order': [1, 0]})
            web.context.unroute('**/documents/library?project_id=*', delay)
    finally:
        # Releasing the actual replies is observation cleanup, not completion
        # of a failed business assertion. Browser may already have closed.
        for item in held:
            if not item['released']:
                try:item['route'].fulfill(response=item['response'])
                except Exception:pass
        server.stop()

"""Real CLI, stdio and Web readbacks of the lifecycle driver's saved states."""
from __future__ import annotations
import asyncio
import json


TEXT = ('origin', 'format', 'version', 'processing_version', 'sha256', 'text_sha256',
        'result_sha256', 'processing_status', 'profile', 'coverage', 'locations', 'tables',
        'text', 'text_length', 'start', 'end', 'start_line', 'end_line')
TABLE = ('origin', 'format', 'version', 'processing_version', 'sha256', 'result_sha256',
         'table_id', 'location', 'rows', 'columns', 'header_rows', 'sheet_state', 'cells',
         'window', 'window_origin', 'header_context')
INFO = ('origin', 'format', 'version', 'processing_version', 'sha256', 'result_sha256', 'available', 'bytes')


def fields(value, keys):
    return {key: value[key] for key in keys if key in value}


def visible_table(browser, table):
    """Check actual rendered cell coordinates, spans and text, not HTTP alone."""
    from playwright.sync_api import expect
    root = browser.page.locator('#' + browser.prefix + '-table-cells')
    expect(root).to_be_visible()
    nodes = root.locator('[data-row][data-column]')
    assert nodes.count() == len(table['cells'])
    for cell in table['cells']:
        node = root.locator('[data-row="' + str(cell['row']) + '"][data-column="' + str(cell['column']) + '"]')
        expect(node).to_have_count(1)
        assert node.get_attribute('rowspan') == str(cell['row_span'])
        assert node.get_attribute('colspan') == str(cell['column_span'])
        button = node.locator('[data-cell-text]')
        expect(button).to_be_visible()
        assert button.text_content() == (cell.get('text') or '')


def failed_detail(probe, item, entry, stage):
    """Inspect the actual visible failure and the exact retry comparison values."""
    from playwright.sync_api import expect
    from document_formats_lifecycle_visual import capture
    from test_document_formats_web_uploads import assert_ui_snapshot
    role = item['role']
    submitted_name = item['label'] + '.' + item['format']
    if entry.get('display_name') is not None:
        assert entry['display_name'] == submitted_name
    # Local files metadata omits the managed display name. The submitted name
    # is an independent expectation for the actual visible library row.
    entry = {**entry, 'display_name': submitted_name}
    with probe.browser(role, stage + '-' + item['label']) as browser:
        browser.project(item['project'], library=True)
        selector = '#doc-library-list .result' if role == 'a' else '#hub-library-list .result'
        owner = 'local' if role == 'a' else 'hub'
        row = assert_ui_snapshot(browser.page, owner, entry, item['format'])
        expect(row.locator(':scope > p').first).to_contain_text(' · 文档 ' + item['id'] + ' · ')
        latest = {key: entry['latest_attempt'][key] for key in ('capture_id', 'attempt_id', 'status', 'config_revision', 'error')}
        assert latest['status'] == 'failed' and latest['error']
        expect(row).to_contain_text('版本 ' + str(entry['version']) + ' · 处理版本 ' + str(entry['processing_version']))
        button = row.get_by_role('button', name='下载采集原件', exact=True)
        if entry['published_snapshot'] is None:
            expect(button).to_be_disabled()
        else:
            expect(button).to_be_enabled()
            browser.download(button, item)
        proof = capture(browser.page, owner, entry, item['format'], browser.evidence / (stage + '-target.png'))
        assert_ui_snapshot(browser.page, owner, entry, item['format'])
        probe.save(stage + '-visible-' + item['label'], {'role': role, 'document_id': item['id'],
            'expected_details': {'published_snapshot': entry['published_snapshot'], 'latest_attempt': latest,
                'retry_target': entry['retry_target']},
            'actual_visible_details_evidence': 'web-visible-row-snapshot observation attachments before and after capture',
            'capture': proof, 'browser_events': browser.events})


def targets(probe):
    from document_formats_installed_lifecycle import snapshot
    projected_rows = probe.request('hub', '/v1/documents/files')
    cases = []
    for original in probe.items:
        item = {**original, 'version': original.get('version', 1), 'processing_version': original.get('processing_version', 1)}
        canonical = snapshot(probe, item)
        if item['role'] == 'a':
            cases.append({'role': 'a', 'remote': False, 'project': item['project'], 'item': item, 'canonical': canonical})
            own = [row for row in projected_rows if row['origin'] == probe.expected_origin(item)]
            if own:
                assert len(own) == 1 and len(own[0]['project_ids']) == 1
                project = {'id': own[0]['project_ids'][0]}
                for role in ('hub', 'a'):
                    cases.append({'role': role, 'remote': role == 'a', 'project': project,
                                  'item': item, 'canonical': canonical})
        else:
            for role in ('hub', 'a'):
                cases.append({'role': role, 'remote': role == 'a', 'project': item['project'],
                              'item': item, 'canonical': canonical})
    for case in cases:
        case['key'] = case['role'] + '-' + ('remote' if case['remote'] else 'native') + '-' + case['item']['id']
    assert len(cases) == len({case['key'] for case in cases})
    return cases


def plans(case):
    canonical = case['canonical']
    result = [({'start': 0, 'end': canonical['hit']['text_length']}, canonical['text'], TEXT),
              ({'view': 'original-info'}, canonical['info'], INFO)]
    for table in canonical['tables']:
        result.append(({'view': 'table', 'table_id': table['table_id'], 'row_start': 1,
            'row_end': table['rows'] + 1, 'column_start': 1, 'column_end': table['columns'] + 1}, table, TABLE))
    return result


def checked_hit(probe, case, result):
    own = [hit for hit in result['results'] if hit['origin'] == probe.expected_origin(case['item'])]
    assert len(own) == 1
    for key in ('origin', 'format', 'version', 'processing_version', 'sha256', 'result_sha256'):
        assert own[0][key] == case['canonical']['hit'][key]
    return own[0]


def replay(probe, cases, phase, saved=None):
    """Each entry uses its own search reference, then that reference after restart."""
    refs = {'cli': {}, 'mcp': {}, 'web': {}}
    for case in cases:
        role, item, key = case['role'], case['item'], case['key']
        args = ['documents', 'search', item['query'], '--scope', 'project',
                '--hub-project-id' if case['remote'] else '--project-id', case['project']['id'], '--limit', 50]
        if role == 'a' and not case['remote']:
            args.append('--local')
        hit = checked_hit(probe, case, probe.cli(role, *args))
        reference = saved['cli'][key] if saved else hit['reference']
        refs['cli'][key] = reference
        for body, expected, keys in plans(case):
            arguments = ['documents', 'read', '--reference', reference]
            for name, value in body.items():
                arguments.extend(['--' + name.replace('_', '-'), value])
            actual = probe.cli(role, *arguments)
            assert fields(actual, keys) == fields(expected, keys), (key, body)
        output = probe.out / (phase + '-cli-' + key + '.' + item['format'])
        downloaded = probe.cli(role, 'documents', 'read', '--reference', reference, '--original-output', output)
        assert output.read_bytes() == item['raw'] and downloaded['sha256'] == item['sha256']
    local = [case for case in cases if case['role'] == 'a']
    requests = [('search_documents', {'query': case['item']['query'], 'scope': 'project', 'limit': 50,
        **({'hub_project_id': case['project']['id']} if case['remote'] else {'project_id': case['project']['id'], 'local': True})})
        for case in local]
    hits = asyncio.run(probe.mcp('a', requests))
    requests, expected = [], []
    for case, result in zip(local, hits, strict=True):
        hit = checked_hit(probe, case, result)
        reference = saved['mcp'][case['key']] if saved else hit['reference']
        refs['mcp'][case['key']] = reference
        for body, wanted, keys in plans(case):
            requests.append(('read_document', {'reference': reference, **body}))
            expected.append((wanted, keys))
    actual = asyncio.run(probe.mcp('a', requests))
    for value, (wanted, keys) in zip(actual, expected, strict=True):
        assert fields(value, keys) == fields(wanted, keys)
    for case in local:
        reference = refs['mcp'][case['key']]
        assert probe.raw_original('a', reference) == case['item']['raw']
        output = probe.out / (phase + '-mcp-' + case['key'] + '.' + case['item']['format'])
        probe.cli('a', 'documents', 'read', '--reference', reference, '--original-output', output)
        assert output.read_bytes() == case['item']['raw']
    for role in ('a', 'hub'):
        with probe.browser(role, phase) as browser:
            browser.page.locator('#' + browser.prefix + '-limit').select_option('50')
            for case in (case for case in cases if case['role'] == role):
                item, key = case['item'], case['key']
                result = browser.search(case['project'], item['query'], remote=case['remote'])
                hit = checked_hit(probe, case, result)
                reference = saved['web'][key] if saved else hit['reference']
                refs['web'][key] = reference
                selector = '#doc-results .result' if role == 'a' else '#hub-results .result'
                row = browser.page.locator(selector).filter(has_text=item['id'])
                assert row.count() == 1
                default = browser.action('text', row.get_by_role('button', name='读取原文', exact=True).click)
                assert (default['start'], default['end']) == (hit['start'], hit['end'])
                assert default['text'] == case['canonical']['text']['text'][default['start']:default['end']]
                for body, wanted, keys in plans(case):
                    if body.get('view') == 'original-info':
                        value = browser.info()
                    elif body.get('view') == 'table':
                        browser.page.locator('#' + browser.prefix + '-table-select').select_option(body['table_id'])
                        value = browser.table_range((body['row_start'], body['row_end'] - 1,
                            body['column_start'], body['column_end'] - 1))
                        visible_table(browser, wanted)
                    else:
                        value = browser.text_range(body['start'], body['end'])
                        from playwright.sync_api import expect
                        node = browser.page.locator('#doc-reader-text' if role == 'a' else '#hub-read-text')
                        expect(node).to_be_visible()
                        assert node.text_content() == wanted['text']
                    assert fields(value, keys) == fields(wanted, keys), (key, body)
                browser.download(browser.page.locator('#' + browser.prefix + '-original-download'), item)
                if saved:
                    # The page UI has no opaque-reference paste control. Use
                    # this authenticated real browser's same public HTTP route
                    # to read its earlier reference as well as the new UI hit.
                    # No product state/response/DOM is changed by the probe.
                    headers = {'Content-Type': 'application/json', 'X-SMM-UI': '1'}
                    if role == 'hub':
                        headers['Authorization'] = 'Bearer ' + probe.token
                    for body, wanted, keys in plans(case):
                        value = browser.page.evaluate('''async ({url,headers,body})=>{
                            const response=await fetch(url,{method:'POST',headers,body:JSON.stringify(body)});
                            return {status:response.status,value:await response.json()};
                        }''', {'url': probe.path(role, '/documents/read'), 'headers': headers,
                               'body': probe.body(role, reference=reference, **body)})
                        assert value['status'] == 200
                        assert fields(value['value'], keys) == fields(wanted, keys), (key, 'old Web ref', body)
                    value = browser.page.evaluate('''async ({url,headers,body})=>{
                        const response=await fetch(url,{method:'POST',headers,body:JSON.stringify(body)});
                        return {status:response.status,bytes:Array.from(new Uint8Array(await response.arrayBuffer()))};
                    }''', {'url': probe.path(role, '/documents/original'), 'headers': headers,
                           'body': probe.body(role, reference=reference)})
                    assert value['status'] == 200 and bytes(value['bytes']) == item['raw']
                    probe.save(phase + '-old-browser-reference-' + key,
                        {'reference': reference, 'views': [body for body, _, _ in plans(case)],
                         'raw_sha256': item['sha256'], 'transport': 'actual authenticated browser fetch, public read/original API',
                         'fresh_ui_hit_reference': hit['reference'], 'same_reference_required': False})
                browser.screenshot(key + '-verified')
            probe.save(phase + '-browser-' + role, {'events': browser.events, 'errors': browser.errors})
    probe.save(phase + '-protocol-references', refs)
    return refs

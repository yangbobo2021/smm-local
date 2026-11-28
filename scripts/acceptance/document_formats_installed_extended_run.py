"""Installed complex-content protocol replay with independent source oracles.

This is the content/reading portion of E1. Lifecycle, direct-index sync,
supervision and native service/X acceptance remain explicit separate checks.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from document_formats_installed_protocols import FormatProbe
from document_formats_installed_extended import Surface, fixtures, verify
from hub_documents_platform import now


def read_plans(probe, items, phase):
    for item in items:
        canonical = Surface(probe, item)
        hit = verify(canonical)
        if 'saved_reference' in item:
            assert hit['reference'] == item['saved_reference']
            canonical = Surface(probe, item, reference=item['saved_reference'])
            verify(canonical)
            assert canonical.reads == item['read_plan']
        else:
            item['saved_reference'] = hit['reference']
            item['read_plan'] = canonical.reads
        roles = [item['role']] + (['a'] if item['role'] == 'hub' else [])
        for role in roles:
            cli = Surface(probe, item, transport='cli', role=role)
            current = verify(cli)
            assert cli.reads == item['read_plan']
            key = 'cli_reference_' + role
            if key in item:
                assert current['reference'] == item[key]
            else:
                item[key] = current['reference']
            target = probe.out / (phase + '-' + role + '-' + item['label'] + '-original.' + item['format'])
            result = probe.cli(role, 'documents', 'read', '--reference', item[key], '--original-output', target)
            assert target.read_bytes() == item['raw'] and result['sha256'] == item['sha256']
    probe.save('extended-' + phase + '-canonical', {
        item['label']: {'origin': probe.expected_origin(item), 'reference': item['saved_reference'],
                        'plans': item['read_plan']} for item in items})


def mcp(probe, items, phase):
    searches = [('search_documents', {'query': item['query'], 'scope': 'project', 'limit': 50,
                **({'project_id': item['project']['id'], 'local': True} if item['role'] == 'a'
                   else {'hub_project_id': item['project']['id']})}) for item in items]
    found = asyncio.run(probe.mcp('a', searches))
    requests, expected = [], []
    for item, value in zip(items, found, strict=True):
        own = [h for h in value['results'] if h['origin'] == probe.expected_origin(item)]
        assert len(own) == 1
        Surface(probe, item).metadata(own[0])
        if 'mcp_reference' in item:
            assert own[0]['reference'] == item['mcp_reference']
        else:
            item['mcp_reference'] = own[0]['reference']
        for step in item['read_plan']:
            requests.append(('read_document', {'reference': item['mcp_reference'], **step['request']}))
            expected.append(step['response'])
    actual = asyncio.run(probe.mcp('a', requests))
    assert len(actual) == len(expected) and actual == expected
    for item in items:
        reference = item['mcp_reference']
        assert probe.raw_original('a', reference) == item['raw']
        target = probe.out / (phase + '-mcp-' + item['label'] + '-original.' + item['format'])
        result = probe.cli('a', 'documents', 'read', '--reference', reference, '--original-output', target)
        assert target.read_bytes() == item['raw'] and result['sha256'] == item['sha256']
    probe.save('extended-' + phase + '-mcp', {'documents': len(items), 'actual_stdio_calls': len(requests) + len(searches),
        'references': {i['label']: i['mcp_reference'] for i in items}})


def browser(probe, items, phase):
    for role in ('a', 'hub'):
        with probe.browser(role, 'extended-' + phase) as web:
            for item in (i for i in items if role == 'a' or i['role'] == role):
                result = web.search(item['project'], item['query'], remote=role == 'a' and item['role'] == 'hub')
                own = [h for h in result['results'] if h['origin'] == probe.expected_origin(item)]
                assert len(own) == 1
                Surface(probe, item).metadata(own[0])
                key = 'web_reference_' + role
                if key in item:
                    assert own[0]['reference'] == item[key]
                else:
                    item[key] = own[0]['reference']
                default = web.read()
                # The default text window is independently derived from the
                # current search hit, even if later full text needs chunks.
                assert (default['start'], default['end']) == (own[0]['start'], own[0]['end'])
                complete = ''.join(step['response']['text'] for step in item['read_plan']
                                   if set(step['request']) == {'start', 'end'})
                assert default['text'] == complete[default['start']:default['end']]
                for index, step in enumerate(item['read_plan']):
                    body, expected = step['request'], step['response']
                    if body.get('view') == 'table':
                        if 'row_start' in body:
                            web.page.locator('#' + web.prefix + '-table-select').select_option(body['table_id'])
                            actual = web.table_range((body['row_start'], body['row_end'] - 1,
                                                      body['column_start'], body['column_end'] - 1))
                        else:
                            actual = web.table(body['table_id'])
                    elif body.get('view') == 'original-info':
                        actual = web.info()
                    elif 'start' in body:
                        actual = web.text_range(body['start'], body['end'])
                    else:
                        actual = web.read()
                    assert actual == expected, (item['label'], role, index, body)
                web.screenshot(item['label'] + '-complete')
                web.download(web.page.locator('#' + web.prefix + '-original-download'), item)
            probe.save('extended-' + phase + '-web-' + role, {'events': web.events,
                'page_errors': web.errors, 'documents': [i['label'] for i in items if role == 'a' or i['role'] == role]})


def execute(config_path, output, smoke=False):
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    probe = FormatProbe(config, output)
    cwd = output / 'non-source-cwd'; cwd.mkdir(); os.chdir(cwd)
    bindings = probe.version_bindings()
    for name, expected in bindings.items():
        raw = (ROOT / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
        probe.keep('source-snapshot/' + name, raw)
    probe.save('extended-source-bindings', {'files': bindings, 'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest()})
    result = None
    try:
        probe.prepare_formats()
        if not smoke:
            probe.browser_uploads()
        items = fixtures(probe)
        from document_formats_protocol_guards import controls, events, assert_read_only
        if config.get('read_guards') and not smoke:
            controls(probe)
        probe.phase = 'read-only'
        start = len(events(probe)) if config.get('read_guards') else 0
        read_plans(probe, items, 'before-restart')
        if not smoke:
            mcp(probe, items, 'before-restart')
            browser(probe, items, 'before-restart')
            probe.complete_cli_http('before-restart')
            probe.local_hub_cli('before-restart')
            probe.mcp_formats('before-restart')
            probe.browser_formats('before-restart')
        if config.get('read_guards'):
            assert_read_only(probe, start)
        probe.phase = 'service-control'
        for role in ('a', 'hub'):
            probe.stop(role)
        for item in [*probe.items, *items]:
            item['path'].unlink()
        start = len(events(probe)) if config.get('read_guards') else 0
        for role in ('hub', 'a'):
            probe.start(role)
        probe.phase = 'read-only'
        read_plans(probe, items, 'after-restart-offline')
        if not smoke:
            mcp(probe, items, 'after-restart-offline')
            browser(probe, items, 'after-restart-offline')
            probe.complete_cli_http('after-restart-offline')
            probe.local_hub_cli('after-restart-offline')
            probe.mcp_formats('after-restart-offline')
            probe.browser_formats('after-restart-offline')
        if config.get('read_guards'):
            assert_read_only(probe, start)
        assert probe.version_bindings() == bindings
        result = {'status': 'passed', 'actual_actor': probe.actor(), 'core_documents': len(probe.items),
                  'extended_documents': len(items), 'smoke_only': smoke, 'finished_at': now(),
                  'not_covered': ['lifecycle and direct-index sync', 'native services', 'cross-OS transfer']}
    except BaseException:
        probe.save('failure', {'traceback': traceback.format_exc(), 'at': now()})
        raise
    finally:
        probe.cleanup()
    probe.save('result', result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    execute(args.target_config.resolve(), args.output.resolve(), args.smoke)


if __name__ == '__main__':
    main()

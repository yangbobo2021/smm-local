"""Actual installed-package offline-all E1 and split-message E3/E4 reads."""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from selective_upload_platform import Run


class ScopeProbe(Run):
    evidence_scope = 'actual offline-all E1 supplement and split-message scoped read; not full A/E acceptance'

    def checked_read(self, read, session, texts):
        assert read['source_session_id'] == session
        assert [m['text'] for m in read['messages']] == texts

    def browser_query(self, query, scope, expected, *, private_title=None):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            kwargs = {'headless': True}
            if self.t.get('browser'): kwargs['executable_path'] = self.t['browser']
            browser = p.chromium.launch(**kwargs); context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            context.tracing.start(screenshots=True, snapshots=True, sources=True); page = context.new_page()
            try:
                page.goto(self.web); page.locator('nav button[data-tab=search]').click()
                page.locator('#query').fill(query); page.locator('#archive-mode').select_option('combined')
                page.locator('#scope').select_option(scope); page.locator('#limit').select_option('20')
                if scope == 'project': page.locator('#search-project').select_option(str(self.projects['A']))
                with page.expect_response(lambda r: r.url.endswith('/api/search')) as answer: page.locator('#search-form button').click()
                result = answer.value.json(); assert {h['source_session_id'] for h in result['results']} == set(expected)
                reads = []
                for i, hit in enumerate(result['results']):
                    with page.expect_response(lambda r: r.url.endswith('/api/read')) as answer:
                        page.locator('#results .result').nth(i).get_by_role('button', name='读取命中及允许的上下文').click()
                    read = answer.value.json(); self.checked_read(read, hit['source_session_id'], expected[hit['source_session_id']])
                    if private_title:
                        assert private_title not in read['title']
                        assert private_title not in page.locator('#reader').inner_text()
                    reads.append(read)
                page.screenshot(path=str(self.output / (query + '-browser.png')), full_page=True)
                return {'search': result, 'reads': reads, 'browser_version': browser.version}
            finally:
                context.tracing.stop(path=str(self.output / (query + '-browser-trace.zip'))); browser.close()

    def offline_all(self):
        expected = {'local-' + n: ['selective common local-' + n + ' original'] for n in ['A', 'D', 'G', 'U', 'U2']}
        expected['plugin-history'] = ['selective common plugin-only original', 'selective common plugin-only appended']
        self.offline = True
        try:
            cli = self.cli(self.db, 'search', 'selective', '--scope', 'all', '--limit', '20')
            mcp = asyncio.run(self.mcp('search_conversations', {'query': 'selective', 'scope': 'all', 'limit': 20}))
            reads = {}
            for channel, result in [('cli', cli), ('mcp', mcp)]:
                assert {h['source_session_id'] for h in result['results']} == set(expected)
                assert result['archive_scope'] == 'local' and result['coverage']['hub'] == 'unavailable'
                assert result['fallback_reason']
                reads[channel] = []
                for hit in result['results']:
                    read = self.cli(self.db, 'read', '--reference', hit['reference']) if channel == 'cli' else asyncio.run(self.mcp('read_conversation', {'reference': hit['reference']}))
                    self.checked_read(read, hit['source_session_id'], expected[hit['source_session_id']]); reads[channel].append(read)
            web = self.browser_query('selective', 'all', expected)
            assert web['search']['archive_scope'] == 'local' and web['search']['coverage']['hub'] == 'unavailable'
            assert web['search']['fallback_reason']
            self.save('offline-all', {'expected_bodies': expected, 'cli': cli, 'mcp': mcp, 'reads': reads, 'browser': web})
        finally: self.offline = False

    def split_scope(self):
        device = 'e' * 32; outside = 'OUTSIDE_Y_ONLY_SECRET_TITLE'; allowed = 'boundaryneedle allowed X full original'
        self.api(self.t['address'], '/v1/upload-policy/register', {'hub_id': self.hub_id, 'device_id': device})
        head = self.api(self.t['address'], '/v1/upload-policy/status', {'hub_id': self.hub_id, 'device_id': device})
        self.api(self.t['address'], '/v1/upload-policy/set', {'hub_id': self.hub_id, 'device_id': device,
            'expected_revision': head['revision'], 'submission_id': uuid4().hex, 'policy': {'mode': 'all', 'projects': []}})
        self.api(self.t['address'], '/v1/project-metadata', {'hub_id': self.hub_id, 'device_id': device,
            'device_name': 'split-scope-fixture', 'projects': [{'id': 'x', 'name': 'scope-X'}, {'id': 'y', 'name': 'scope-Y'}], 'memberships': []})
        head = self.api(self.t['address'], '/v1/upload-policy/status', {'hub_id': self.hub_id, 'device_id': device})
        records = [{'source': 'codex', 'source_session_id': 'scope-shared', 'source_key': 'scope-' + key,
            'started_at': None, 'position': i, 'source_order': i, 'role': 'user', 'text': text,
            'timestamp': None, 'occurrence': None, 'project_id': key} for i, key, text in [(1, 'y', outside), (2, 'x', allowed)]]
        receipt = self.api(self.t['address'], '/v1/upload', {'hub_id': self.hub_id, 'device_id': device,
            'device_name': 'split-scope-fixture', 'control_epoch': head['control_epoch'], 'policy_revision': head['revision'],
            'batch_id': uuid4().hex, 'records': records}); assert receipt['accepted'] == 2
        projects = self.admin('project', 'list'); x = next(p['id'] for p in projects if p['name'] == 'scope-X')
        local_device = self.cli(self.db, 'upload', 'status')['device_id']
        a = next(p['id'] for p in projects if p['name'] == 'A' and p['owner'] == local_device)
        self.admin('project', 'link', str(a), str(x))
        cli = self.cli(self.db, 'search', 'boundaryneedle', '--scope', 'project', '--project-id', str(self.projects['A']), '--limit', '20')
        mcp = asyncio.run(self.mcp('search_conversations', {'query': 'boundaryneedle', 'scope': 'project', 'project_id': self.projects['A'], 'limit': 20}))
        reads = {}
        for channel, result in [('cli', cli), ('mcp', mcp)]:
            assert len(result['results']) == 1; hit = result['results'][0]; assert hit['title'] == allowed
            read = self.cli(self.db, 'read', '--reference', hit['reference'], '--start', '0', '--end', '999999') if channel == 'cli' else asyncio.run(self.mcp('read_conversation', {'reference': hit['reference'], 'start': 0, 'end': 999999}))
            self.checked_read(read, 'scope-shared', [allowed]); assert read['title'] == allowed
            assert {p['id'] for p in read['projects']} == {x}; reads[channel] = read
        hit = cli['results'][0]
        direct = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': hit['reference'], 'start': 0, 'end': 999999})
        self.checked_read(direct, 'scope-shared', [allowed]); assert direct['title'] == allowed
        legacy = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'conversation_id': hit['id']})
        assert legacy['title'] == outside and [m['text'] for m in legacy['messages']] == [outside, allowed]
        web = None if self.protocol_only else self.browser_query('boundaryneedle', 'project', {'scope-shared': [allowed]}, private_title=outside)
        self.stop_hub(); self.start_hub()
        restarted = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': hit['reference']})
        self.checked_read(restarted, 'scope-shared', [allowed]); assert restarted['title'] == allowed
        self.save('split-scope', {'fixture': records, 'receipt': receipt, 'allowed_project_id': x, 'cli': cli, 'mcp': mcp,
            'reads': reads, 'direct': direct, 'legacy_unscoped': legacy, 'browser': web, 'after_hub_restart': restarted})

    def lifecycle(self):
        if not self.protocol_only: self.offline_all()
        self.split_scope()


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['client', 'self-managed', 'hub-service'])
    p.add_argument('--target-config', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    ScopeProbe(p.parse_args()).run()


if __name__ == '__main__': main()

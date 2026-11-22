"""Installed-package A5 isolation probe against an independent real HTTPS Hub."""
import argparse
import asyncio
import json
from pathlib import Path

from selective_upload_fixture import history
from selective_upload_platform import Run


class Isolation(Run):
    evidence_scope = 'A5 actual HTTPS Hub isolation only; not E1 three-entrance or full A/E acceptance'

    def lifecycle(self):
        self.cli(self.db, 'upload', 'set', '--mode', 'only', '--project-id', str(self.projects['A']))
        self.sync_done(self.db, wait_for_upload=True)
        old = next(h for h in self.hub_hits() if h['source_session_id'] == 'local-A')['reference']
        ids = {p['name']: p['id'] for p in self.admin('project', 'list')}
        self.admin('project', 'link', str(ids['A']), str(ids['D']))
        self.save('isolation-links', self.admin('project', 'links'))
        self.cli(self.db, 'upload', 'set', '--mode', 'only', '--project-id', str(self.projects['D']))
        stopped = self.cli(self.db, 'upload', 'status'); assert stopped['state'] == 'confirmed'
        marker = len(self.requests)
        history(self.root / 'local', 'local-A', 'A', ['selective common local-A original', 'selective forbidden A isolation append'])
        history(self.root / 'local', 'local-A-private', 'A', ['selective forbidden A isolation new'])
        history(self.root / 'local', 'local-D', 'D', ['selective common local-D original', 'selective allowed D isolation append'])
        history(self.root / 'remote', 'remote-B', 'B', ['selective common remote-B original', 'selective allowed other device append'])
        self.sync_done(self.db, wait_for_upload=True); self.sync_done(self.remote_db, wait_for_upload=True)
        # Source is synthetic; run the installed VibeInsightSync, with no source server.
        code = '''import json,sys
from pathlib import Path
from smm_hub._archive import Archive
from smm_hub.vibeinsight import VibeInsightSync
class Source:
 def validate(self): pass
 def projects(self,through=None): return ['synthetic.example/005/V']
 def upper(self): return ('2026-11-01T00:00:01','v-event-2')
 def page(self,project,after,through,limit):
  rows=[{'id':'v-event-'+str(i),'created_at':'2026-11-01T00:00:0'+str(i-1),'event_timestamp':'2026-11-01T00:00:0'+str(i-1),'user_id':'synthetic-owner','platform_code':'codex','session_id':'vibe-V','trace_id':'v-trace-'+str(i),'event_type':'trace.started','message':text,'project':project} for i,text in [(1,'selective common VibeInsight original'),(2,'selective allowed VibeInsight append')]]
  return [r for r in rows if after is None or (r['created_at'],r['id'])>tuple(after)][:limit]
d=Archive(Path(sys.argv[1])); print(json.dumps(VibeInsightSync(d,'synthetic-005-source').run(Source())))
'''
        vibe = json.loads(self.command([self.t['hub_python'], '-I', '-X', 'utf8', '-c', code, self.state / 'smm-hub.sqlite3']).stdout)
        hits = {h['source_session_id']: h for h in self.hub_hits()}
        expected = {'local-A': ['selective common local-A original'],
            'local-D': ['selective common local-D original', 'selective allowed D isolation append'],
            'remote-B': ['selective common remote-B original', 'selective allowed other device append'],
            'remote-C': ['selective common remote-C original'],
            'vibe-V': ['selective common VibeInsight original', 'selective allowed VibeInsight append']}
        assert set(hits) == set(expected), set(hits)
        reads = {}
        for session, texts in expected.items():
            read = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': hits[session]['reference']})
            assert [m['text'] for m in read['messages']] == texts, (session, read)
            reads[session] = read
        retained = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': old})
        assert [m['text'] for m in retained['messages']] == expected['local-A']
        sent = self.requests[marker:]
        assert 'selective forbidden A isolation' not in json.dumps(sent)
        local = self.cli(self.db, 'search', 'isolation', '--local', '--limit', '50')
        assert {'local-A', 'local-A-private', 'local-D'} <= {h['source_session_id'] for h in local['results']}
        state = self.cli(self.db, 'upload', 'status')
        assert state['state'] == 'confirmed' and state['allowed_pending_messages'] == state['inflight_messages'] == 0
        self.save('isolation-result', {'scope': 'A5 only; fixture D is the related permitted project B',
            'stopped': stopped, 'expected_bodies': expected, 'hub_search': hits, 'reads': reads,
            'old_reference_read': retained, 'local_search': local, 'vibe_sync': vibe, 'requests_after_stop': sent, 'final_state': state})
        if self.t.get('extra_entrances'): self.extra_interfaces(expected)

    def extra_interfaces(self, hub_bodies):
        expected = {**hub_bodies, 'local-A': ['selective common local-A original', 'selective forbidden A isolation append'],
            'local-A-private': ['selective forbidden A isolation new'],
            **{'local-' + n: ['selective common local-' + n + ' original'] for n in ['G', 'U', 'U2']},
            'plugin-history': ['selective common plugin-only original', 'selective common plugin-only appended']}
        local_names = {'local-A', 'local-A-private', 'local-D', 'local-G', 'local-U', 'local-U2', 'plugin-history'}
        cases = [('local-project', True, 'project', {'local-A', 'local-A-private', 'local-D'}),
                 ('local-all', True, 'all', local_names), ('combined-all', False, 'all', set(expected))]
        def check(result, names):
            assert {h['source_session_id'] for h in result['results']} == names
        def check_read(read, session):
            assert read['source_session_id'] == session
            assert [m['text'] for m in read['messages']] == expected[session]
        for stage, local, scope, names in cases:
            marker = len(self.requests)
            options = {'query': 'selective', 'local': local, 'scope': scope, 'limit': 20}
            args = ['search', 'selective', '--scope', scope, '--limit', '20']
            if local: args += ['--local']
            if scope == 'project':
                args += ['--project-id', str(self.projects['A'])]; options['project_id'] = self.projects['A']
            cli = self.cli(self.db, *args); check(cli, names)
            mcp = asyncio.run(self.mcp('search_conversations', options)); check(mcp, names)
            reads = {}
            for channel, result in [('cli', cli), ('mcp', mcp)]:
                reads[channel] = []
                for hit in result['results']:
                    read = self.cli(self.db, 'read', '--reference', hit['reference']) if channel == 'cli' else asyncio.run(self.mcp('read_conversation', {'reference': hit['reference']}))
                    check_read(read, hit['source_session_id']); reads[channel].append(read)
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                kwargs = {'headless': True}
                if self.t.get('browser'): kwargs['executable_path'] = self.t['browser']
                browser = p.chromium.launch(**kwargs); context = browser.new_context(viewport={'width': 1440, 'height': 1100})
                context.tracing.start(screenshots=True, snapshots=True, sources=True); page = context.new_page()
                try:
                    page.goto(self.web); page.locator('nav button[data-tab=search]').click()
                    page.locator('#archive-mode').select_option('local' if local else 'combined')
                    page.locator('#query').fill('selective'); page.locator('#scope').select_option(scope)
                    if scope == 'project': page.locator('#search-project').select_option(str(self.projects['A']))
                    page.locator('#limit').select_option('20')
                    with page.expect_response(lambda r: r.url.endswith('/api/search')) as answer: page.locator('#search-form button').click()
                    web = answer.value.json(); check(web, names); web_reads = []
                    for i, hit in enumerate(web['results']):
                        with page.expect_response(lambda r: r.url.endswith('/api/read')) as answer:
                            page.locator('#results .result').nth(i).get_by_role('button', name='读取命中及允许的上下文').click()
                        read = answer.value.json(); check_read(read, hit['source_session_id']); web_reads.append(read)
                    page.screenshot(path=str(self.output / (stage + '.png')), full_page=True)
                finally:
                    context.tracing.stop(path=str(self.output / (stage + '-browser-trace.zip'))); browser.close()
            requests = self.requests[marker:]
            if local: assert not any(r['route'] in ('/v1/search', '/v1/read', '/v1/query-scope') for r in requests)
            self.save(stage, {'expected_sessions': sorted(names), 'expected_bodies': expected, 'cli': cli, 'mcp': mcp,
                'reads': reads, 'browser': web, 'browser_reads': web_reads, 'requests': requests})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target-config', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); args.mode = 'client'; Isolation(args).run()


if __name__ == '__main__': main()

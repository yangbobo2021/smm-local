"""Opt-in 005 installed-wheel CLI, real stdio MCP, browser and service probe.

No VibeInsight server or PostgreSQL is contacted. TLS audit relay sees synthetic
requests only. Each output directory is exclusive; a failed run never passes.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import platform
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler

HERE = Path(__file__).resolve().parent


def now(): return datetime.now(timezone.utc).isoformat()


def eventually(check, seconds=45):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        try:
            if value := check(): return value
        except (OSError, ValueError): pass
        time.sleep(.2)
    raise AssertionError('acceptance condition timed out')


class Run:
    def __init__(self, args):
        self.args = args; self.t = json.loads(args.target_config.read_text(encoding='utf-8-sig'))
        self.root = Path(self.t['work']).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        self.output = args.output.resolve(); self.output.mkdir(parents=True, exist_ok=False)
        self.state = self.root / self.t.get('state_name', 'hub-state')
        self.env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'VIRTUAL_ENV', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID', 'CLAUDE_SESSION_ID'}}
        self.env.update(PYTHONUTF8='1', PYTHONIOENCODING='utf-8', SSL_CERT_FILE=self.t['cert'], SMM_SERVICE_PORT='0')
        self.token = 'synthetic-005-' + os.urandom(24).hex()
        self.commands = []; self.requests = []; self.process = None; self.browser = None
        self.protocol_only = bool(self.t.get('protocol_only'))
        if self.protocol_only and args.mode != 'hub-service': raise ValueError('protocol_only is restricted to E3 Hub service probes, not E1 client acceptance')
        self.clients = []; self.login_label = None; self.relay = None; self.offline = False; self.started = now(); self.identities = []
        self.opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context(cafile=self.t['cert'])))
        for source in HERE.glob('selective_upload_*.py'):
            (self.output / source.name).write_bytes(source.read_bytes())

    def redact(self, value):
        encoded = json.dumps(value, ensure_ascii=False, default=str).replace(self.token, '<synthetic-token>')
        for original, label in sorted([(str(self.root), '<task>'), (str(Path.home()), '<home>'),
                                       (str(self.args.target_config), '<target-config>')], key=lambda p: -len(p[0])):
            encoded = encoded.replace(json.dumps(original)[1:-1], label)
        return json.loads(encoded)

    def save(self, name, value):
        (self.output / (name + '.json')).write_text(json.dumps(self.redact(value), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def command(self, argv, expected=0, timeout=60):
        p = subprocess.run(list(map(str, argv)), env=self.env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        self.commands.append(self.redact({'at': now(), 'argv': argv, 'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}))
        (self.output / 'commands.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in self.commands), encoding='utf-8')
        assert self.token not in p.stdout + p.stderr, 'token appeared in command output'
        if expected is not None: assert p.returncode == expected, self.commands[-1]
        return p

    def cli(self, db, *args, expected=0):
        p = self.command([self.t['local_python'], '-I', '-m', 'smm_local.cli', '--db', db, *args], expected=expected)
        return json.loads(p.stdout) if p.returncode == 0 else p.stderr

    def admin(self, *args):
        return json.loads(self.command([self.t['hub_python'], '-I', '-m', 'smm_hub.cli', 'hub', '--state-dir', self.state, *args], timeout=90).stdout)

    def api(self, address, route, payload=None, *, method=None, local=False):
        headers = {'Content-Type': 'application/json'}
        if local: headers.update(Origin=address, **{'X-SMM-UI': '1'})
        else: headers['Authorization'] = 'Bearer ' + self.token
        req = Request(address + route, data=json.dumps(payload).encode() if payload is not None else None,
                      headers=headers, method=method)
        with self.opener.open(req, timeout=10) as response: return json.load(response)

    def installed(self):
        candidate = self.t['candidate']; assert candidate['dirty'] is False
        tooling = self.t.get('browser_tooling')
        tooling_identity = None
        if tooling:
            directory = Path(tooling['directory'])
            manifest = json.loads(Path(tooling['manifest']).read_text())
            actual = {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in manifest['files']}
            assert actual == manifest['files'], 'portable browser tooling differs from its source manifest'
            sys.path.insert(0, str(directory))
            os.environ['PLAYWRIGHT_NODEJS_PATH'] = tooling['node']
            self.env['PLAYWRIGHT_NODEJS_PATH'] = tooling['node']
            tooling_identity = {'source': manifest['source'], 'files': actual,
                                'node_sha256': hashlib.sha256(Path(tooling['node']).read_bytes()).hexdigest(),
                                'node_version': self.command([tooling['node'], '--version']).stdout.strip()}
        observed = {}
        for package, interpreter in [('local', self.t['local_python']), ('hub', self.t['hub_python'])]:
            expected = candidate['installed_' + package]
            code = "import importlib.util,pathlib,hashlib,json,sys,platform; r=pathlib.Path(importlib.util.find_spec('smm_' + sys.argv[1]).origin).parent.parent; print(json.dumps({'files':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in json.loads(sys.argv[2])},'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'other_package':importlib.util.find_spec('smm_hub' if sys.argv[1]=='local' else 'smm_local') is not None}))"
            value = json.loads(self.command([interpreter, '-I', '-c', code, package, json.dumps(list(expected))]).stdout)
            assert value['files'] == expected, 'installed module differs from wheel'
            assert not value['other_package'], 'independent package environment contains the other SMM package'
            observed[package] = value
        self.save('manifest', {'candidate': candidate, 'installed': observed, 'started_at': self.started,
                               'platform': platform.platform(), 'identity': self.identity(), 'mode': self.args.mode,
                               'browser_tooling': tooling_identity})

    def identity(self):
        if os.name == 'nt':
            import ctypes
            elevated = bool(ctypes.windll.shell32.IsUserAnAdmin())
            if self.args.mode == 'client': assert not elevated, 'client probe requires ordinary interactive user'
            return {'elevated_admin': elevated, 'user': os.environ.get('USERNAME')}
        assert os.getuid() != 0
        return {'uid': os.getuid(), 'user': os.environ.get('USER')}

    def start_hub(self):
        if self.args.mode == 'hub-service':
            self.admin('enable')
        else:
            log = (self.output / 'hub.log').open('a', encoding='utf-8')
            self.process = subprocess.Popen([self.t['hub_python'], '-I', '-m', 'smm_hub.cli', 'serve-hub', '--state-dir', str(self.state),
                '--host', '127.0.0.1', '--port', str(self.t['port']), '--token-file', str(self.root / 'input-token'),
                '--tls-cert', self.t['cert'], '--tls-key', self.t['key']], env=self.env, stdout=log, stderr=log)
            log.close()
        eventually(lambda: self.api(self.t['address'], '/v1/info'))
        self.identities.append(self.hub_identity()); self.save('service-events', self.identities)

    def stop_hub(self):
        if self.args.mode == 'hub-service': self.admin('disable')
        elif self.process and self.process.poll() is None:
            self.process.terminate(); self.process.wait(timeout=20)
            self.identities.append({'event': 'process-exit', 'pid': self.process.pid, 'exit_code': self.process.returncode, 'at': now()})
            assert self.process.returncode in (0, -15)
            self.save('service-events', self.identities)

    def hub_identity(self):
        if self.args.mode != 'hub-service': return {'event': 'start', 'mode': 'serve-hub', 'pid': self.process.pid, 'at': now()}
        suffix = hashlib.sha256(str(self.state).encode()).hexdigest()[:12]
        if sys.platform == 'linux':
            name = 'smm-hub-' + suffix + '.service'
            value = self.command(['systemctl', '--user', 'show', name, '-p', 'MainPID', '-p', 'ActiveState', '-p', 'ExecStart']).stdout
            pid = int(next(s.split('=', 1)[1] for s in value.splitlines() if s.startswith('MainPID=')))
            assert pid > 0 and os.stat(f'/proc/{pid}').st_uid == os.getuid()
            return {'mode': 'systemd-user', 'definition': self.command(['systemctl', '--user', 'cat', name]).stdout, 'pid': pid, 'state': value, 'at': now()}
        if sys.platform == 'darwin':
            import plistlib, pwd, re
            label = 'ai.smm.hub.' + suffix
            definition = plistlib.loads((Path('/Library/LaunchDaemons') / (label + '.plist')).read_bytes())
            assert definition['UserName'] == pwd.getpwuid(os.getuid()).pw_name
            value = self.command(['sudo', '-n', 'launchctl', 'print', 'system/' + label]).stdout
            pid = int(re.search(r'\bpid = (\d+)', value)[1]); assert pid > 0
            return {'mode': 'system-launchd', 'definition': definition, 'pid': pid, 'at': now(), 'process': self.command(['ps', '-o', 'uid,pid,ppid,command', '-p', str(pid)]).stdout}
        name = 'smm-hub-' + suffix
        value = self.command(['powershell', '-NoProfile', '-Command', f"$s=Get-CimInstance Win32_Service -Filter \"Name='{name}'\"; $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$s.ProcessId); @{{service=$s|Select-Object Name,StartName,State,ProcessId;owner=Invoke-CimMethod -InputObject $p -MethodName GetOwner}}|ConvertTo-Json -Depth 5"]).stdout
        parsed = json.loads(value); assert parsed['service']['StartName'].lower() == r'nt authority\localservice'
        assert parsed['service']['State'] == 'Running'; assert parsed['owner']['User'].lower().replace(' ', '') == 'localservice'
        return {'mode': 'LocalService', **parsed, 'pid': parsed['service']['ProcessId'], 'at': now()}

    def setup(self):
        assert not self.state.exists(), 'new task state is required'
        if self.args.mode != 'hub-service':
            self.command([self.t['hub_python'], '-I', HERE / 'selective_upload_fixture.py', 'seed-vibe', '--root', self.state])
        (self.root / 'input-token').write_text(self.token, encoding='ascii')
        if self.args.mode == 'hub-service':
            # setup creates the service credential; read it privately after setup.
            result = self.admin('setup', '--address', self.t['address'], '--bind', '127.0.0.1', '--port', str(self.t['port']),
                '--tls-cert', self.t['cert'], '--tls-key', self.t['key'], '--ca-file', self.t['cert'])
            self.token = (self.state / 'hub-token').read_text().strip()
            (self.root / 'input-token').write_text(self.token, encoding='ascii')
            self.identities.append(self.hub_identity()); self.save('setup', result)
            self.command([self.t['hub_python'], '-I', HERE / 'selective_upload_fixture.py', 'seed-vibe', '--root', self.state])
        else: self.start_hub()
        self.hub_id = self.api(self.t['address'], '/v1/info')['hub_id']
        self.make_relay()
        for name in ('local', 'remote'):
            directory = self.root / name
            result = json.loads(self.command([self.t['local_python'], '-I', HERE / 'selective_upload_fixture.py', 'prepare', '--root', directory, '--device', name]).stdout)
            db = directory / 'archive.sqlite3'; self.clients.append(db)
            self.save('fixture-' + name, result)
            if name == 'local': self.unassigned = next(h for h in result['search']['results'] if h['source_session_id'] == 'local-U')
            self.cli(db, 'configure-hub', self.relay_address, '005-' + name, '--token-file', self.root / 'input-token')
            if name == 'local' and self.args.mode == 'login-service': self.install_login(db)
        self.db, self.remote_db = self.clients
        self.projects = {p['name']: p['id'] for p in self.cli(self.db, 'projects')}
        self.cli(self.remote_db, 'upload', 'set', '--mode', 'all'); self.cli(self.remote_db, 'maintenance', 'sync')
        endpoint = json.loads((Path(str(self.db) + '.service.json')).read_text()); self.web = endpoint['url']
        self.save('local-service', {'url': self.web, 'on_demand': endpoint['on_demand'], 'identity': self.identity()})
        self.cli(self.db, 'maintenance', 'sync')
        assert not any(h['source_session_id'].startswith('local-') for h in self.hub_hits())
        initial = self.cli(self.db, 'upload', 'status'); assert initial['state'] == 'needs_selection'
        self.save('new-connection-status', initial)
        # Associate unuploaded A with B and V, B with C, and A with local-only D only locally.
        projects = self.admin('project', 'list'); ids = {p['name']: p['id'] for p in projects}
        for other in ('B', 'synthetic.example/005/V'): self.admin('project', 'link', str(ids['A']), str(ids[other]))
        self.admin('project', 'link', str(ids['B']), str(ids['C']))
        self.save('hub-projects', self.admin('project', 'list')); self.save('hub-links', self.admin('project', 'links'))

    def make_relay(self):
        run = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self): self.forward()
            def do_POST(self): self.forward()
            def forward(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                payload = json.loads(raw) if raw else None
                run.requests.append({'at': now(), 'route': self.path, 'payload': payload, 'offline': run.offline})
                if run.offline: self.send_response(503); self.end_headers(); return
                req = Request(run.t['address'] + self.path, data=raw if raw else None,
                              headers={'Content-Type': 'application/json', 'Authorization': self.headers.get('Authorization', '')}, method=self.command)
                try:
                    with run.opener.open(req, timeout=10) as response: code, body = response.status, response.read()
                except HTTPError as exc: code, body = exc.code, exc.read()
                except OSError: code, body = 503, b'{}'
                self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        self.relay = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(self.t['cert'], self.t['key'])
        self.relay.socket = context.wrap_socket(self.relay.socket, server_side=True)
        threading.Thread(target=self.relay.serve_forever, daemon=True).start()
        self.relay_address = f'https://localhost:{self.relay.server_port}'

    def hub_hits(self): return self.api(self.t['address'], '/v1/search', {'query': 'selective', 'limit': 50, 'preview_chars': 0})['results']

    def policy_and_stop(self):
        before = self.cli(self.db, 'upload', 'status'); self.save('initial-choice', before)
        for mode, selected in [('only', []), ('none', []), ('only', [self.projects['A']])]:
            args = ['upload', 'set', '--mode', mode]
            for project in selected: args += ['--project-id', str(project)]
            value = self.cli(self.db, *args); assert value['state'] == 'confirmed'; self.save('choice-' + mode + '-' + str(len(selected)), value)
        self.cli(self.db, 'maintenance', 'sync')
        old = next(h for h in self.hub_hits() if h['source_session_id'] == 'local-A')
        self.old_reference = old['reference']; self.save('old-original', self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': self.old_reference}))
        self.old_batch = next(r['payload'] for r in self.requests if r['route'] == '/v1/upload' and r['payload'].get('records') and r['payload']['device_name'] == '005-local')
        self.cli(self.db, 'upload', 'set', '--mode', 'none')
        stop = self.cli(self.db, 'upload', 'status'); assert stop['state'] == 'confirmed'
        self.stop_index = len(self.requests)
        self.command([self.t['local_python'], '-I', HERE / 'selective_upload_fixture.py', 'append', '--root', self.root / 'local'])
        self.cli(self.db, 'maintenance', 'sync')
        assert not any('appended while stopped' in m['text'] or 'new while stopped' in m['text'] for h in self.hub_hits() for m in h['matched_messages'])
        self.reject_old_requests('initial-stop')
        self.save('stopped-state', stop)

    def reject_old_requests(self, label):
        before = self.hub_hits()
        observations = []
        for versioned in (True, False):
            batch = dict(self.old_batch)
            if not versioned:
                for key in ('policy_revision', 'control_epoch', 'batch_id'): batch.pop(key, None)
            try: self.api(self.t['address'], '/v1/upload', batch)
            except HTTPError as exc:
                assert exc.code in (403, 409)
                observations.append({'versioned': versioned, 'status': exc.code, 'response': exc.read().decode('utf-8')})
            else: raise AssertionError('stale/legacy body accepted after confirmed stop')
        after = self.hub_hits(); assert before == after
        self.save(label + '-replay', {'attempts': observations, 'before': before, 'after': after})

    async def mcp(self, tool, arguments):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        params = StdioServerParameters(command=self.t['local_python'], args=['-I', '-m', 'smm_local.mcp_server', '--db', str(self.db)], env=self.env)
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize(); response = await session.call_tool(tool, arguments)
                assert not response.isError, response
                return json.loads(response.content[0].text)

    def assert_scope(self, result, expected):
        assert {h['source_session_id'] for h in result['results']} == set(expected), result

    def interfaces(self, stage, expected):
        args = ['search', 'selective', '--scope', 'project', '--project-id', str(self.projects['A']), '--limit', '20']
        cli = self.cli(self.db, *args); self.assert_scope(cli, expected); self.save(stage + '-cli-search', cli)
        mcp = asyncio.run(self.mcp('search_conversations', {'query': 'selective', 'scope': 'project', 'project_id': self.projects['A'], 'limit': 20}))
        self.assert_scope(mcp, expected); self.save(stage + '-mcp-search', mcp)
        for name, result in [('cli', cli), ('mcp', mcp)]:
            reads = []
            for hit in result['results']:
                read = (self.cli(self.db, 'read', '--reference', hit['reference']) if name == 'cli'
                        else asyncio.run(self.mcp('read_conversation', {'reference': hit['reference']})))
                assert read['source_session_id'] == hit['source_session_id']
                texts = [m['text'] for m in read['messages']]
                expected_texts = {'local-A': ['selective common local-A original', 'selective common local-A appended while stopped'],
                    'local-A-new': ['selective common local-A new while stopped'], 'remote-B': ['selective common remote-B original'],
                    'vibe-V': ['selective common VibeInsight original']}
                assert texts == expected_texts[hit['source_session_id']], texts
                reads.append(read)
            self.save(stage + '-' + name + '-reads', reads)
        if not self.protocol_only: self.browser_scope(stage, expected)
        return cli

    def browser_scope(self, stage, expected):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            kwargs = {'headless': True}
            if self.t.get('browser'): kwargs['executable_path'] = self.t['browser']
            browser = p.chromium.launch(**kwargs)
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page(); errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
            responses = []
            page.on('response', lambda r: responses.append({'url': r.url, 'status': r.status, 'json': r.json()}) if r.url.endswith('/api/search') or r.url.endswith('/api/read') else None)
            try:
                page.goto(self.web); page.locator('nav button[data-tab=settings]').click()
                page.locator('#upload-state').wait_for(); page.screenshot(path=str(self.output / (stage + '-upload.png')), full_page=True)
                page.locator('nav button[data-tab=search]').click(); page.locator('#query').fill('selective')
                page.locator('#scope').select_option('project'); page.locator('#search-project').select_option(str(self.projects['A']))
                page.locator('#limit').select_option('20')
                with page.expect_response(lambda r: r.url.endswith('/api/search')) as answer: page.locator('#search-form button').click()
                response = answer.value.json(); self.assert_scope(response, expected)
                page.locator('#results .result').first.wait_for(); page.screenshot(path=str(self.output / (stage + '-search.png')), full_page=True)
                reads = []
                for i, hit in enumerate(response['results']):
                    with page.expect_response(lambda r: r.url.endswith('/api/read')) as answer:
                        page.locator('#results .result').nth(i).get_by_role('button', name='读取命中及允许的上下文').click()
                    read = answer.value.json(); assert read['source_session_id'] == hit['source_session_id']; reads.append(read)
                    page.locator('#reader-card').wait_for(); page.screenshot(path=str(self.output / (stage + '-read-' + str(i) + '.png')), full_page=True)
                assert not errors, errors
                self.save(stage + '-browser', {'version': browser.version, 'search': response, 'reads': reads, 'responses': responses, 'page_errors': errors})
            finally:
                context.tracing.stop(path=str(self.output / (stage + '-browser-trace.zip'))); browser.close()

    def restart_local(self):
        if self.login_label:
            descriptor = Path(str(self.db) + '.service.json')
            previous_stamp = descriptor.stat().st_mtime_ns
            self.login_action('stop')
            self.login_action('start')
            def ready():
                path = Path(str(self.db) + '.service.json')
                if not path.exists() or path.stat().st_mtime_ns == previous_stamp: return False
                endpoint = json.loads(path.read_text())
                return endpoint if self.api(endpoint['url'], '/api/status', local=True) else False
            eventually(ready)
        else:
            self.cli(self.db, 'stop-on-demand')
            self.cli(self.db, 'maintenance', 'status')
        self.web = json.loads(Path(str(self.db) + '.service.json').read_text())['url']
        state = self.cli(self.db, 'upload', 'status'); assert state['policy']['mode'] == 'none'
        self.save('local-restart', state)

    def browser_configuration(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            kwargs = {'headless': True}
            if self.t.get('browser'): kwargs['executable_path'] = self.t['browser']
            browser = p.chromium.launch(**kwargs)
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page(); changes = []
            try:
                page.goto(self.web); page.locator('nav button[data-tab=settings]').click()
                page.wait_for_function("document.querySelector('#upload-state').textContent.includes('待选择')")
                for mode, selected in [('only', []), ('only', ['A']), ('except', ['A']), ('all', []), ('none', []), ('only', [])]:
                    page.locator('#upload-mode').select_option(mode)
                    if mode in ('only', 'except'):
                        for checkbox in page.locator('.upload-project-check').all(): checkbox.uncheck()
                        for name in selected: page.locator('.upload-project-check[value="' + str(self.projects[name]) + '"]').check()
                    with page.expect_response(lambda r: r.url.endswith('/api/upload') and r.request.method == 'PUT') as response, page.expect_response(lambda r: r.url.endswith('/api/upload') and r.request.method == 'GET'):
                        page.locator('#upload-save').click()
                    saved = response.value.json(); observed = self.cli(self.db, 'upload', 'status')
                    assert saved['state'] == observed['state'] == 'confirmed'
                    assert saved['policy'] == observed['policy'] and saved['policy']['mode'] == mode
                    page.screenshot(path=str(self.output / ('config-' + str(len(changes)) + '-' + mode + '.png')), full_page=True)
                    changes.append({'web': saved, 'cli': observed})
                page.locator('nav button[data-tab=projects]').click()
                with page.expect_response(lambda r: r.url.endswith('/api/projects/global')) as response: page.locator('#ensure-global').click()
                global_project = response.value.json()
                page.locator('#assign-conversation').fill(str(self.unassigned['id']))
                page.locator('#assign-project').select_option(str(global_project['id']))
                with page.expect_response(lambda r: r.url.endswith('/api/projects/assign')) as response: page.locator('#assign-save').click()
                preview = response.value.json(); assert not preview['applied']
                assert preview['affected_conversations'] == [self.unassigned['id']]
                page.locator('#project-change-preview').wait_for(); page.screenshot(path=str(self.output / 'assignment-preview.png'), full_page=True)
                with page.expect_response(lambda r: r.url.endswith('/api/projects/assign')) as response: page.locator('#project-change-confirm').click()
                applied = response.value.json(); assert applied['applied']
                self.cli(self.db, 'maintenance', 'sync')
                assigned = self.cli(self.db, 'read', str(self.unassigned['id']))
                assert assigned['project_id'] == global_project['id']
                self.save('browser-configuration', {'changes': changes, 'global': global_project, 'preview': preview, 'applied': applied, 'read_after_reimport': assigned})
            finally:
                context.tracing.stop(path=str(self.output / 'configuration-browser-trace.zip')); browser.close()

    def install_login(self, db):
        assert sys.platform == 'darwin'
        self.cli(db, 'stop-on-demand')
        self.login_label = 'ai.smm.local.acceptance.' + hashlib.sha256(str(self.root).encode()).hexdigest()[:12]
        wrapper = self.root / 'login-candidate'
        wrapper.write_text('#!' + self.t['local_python'] + '\nimport os,sys\nos.environ["SSL_CERT_FILE"]=' + repr(self.t['cert']) + '\nos.execv(sys.executable,[sys.executable,"-I","-m","smm_local.cli",*sys.argv[1:],"--port","0"])\n', encoding='utf-8')
        wrapper.chmod(0o700)
        code = "from pathlib import Path; import sys; from smm_local.login_service import install; install(Path(sys.argv[1]),Path(sys.argv[2]),label=sys.argv[3],logs=Path(sys.argv[4]))"
        self.command([self.t['local_python'], '-I', '-c', code, wrapper, db, self.login_label, self.root / 'login-logs'])
        eventually(lambda: Path(str(db) + '.service.json').exists())
        self.login_action('inspect')

    def login_action(self, action):
        import plistlib, re
        plist = Path.home() / 'Library/LaunchAgents' / (self.login_label + '.plist')
        domain = 'gui/' + str(os.getuid())
        if action == 'stop': self.command(['launchctl', 'bootout', domain, plist]); return
        if action == 'start': self.command(['launchctl', 'bootstrap', domain, plist])
        text = self.command(['launchctl', 'print', domain + '/' + self.login_label]).stdout
        pid = int(re.search(r'\bpid = (\d+)', text)[1]); assert pid > 0
        self.save('login-service-' + str(len(self.commands)), {'label': self.login_label, 'pid': pid,
            'definition': plistlib.loads(plist.read_bytes()), 'process': self.command(['ps', '-o', 'uid,pid,ppid,command', '-p', str(pid)]).stdout})

    def lifecycle(self):
        if not self.protocol_only: self.browser_configuration()
        self.policy_and_stop()
        expected = ['local-A', 'local-A-new', 'remote-B', 'vibe-V']
        self.interfaces('combined-stopped', expected)
        local = self.cli(self.db, 'search', 'selective', '--local', '--scope', 'project', '--project-id', str(self.projects['A']), '--limit', '20')
        self.assert_scope(local, ['local-A', 'local-A-new', 'local-D']); self.save('explicit-local', local)
        all_local = self.cli(self.db, 'search', 'selective', '--local', '--limit', '50')
        assert {'local-G', 'local-U', 'plugin-history'} <= {h['source_session_id'] for h in all_local['results']}
        self.save('all-local', all_local)
        self.offline = True
        self.interfaces('offline', ['local-A', 'local-A-new'])
        self.offline = False
        self.interfaces('reconnected', expected)
        self.restart_local(); self.interfaces('local-restarted', expected)
        if self.args.mode in ('hub-service', 'self-managed'):
            before = self.identities[-1]['pid']; self.stop_hub(); self.start_hub()
            assert self.identities[-1]['pid'] != before
            self.cli(self.db, 'maintenance', 'sync')
            assert self.cli(self.db, 'upload', 'status')['policy']['mode'] == 'none'
            self.save('hub-restart-rule', self.cli(self.db, 'upload', 'status'))
            self.reject_old_requests('after-hub-restart')
        after_stop = self.requests[self.stop_index:]
        sent = json.dumps([r['payload'] for r in after_stop])
        for secret in ('local-A-new', 'appended while stopped', 'new while stopped', 'plugin-only original'):
            assert secret not in sent, 'forbidden local material sent to Hub'
        self.save('stopped-payloads', after_stop)
        self.cli(self.db, 'upload', 'set', '--mode', 'all'); self.cli(self.db, 'maintenance', 'sync')
        allowed = self.cli(self.db, 'upload', 'status'); assert allowed['state'] == 'confirmed'
        new = next(h for h in self.hub_hits() if h['source_session_id'] == 'local-A-new')
        assert self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': new['reference']})['messages'][0]['text'] == 'selective common local-A new while stopped'
        old = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': self.old_reference})
        assert [m['text'] for m in old['messages']] == ['selective common local-A original']
        before = [(h['source_session_id'], [m['canonical_id'] for m in h['matched_messages']]) for h in self.hub_hits()]
        self.cli(self.db, 'maintenance', 'sync')
        assert before == [(h['source_session_id'], [m['canonical_id'] for m in h['matched_messages']]) for h in self.hub_hits()]
        assert 'local-U2' not in {h['source_session_id'] for h in self.hub_hits()}
        self.save('backfill', {'state': allowed, 'hub': self.hub_hits(), 'old-reference-read': old})

    def cleanup(self):
        failures = []
        if self.login_label:
            try:
                code = 'import sys; from smm_local.login_service import uninstall; uninstall(label=sys.argv[1])'
                self.command([self.t['local_python'], '-I', '-c', code, self.login_label])
                assert not (Path.home() / 'Library/LaunchAgents' / (self.login_label + '.plist')).exists()
            except Exception as exc: failures.append(str(exc))
        for db in self.clients:
            try: self.cli(db, 'stop-on-demand')
            except Exception as exc: failures.append(str(exc))
        if self.relay:
            self.relay.shutdown(); self.relay.server_close()
        try: self.stop_hub()
        except Exception as exc: failures.append(str(exc))
        if self.args.mode == 'hub-service':
            # remove only this task service; database/evidence remain for diagnosis.
            suffix = hashlib.sha256(str(self.state).encode()).hexdigest()[:12]
            if sys.platform == 'linux':
                path = Path.home() / '.config/systemd/user' / ('smm-hub-' + suffix + '.service')
                path.unlink(missing_ok=True); self.command(['systemctl', '--user', 'daemon-reload'])
            elif sys.platform == 'darwin':
                self.command(['sudo', '-n', 'rm', '-f', '/Library/LaunchDaemons/ai.smm.hub.' + suffix + '.plist'])
            else: self.command(['sc.exe', 'delete', 'smm-hub-' + suffix])
        self.save('cleanup', {'failures': failures}); assert not failures, failures

    def run(self):
        failure = None
        try: self.installed(); self.setup(); self.lifecycle()
        except BaseException as exc:
            failure = f'{type(exc).__name__}: {exc}'; raise
        finally:
            try: self.cleanup()
            except BaseException as exc:
                if failure is None: failure = f'cleanup: {exc}'; raise
            finally:
                self.save('payloads', self.requests)
                self.save('result', {'status': 'failed' if failure else 'passed', 'failure': failure,
                                    'started_at': self.started, 'finished_at': now(), 'mode': self.args.mode,
                                    'scope': 'E3 API/CLI/MCP core; no E1 browser claim' if self.protocol_only else 'E1 core entrances; E3 if hub-service; E4 if self-managed; not full A1-A12 proof'})


def main():
    p = argparse.ArgumentParser(); p.add_argument('mode', choices=['client', 'hub-service', 'self-managed', 'login-service']); p.add_argument('--target-config', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    Run(p.parse_args()).run()


if __name__ == '__main__': main()

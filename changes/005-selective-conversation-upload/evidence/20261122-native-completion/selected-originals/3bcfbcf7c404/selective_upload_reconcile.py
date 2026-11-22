"""Actual CLI/Web reconciliation snapshot rejection in independent wheel envs."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from selective_upload_platform import Run


class ReconcileProbe(Run):
    evidence_scope = 'E1 actual dual-version CLI/Web reconciliation only; not full A/E acceptance'

    def local_rule(self):
        value = self.cli(self.db, 'upload', 'status')
        return {k: value[k] for k in ['hub_id', 'device_id', 'generation', 'policy']}

    def hub_rule(self):
        return self.api(self.t['address'], '/v1/upload-policy/status', {'hub_id': self.hub_id, 'device_id': self.device})

    def external_stop(self):
        before = self.hub_rule()
        payload = {'hub_id': self.hub_id, 'device_id': self.device, 'expected_revision': before['revision'],
            'submission_id': 'external-stop-' + uuid4().hex, 'policy': {'mode': 'none', 'projects': []}}
        reply = self.api(self.t['address'], '/v1/upload-policy/set', payload)
        assert reply['revision'] == before['revision'] + 1 and reply['policy']['mode'] == 'none'
        return {'request': payload, 'response': reply}

    def command_reconcile(self, arguments):
        return self.command([self.t['local_python'], '-I', '-X', 'utf8', '-m', 'smm_local.cli', '--db', self.db,
            'upload', 'reconcile', *arguments], expected=None)

    def lifecycle(self):
        self.cli(self.db, 'upload', 'set', '--mode', 'none')
        self.device = self.cli(self.db, 'upload', 'status')['device_id']
        external = self.external_stop()  # An unknown remote submission keeps automatic all pending.
        shown = self.cli(self.db, 'upload', 'reconcile')
        assert shown['local']['policy']['mode'] == shown['hub']['policy']['mode'] == 'none'
        assert shown['hub']['revision'] == external['response']['revision']
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            kwargs = {'headless': True}
            if self.t.get('browser'): kwargs['executable_path'] = self.t['browser']
            browser = p.chromium.launch(**kwargs); context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            context.tracing.start(screenshots=True, snapshots=True, sources=True); page = context.new_page()
            errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
            def show_difference():
                with page.expect_response(lambda r: r.url.endswith('/api/upload/reconcile')) as answer:
                    page.locator('#upload-diff').click()
                response = answer.value; assert response.status == 200
                page.locator('#upload-difference').wait_for()
                return response.json()
            def submit(use):
                with page.expect_response(lambda r: r.url.endswith('/api/upload/reconcile')) as answer:
                    page.locator('#upload-use-' + use).click()
                response = answer.value
                return {'status': response.status, 'request': response.request.post_data_json, 'response': response.json()}
            try:
                page.goto(self.web); page.locator('nav button[data-tab=settings]').click()
                old_web = show_difference()
                assert old_web['local']['generation'] == shown['local']['generation']
                assert old_web['hub']['revision'] == shown['hub']['revision']
                self.offline = True
                try: pending = self.cli(self.db, 'upload', 'set', '--mode', 'all')
                finally: self.offline = False
                assert pending['state'] == 'pending' and pending['generation'] > shown['local']['generation']
                local_before = self.local_rule(); hub_before = self.hub_rule()
                assert local_before['policy']['mode'] == 'all' and hub_before['policy']['mode'] == 'none'
                assert hub_before['revision'] == shown['hub']['revision']
                marker = len(self.requests)
                stale_cli = self.command_reconcile(['--use', 'local', '--expected-hub-revision', str(shown['hub']['revision']),
                    '--expected-local-generation', str(shown['local']['generation'])])
                assert stale_cli.returncode != 0 and not stale_cli.stdout and '本机' in stale_cli.stderr and '重新' in stale_cli.stderr
                stale_web = submit('local')
                assert stale_web['status'] == 400
                assert stale_web['request']['expected_hub_revision'] == old_web['hub']['revision']
                assert stale_web['request']['expected_local_generation'] == old_web['local']['generation']
                page.wait_for_function("document.querySelector('#notice').classList.contains('error')")
                assert '重新' in page.locator('#notice').inner_text()
                page.screenshot(path=str(self.output / 'stale-local-rejected.png'), full_page=True)
                missing = self.command_reconcile(['--use', 'local', '--expected-hub-revision', str(hub_before['revision'])])
                assert missing.returncode != 0 and 'local.generation' in missing.stderr
                assert self.local_rule() == local_before and self.hub_rule() == hub_before
                rejected_calls = self.requests[marker:]
                assert not any(r['route'] == '/v1/upload-policy/set' and r['payload']['device_id'] == self.device for r in rejected_calls)
                help_text = self.command_reconcile(['--help']); assert help_text.returncode == 0
                assert '--expected-local-generation' in help_text.stdout and 'local.generation' in help_text.stdout
                fresh = self.cli(self.db, 'upload', 'reconcile')
                accepted = self.command_reconcile(['--use', 'local', '--expected-hub-revision', str(fresh['hub']['revision']),
                    '--expected-local-generation', str(fresh['local']['generation'])])
                assert accepted.returncode == 0
                accepted_state = json.loads(accepted.stdout)
                assert accepted_state['state'] == 'confirmed' and accepted_state['policy']['mode'] == 'all'
                assert self.hub_rule()['policy'] == accepted_state['policy']
                current_web = show_difference(); later_stop = self.external_stop()
                local_before_hub_stale = self.local_rule()
                stale_hub = submit('local'); assert stale_hub['status'] == 400
                assert stale_hub['request']['expected_local_generation'] == current_web['local']['generation']
                assert stale_hub['request']['expected_hub_revision'] == current_web['hub']['revision']
                assert self.local_rule() == local_before_hub_stale
                assert self.hub_rule()['revision'] == later_stop['response']['revision']
                page.screenshot(path=str(self.output / 'stale-hub-rejected.png'), full_page=True)
                refreshed = show_difference(); adopted = submit('hub')
                assert adopted['status'] == 200 and adopted['response']['policy']['mode'] == 'none'
                assert adopted['request']['expected_local_generation'] == refreshed['local']['generation']
                assert adopted['request']['expected_hub_revision'] == refreshed['hub']['revision']
                page.wait_for_function("document.querySelector('#upload-state').textContent.includes('本机与 Hub 已确认') && document.querySelector('#upload-state').textContent.includes('全部不上传')")
                page.screenshot(path=str(self.output / 'adopted-hub-current.png'), full_page=True)
                assert self.hub_rule()['policy']['mode'] == self.local_rule()['policy']['mode'] == 'none'
                legacy_hub_adoption = self.cli(self.db, 'upload', 'reconcile', '--use', 'hub')
                assert legacy_hub_adoption['state'] == 'confirmed' and legacy_hub_adoption['policy']['mode'] == 'none'
                assert self.hub_rule()['policy'] == legacy_hub_adoption['policy']
                assert not errors, errors
                self.save('reconcile-result', {'initial_cli_view': shown, 'initial_web_view': old_web, 'external_head': external,
                    'pending_local': pending, 'before_stale_local': local_before, 'before_stale_hub': hub_before,
                    'stale_cli': {'exit_code': stale_cli.returncode, 'stdout': stale_cli.stdout, 'stderr': stale_cli.stderr},
                    'stale_web': stale_web, 'missing_cli': {'exit_code': missing.returncode, 'stderr': missing.stderr},
                    'rejected_policy_calls': rejected_calls, 'fresh_cli_view': fresh, 'fresh_cli_accepted': accepted_state,
                    'later_external_stop': later_stop, 'stale_hub_web': stale_hub, 'fresh_web_view': refreshed,
                    'adopted_hub_web': adopted, 'cli_use_hub_without_versions': legacy_hub_adoption, 'final_local': self.local_rule(), 'final_hub': self.hub_rule(),
                    'browser_version': browser.version, 'page_errors': errors})
            finally:
                context.tracing.stop(path=str(self.output / 'reconcile-browser-trace.zip')); browser.close()


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--target-config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); args = p.parse_args(); args.mode = 'client'; ReconcileProbe(args).run()


if __name__ == '__main__': main()

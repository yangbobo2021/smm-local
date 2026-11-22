"""Real 0.4.0/new package combinations in four independent environments."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from selective_upload_fixture import history
from selective_upload_platform import Run, eventually


class Compatibility(Run):
    def __init__(self, args):
        super().__init__(args)
        self.old_local = self.t['old_local_python']; self.old_hub = self.t['old_hub_python']
        self.active_hub_python = self.t['hub_python']

    def cli_at(self, interpreter, db, *args, expected=0):
        p = self.command([interpreter, '-I', '-X', 'utf8', '-m', 'smm_local.cli', '--db', db, *args], expected=expected)
        return json.loads(p.stdout) if p.returncode == 0 else p.stderr

    def sync_at(self, interpreter, db, *, expect_failure=False):
        code = "import sys,json; from smm_local.core import Archive; from smm_local.federation import push_pending; d=Archive(sys.argv[1]); d.sync_codex(); print(json.dumps(push_pending(d)))"
        result = self.command([interpreter, '-I', '-X', 'utf8', '-c', code, db], expected=None)
        if expect_failure: assert result.returncode != 0
        else: assert result.returncode == 0, result.stderr
        return {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

    def new_archive(self, name, interpreter):
        root = self.root / name; root.mkdir()
        history(root, name, 'A', ['selective compatibility ' + name + ' original'])
        empty = root / 'empty'; empty.mkdir(); db = root / 'archive.sqlite3'
        code = "import sys; from smm_local.core import Archive; d=Archive(sys.argv[1]); d.set_settings(codex_root=sys.argv[2],claude_root=sys.argv[3]); d.sync_codex()"
        self.command([interpreter, '-I', '-X', 'utf8', '-c', code, db, root / 'sessions', empty])
        self.clients.append(db); return db

    def start_compat_hub(self, interpreter, state):
        self.state = state; self.t['hub_python'] = interpreter; self.start_hub()
        self.hub_id = self.api(self.t['address'], '/v1/info')['hub_id']

    def execute_combinations(self):
        self.installed()
        for interpreter, package in [(self.old_local, 'smm-local'), (self.old_hub, 'smm-hub')]:
            code = "from importlib.metadata import version; import importlib.util,sys,json,pathlib,hashlib; r=pathlib.Path(importlib.util.find_spec(sys.argv[1].replace('-','_')).origin).parent; print(json.dumps({'version':version(sys.argv[1]),'modules':{p.relative_to(r).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*.py')}}))"
            identity = json.loads(self.command([interpreter, '-I', '-X', 'utf8', '-c', code, package]).stdout)
            assert identity['version'] == '0.4.0'
            expected = self.t['old_candidate']['installed_' + package.split('-')[1]]
            assert {package.replace('-', '_') + '/' + n: h for n, h in identity['modules'].items()} == expected
            self.save('old-' + package + '-identity', {'installed': identity, 'candidate': self.t['old_candidate']})
        (self.root / 'input-token').write_text(self.token, encoding='ascii')
        self.start_compat_hub(self.old_hub, self.root / 'old-hub-state')
        olddb = self.new_archive('old-device', self.old_local)
        self.cli_at(self.old_local, olddb, 'configure-hub', self.t['address'], 'legacy-device', '--token-file', self.root / 'input-token')
        self.sync_at(self.old_local, olddb)
        remote = self.api(self.t['address'], '/v1/search', {'query': 'selective', 'preview_chars': 0})
        hit = next(h for h in remote['results'] if h['source_session_id'] == 'old-device')
        self.save('old-hub-original', remote)
        newdb = self.new_archive('new-device', self.t['local_python'])
        self.cli(newdb, 'configure-hub', self.t['address'], 'new-device', '--token-file', self.root / 'input-token')
        self.cli(newdb, 'upload', 'set', '--mode', 'all')  # Saved locally; old Hub cannot confirm.
        sync = self.sync_at(self.t['local_python'], newdb)
        assert json.loads(sync['stdout'])['uploaded'] == 0
        combined = self.cli(newdb, 'search', 'selective', '--limit', '20')
        assert {h['source_session_id'] for h in combined['results']} == {'old-device', 'new-device'}
        oldhit = next(h for h in combined['results'] if h['source_session_id'] == 'old-device')
        assert self.cli(newdb, 'read', '--reference', oldhit['reference'])['messages'][0]['text'] == 'selective compatibility old-device original'
        project = self.cli(newdb, 'projects')[0]['id']
        scoped = self.cli(newdb, 'search', 'selective', '--scope', 'project', '--project-id', str(project))
        assert {h['source_session_id'] for h in scoped['results']} == {'new-device'} and scoped['fallback_reason']
        self.save('new-local-old-hub', {'sync': sync, 'combined': combined, 'scoped': scoped})
        self.cli(newdb, 'stop-on-demand')
        self.stop_hub()
        # Keep the old server archive and identity, upgrade its runtime only.
        self.start_compat_hub(self.active_hub_python, self.root / 'old-hub-state')
        before = self.api(self.t['address'], '/v1/search', {'query': 'selective', 'preview_chars': 0})
        assert len(before['results']) == 1
        oldreference = {'hub_id': before['hub_id'], 'conversation_id': hit['id'], 'message_id': hit['matched_messages'][0]['hub_message_id']}
        upgraded = self.sync_at(self.t['local_python'], olddb)
        assert json.loads(upgraded['stdout'])['uploaded'] == 0
        status = self.cli(olddb, 'upload', 'status')
        assert status['policy']['mode'] == 'all' and status['state'] == 'confirmed'
        after = self.api(self.t['address'], '/v1/search', {'query': 'selective', 'preview_chars': 0})
        assert len(after['results']) == 1
        original = self.api(self.t['address'], '/v1/read', oldreference)
        assert original['messages'][0]['text'] == 'selective compatibility old-device original'
        self.cli(olddb, 'upload', 'set', '--mode', 'none')
        history(olddb.parent, 'old-device', 'A', ['selective compatibility old-device original', 'selective compatibility forbidden appended'])
        rejected = self.sync_at(self.old_local, olddb, expect_failure=True)
        current = self.api(self.t['address'], '/v1/read', oldreference)
        assert current['messages'] == original['messages']
        oldread = self.cli_at(self.old_local, olddb, 'read', str(hit['id']), '--hub-id', self.hub_id,
                              '--hub-message-id', str(hit['matched_messages'][0]['hub_message_id']))
        assert oldread['messages'][0]['text'] == 'selective compatibility old-device original'
        self.save('migrated-old-device', {'before': before, 'after': after, 'upgraded': upgraded, 'state': status,
                                        'old_write_rejected': rejected, 'old_read': oldread})
        # An unmanaged different legacy device still uploads normally.
        unmanaged = self.new_archive('unmanaged-legacy', self.old_local)
        self.cli_at(self.old_local, unmanaged, 'configure-hub', self.t['address'], 'unmanaged-legacy', '--token-file', self.root / 'input-token')
        self.sync_at(self.old_local, unmanaged)
        assert any(h['source_session_id'] == 'unmanaged-legacy' for h in self.hub_hits())
        self.save('unmanaged-old-local', self.hub_hits())
        # Same Hub, different usable URL preserves the stop. Actual new Hub requires choice.
        same = self.t['address'].replace('localhost', '127.0.0.1')
        self.cli(olddb, 'configure-hub', same, 'legacy-device', '--token-file', self.root / 'input-token')
        assert self.cli(olddb, 'upload', 'status')['policy']['mode'] == 'none'
        for db in self.clients: self.cli(db, 'stop-on-demand')
        self.stop_hub(); self.start_compat_hub(self.active_hub_python, self.root / 'new-identity-hub')
        self.cli(olddb, 'configure-hub', self.t['address'], 'legacy-device', '--token-file', self.root / 'input-token')
        newstate = self.cli(olddb, 'upload', 'status'); assert newstate['state'] == 'needs_selection'
        assert self.sync_at(self.t['local_python'], olddb)['exit_code'] == 0
        legacy_after_registration = self.sync_at(self.old_local, olddb, expect_failure=True)
        assert not self.hub_hits()
        self.save('actual-hub-change', {'state': newstate, 'old_write_rejected_after_registration': legacy_after_registration})

    def run(self):
        failure = None
        try: self.execute_combinations()
        except BaseException as exc: failure = f'{type(exc).__name__}: {exc}'; raise
        finally:
            try: self.cleanup()
            finally: self.save('result', {'status': 'failed' if failure else 'passed', 'failure': failure, 'scope': 'actual 0.4.0/new Local and Hub combinations'})


def main():
    p = argparse.ArgumentParser(); p.add_argument('--target-config', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); args.mode = 'self-managed'; Compatibility(args).run()


if __name__ == '__main__': main()

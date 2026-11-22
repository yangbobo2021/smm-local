"""Installed-package restore probes; all archives/services are task-owned.

R4 substitutes an offline installer success, then injects a health failure after
an actual service restart and a new stop decision. Package bytes stay candidate
bytes. It tests the real upgrade/restore control path, not publishing/installing
an unknown package from a registry.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

from selective_upload_platform import Run


class Recovery(Run):
    def sql_backup(self, database, destination):
        with sqlite3.connect(database) as source, sqlite3.connect(destination) as target: source.backup(target)
        return hashlib.sha256(destination.read_bytes()).hexdigest()

    def sql_restore(self, backup, database):
        with sqlite3.connect(backup) as source, sqlite3.connect(database) as target: source.backup(target)

    def initial(self):
        self.installed(); self.setup()
        self.cli(self.db, 'upload', 'set', '--mode', 'all'); self.cli(self.db, 'maintenance', 'sync')
        hit = next(h for h in self.hub_hits() if h['source_session_id'] == 'local-A')
        self.reference = hit['reference']
        self.save('original-before-backup', self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': self.reference}))
        self.local_backup = self.root / 'old-local.sqlite3'; self.hub_backup = self.root / 'old-hub.sqlite3'
        local_hash = self.sql_backup(self.db, self.local_backup)
        hub_hash = self.sql_backup(self.state / 'smm-hub.sqlite3', self.hub_backup)
        self.config_backup = self.root / 'old-local.hub.json'
        self.config_backup.write_bytes(Path(str(self.db) + '.hub.json').read_bytes())
        self.profile_backup = self.root / 'old-hub-profile.json'
        profile = self.state / 'hub.json'
        if profile.exists(): self.profile_backup.write_bytes(profile.read_bytes())
        self.save('backup-identity', {'local_sha256': local_hash, 'hub_sha256': hub_hash,
                                    'profile_sha256': hashlib.sha256(self.profile_backup.read_bytes()).hexdigest() if self.profile_backup.exists() else None})

    def stop_and_append(self):
        self.cli(self.db, 'upload', 'set', '--mode', 'none')
        self.command([self.t['local_python'], '-I', Path(__file__).with_name('selective_upload_fixture.py'), 'append', '--root', self.root / 'local'])
        self.cli(self.db, 'maintenance', 'sync')
        assert not any(h['source_session_id'] == 'local-A-new' for h in self.hub_hits())
        self.save('confirmed-stop', self.cli(self.db, 'upload', 'status'))

    def restore_case(self):
        self.initial(); self.stop_and_append()
        if self.args.case == 'R1':
            prepared = self.cli(self.db, 'upload', 'prepare-restore')
            guard = Path(str(self.db) + '.upload-guard.json')
            before = guard.read_bytes()
            self.cli(self.db, 'stop-on-demand')
            self.sql_restore(self.local_backup, self.db)
            Path(str(self.db) + '.hub.json').write_bytes(self.config_backup.read_bytes())
            assert guard.read_bytes() == before
            self.cli(self.db, 'maintenance', 'status')
        else:
            prepared = self.admin('prepare-restore')
            guard = Path(str(self.state / 'smm-hub.sqlite3') + '.upload-guard.json')
            before = guard.read_bytes()
            self.stop_hub(); self.sql_restore(self.hub_backup, self.state / 'smm-hub.sqlite3')
            if self.args.case == 'R3':
                assert self.profile_backup.exists(), 'R3 requires a real configured Hub service'
                (self.state / 'hub.json').write_bytes(self.profile_backup.read_bytes())
            assert guard.read_bytes() == before
            self.start_hub(); self.cli(self.db, 'maintenance', 'sync')
        assert prepared['body_stopped']
        assert str(guard) in prepared['do_not_restore']
        self.save('restore-preparation', prepared)
        self.check_difference_and_finish()

    def check_difference_and_finish(self):
        before = self.cli(self.db, 'upload', 'status')
        assert before['state'] == 'conflict', before
        diff = self.cli(self.db, 'upload', 'reconcile')
        assert diff['hub']['policy']['mode'] == 'none'
        unchanged = self.cli(self.db, 'upload', 'status')
        assert (unchanged['generation'], unchanged['policy']) == (before['generation'], before['policy'])
        self.save('difference-before-decision', diff)
        adopted = self.cli(self.db, 'upload', 'reconcile', '--use', 'hub')
        assert adopted['state'] == 'confirmed' and adopted['policy']['mode'] == 'none'
        self.cli(self.db, 'maintenance', 'sync')
        assert 'local-A-new' not in {h['source_session_id'] for h in self.hub_hits()}
        original = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': self.reference})
        assert [m['text'] for m in original['messages']] == ['selective common local-A original']
        self.save('adopted-stop', {'state': adopted, 'old-original': original})
        self.cli(self.db, 'upload', 'set', '--mode', 'only', '--project-id', str(self.projects['A']))
        self.cli(self.db, 'maintenance', 'sync')
        hits = {h['source_session_id']: h for h in self.hub_hits()}
        expected = {'local-A': ['selective common local-A original', 'selective common local-A appended while stopped'],
                    'local-A-new': ['selective common local-A new while stopped']}
        reads = {}
        for session, texts in expected.items():
            read = self.api(self.t['address'], '/v1/read', {'hub_id': self.hub_id, 'reference': hits[session]['reference']})
            assert [m['text'] for m in read['messages']] == texts
            reads[session] = read
        def identities(): return sorted((h['source_session_id'], m['canonical_id'], m['content_version']) for h in self.hub_hits() for m in h['matched_messages'])
        before = identities(); self.cli(self.db, 'maintenance', 'sync'); assert identities() == before
        self.save('allowed-backfill', reads)

    def upgrade_failure(self):
        assert self.args.mode == 'hub-service' and sys.platform == 'linux', 'R4 uses real Linux systemd-user service'
        self.initial()
        # The injected worker executes Hub.upgrade in its actual installed env;
        # sys.prefix must be the task's tools/smm-hub directory.
        prefix = Path(self.t['hub_python']).parent.parent
        assert prefix.name == 'smm-hub'
        fake = self.root / 'offline-installer'
        fake.write_text('#!' + self.t['hub_python'] + '\nimport json,sys\nfrom pathlib import Path\np=Path(' + repr(str(self.root / 'installer-calls.jsonl')) + ')\nwith p.open("a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nif sys.argv[1:]==["tool","dir"]:print(' + repr(str(prefix.parent)) + ')\n', encoding='utf-8')
        fake.chmod(0o700)
        local_config = json.loads(Path(str(self.db) + '.hub.json').read_text())
        worker = self.root / 'upgrade-worker.py'
        worker.write_text('''import json,sys,ssl
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request,build_opener,ProxyHandler,HTTPSHandler
from smm_hub.hub_admin import Hub
from smm_hub.upload import HubUpload
from smm_hub._archive import Archive
root,installer,address,cert,device,report=sys.argv[1:]
h=Hub(Path(root));token=(Path(root)/'hub-token').read_text().strip()
opener=build_opener(ProxyHandler({}),HTTPSHandler(context=ssl.create_default_context(cafile=cert)))
def api(route,payload):
 with opener.open(Request(address+'/v1/'+route,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}),timeout=10) as r:return json.load(r)
original=h.status;observed={};failed=False
def failing_health(*args,**kwargs):
 global failed
 result=original(*args,**kwargs)
 if not failed:
  failed=True
  state=api('upload-policy/status',{'hub_id':result['hub_id'],'device_id':device})
  observed['stop_before_failure']=api('upload-policy/set',{'hub_id':state['hub_id'],'device_id':device,'expected_revision':state['revision'],'submission_id':'controlled-health-stop','policy':{'mode':'none','projects':[]}})
  raise RuntimeError('synthetic upgrade health failure after confirmed stop')
 return result
h.status=failing_health
try:h.upgrade(SimpleNamespace(uv=installer,version='0.4.0',index=None,prerelease=False))
except RuntimeError as e:observed['upgrade_exception']=str(e)
else:raise AssertionError('expected actual upgrade recovery branch')
assert failed and '已恢复' in observed['upgrade_exception']
observed['after_recovery']=original(wait=True)
observed['control']=HubUpload(Archive(h.database),observed['stop_before_failure']['hub_id']).status(device)
assert observed['control']['policy']['mode']=='none' and observed['control']['conflict']
observed['installer_kind']='offline success stub; actual package remains candidate bytes; real systemd start/health/restore'
Path(report).write_text(json.dumps(observed,ensure_ascii=False,indent=2))
''', encoding='utf-8')
        report = self.root / 'upgrade-worker-result.json'
        self.command([self.t['hub_python'], '-I', worker, self.state, fake, self.t['address'], self.t['cert'], local_config['device_id'], report], timeout=120)
        self.save('upgrade-failure-recovery', json.loads(report.read_text()))
        self.command([self.t['local_python'], '-I', Path(__file__).with_name('selective_upload_fixture.py'), 'append', '--root', self.root / 'local'])
        self.cli(self.db, 'maintenance', 'sync')
        self.check_difference_and_finish()

    def run(self):
        error = None
        try:
            if self.args.case == 'R4': self.upgrade_failure()
            else: self.restore_case()
        except BaseException as exc: error = f'{type(exc).__name__}: {exc}'; raise
        finally:
            try: self.cleanup()
            except BaseException as exc:
                if error is None: error = f'cleanup: {exc}'; raise
            finally:
                self.save('result', {'status': 'failed' if error else 'passed', 'failure': error, 'case': self.args.case,
                                     'scope': 'actual installed package restore procedure; R4 real upgrade failure path with offline installer stub'})


def main():
    p = argparse.ArgumentParser(); p.add_argument('mode', choices=['self-managed', 'hub-service']); p.add_argument('--case', choices=['R1', 'R2', 'R3', 'R4'], required=True)
    p.add_argument('--target-config', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    Recovery(p.parse_args()).run()


if __name__ == '__main__': main()

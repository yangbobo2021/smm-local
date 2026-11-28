"""Task-owned installed Hub service controller for macOS and Ubuntu H probes.

macOS execution is intended for the authorized native CI runner with sudo -n.
The controller never substitutes a foreground process for a managed service.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import time

from document_formats_installed_protocols import FormatProbe
from hub_documents_checks import stopped
from hub_documents_platform import now


class NativePosixProbe(FormatProbe):
    def __init__(self, config, output):
        assert sys.platform in {'darwin', 'linux'}
        super().__init__(config, output)
        suffix = hashlib.sha256(str(self.hub_state.resolve()).encode()).hexdigest()[:12]
        self.unit = 'smm-hub-' + suffix + '.service'
        self.label = 'ai.smm.hub.' + suffix
        self.unit_path = Path.home() / '.config/systemd/user' / self.unit
        self.plist = Path('/Library/LaunchDaemons') / (self.label + '.plist')
        self.service_installed = False
        self.service_pid = None
        self.service_events = []
        self.initial_linger = None
        self.initial_manager = None
        assert not (self.plist if sys.platform == 'darwin' else self.unit_path).exists()

    def env(self, role='a'):
        value = super().env(role)
        if sys.platform == 'linux':
            value.update(XDG_RUNTIME_DIR='/run/user/' + str(os.getuid()),
                DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/' + str(os.getuid()) + '/bus')
        if hasattr(self, 'gate_root'):
            value.update(SMM_008_ACTIVE_GATE=str(self.gate_root),
                SMM_008_ACTIVE_RAW=json.dumps(self.gate_raw_paths), SMM_008_ACTIVE_SOURCES='[]')
        return value

    def native(self, label, argv, *, code=0):
        return self.run('native-service-' + label, argv, code=code, role='hub')

    def start(self, role):
        if role != 'hub':
            return super().start(role)
        self.phase = 'resume-captured' if getattr(self,'native_resume_aid',None) else 'service-control'
        if not self.service_installed:
            if sys.platform == 'darwin':
                self.native('sudo-preflight', ['sudo', '-n', 'true'])
                self.native('initial-registration', ['sudo', '-n', 'launchctl', 'print', 'system/' + self.label], code=113)
            else:
                linger = self.native('initial-linger', ['loginctl', 'show-user', str(os.getuid()), '-p', 'Linger', '--value']).strip()
                manager = self.native('initial-user-manager', ['systemctl', 'show', 'user@' + str(os.getuid()) + '.service', '-p', 'ActiveState', '--value']).strip()
                assert linger in {'yes', 'no'} and manager in {'active', 'inactive'}
                self.initial_linger, self.initial_manager = linger, manager
                if self.initial_linger != 'yes':
                    self.native('enable-linger', ['sudo', '-n', 'loginctl', 'enable-linger', str(os.getuid())])
                if self.initial_manager != 'active':
                    self.native('start-user-manager', ['sudo', '-n', 'systemctl', 'start', 'user@' + str(os.getuid()) + '.service'])
            self.service_installed = True  # Cleanup must also cover partial setup.
            self.cli('hub', 'setup', '--address', self.address['hub'], '--bind', '127.0.0.1',
                '--port', self.ports['hub'], '--tls-cert', self.ca, '--tls-key', self.key, '--ca-file', self.ca)
            self.token = (self.hub_state / 'hub-token').read_text(encoding='ascii').strip()
            self.token_file.write_text(self.token, encoding='ascii')
            self.token_file.chmod(0o600)
        else:
            self.cli('hub', 'enable')
        deadline = time.monotonic() + 40
        while True:
            try:
                self.request('hub', '/v1/info')
                break
            except (OSError, TimeoutError):
                assert time.monotonic() < deadline
                time.sleep(.1)
        import psutil
        if sys.platform == 'darwin':
            actual = self.native('actual-launchd', ['sudo', '-n', 'launchctl', 'print', 'system/' + self.label])
            matches = re.findall(r'^\s*pid = (\d+)\s*$', actual, flags=re.MULTILINE)
            assert len(matches) == 1
            pid = int(matches[0])
            definition = plistlib.loads(self.plist.read_bytes())
            import pwd
            assert definition['Label'] == self.label and definition['UserName'] == pwd.getpwuid(os.getuid()).pw_name
        else:
            actual = self.native('actual-systemd', ['systemctl', '--user', 'show', self.unit,
                '-p', 'MainPID', '-p', 'ActiveState', '-p', 'ExecStart', '-p', 'FragmentPath'])
            matches = re.findall(r'^MainPID=(\d+)$', actual, flags=re.MULTILINE)
            assert len(matches) == 1 and 'ActiveState=active' in actual
            pid = int(matches[0])
            definition = self.unit_path.read_text(encoding='utf-8')
            assert 'FragmentPath=' + str(self.unit_path) in actual
        process = psutil.Process(pid)
        assert process.uids().effective == os.getuid() != 0
        assert 'smm_hub.cli' in process.cmdline() and str(self.hub_state) in process.cmdline()
        self.service_pid = pid
        self.service_events.append({'action': 'started', 'at': now(), 'pid': pid,
            'created': process.create_time(), 'uid': process.uids().effective,
            'argv': process.cmdline(), 'native_status': actual, 'definition': definition})
        self.save('native-service-events', self.service_events)
        self.phase = 'resume-captured' if getattr(self,'native_resume_aid',None) else 'prepare'

    def stop(self, role):
        if role != 'hub':
            return super().stop(role)
        assert self.service_pid is not None
        self.phase = 'service-control'
        import psutil
        process = psutil.Process(self.service_pid)
        members = []
        for member in [process, *process.children(recursive=True)]:
            try:
                members.append({'pid': member.pid, 'created': member.create_time()})
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
        self.cli('hub', 'disable')
        stopped([m['pid'] for m in members], [('127.0.0.1', self.ports['hub'])])
        self.service_pid = None
        event = {'action': 'stopped', 'at': now(), 'members': members, 'port_unbound': True}
        self.service_events.append(event)
        self.save('native-service-events', self.service_events)
        self.phase = 'archive-only'
        return event

    def assert_restart_read_only(self,start):
        from document_formats_protocol_guards import events
        all_events=events(self);window=all_events[start:];accepted=[]
        import pwd
        user=pwd.getpwuid(os.getuid()).pw_name
        allowed=[['systemctl','--user','show-environment'],
            ['loginctl','show-user',user,'-p','Linger','--value'],
            ['systemctl','--user','daemon-reload'],['systemctl','--user','enable',self.unit],
            ['systemctl','--user','start',self.unit],['sudo','-v'],
            ['sudo','launchctl','enable','system/'+self.label],
            ['sudo','launchctl','print','system/'+self.label],
            ['sudo','launchctl','bootstrap','system',str(self.plist)],
            ['sudo','launchctl','kickstart','system/'+self.label]]
        for event in window:
            assert event['kind'] not in {'source-open','content-processing'},event
            if event['kind']=='network-call':assert event['allowed'],event
            if event['kind']!='child-start':continue
            identities=[e for e in all_events if e['kind']=='identity' and e['owner']==event['owner']
                and e['pid']==event['pid'] and e['monotonic_ns']<=event['monotonic_ns']]
            assert identities;identity=max(identities,key=lambda e:e['monotonic_ns'])
            assert event['owner']=='hub' and identity['euid']==os.getuid()!=0
            argv=identity['argv'];assert 'smm_hub.cli' in argv and argv[-1]=='enable'
            assert Path(argv[argv.index('--state-dir')+1]).resolve()==self.hub_state.resolve()
            effective=event['effective_arguments'];assert effective is not None and len(effective)>1
            command=list(map(str,effective[1]));command[0]=Path(command[0]).name
            install=(len(command)==10 and command[:8]==['sudo','install','-o','root','-g','wheel','-m','644']
                and command[-1]==str(self.plist) and Path(command[8]).is_absolute())
            assert command in allowed or install,command
            accepted.append({'event':event,'actual_maintenance_identity':identity,'exact_native_command':command})
        assert accepted,'Actual native startup management was not observed'
        self.save('native-normal-restart-zero-processing',{'events':window,'qualified_native_management':accepted,
            'unexpected_source_processing_ocr_or_business_child':[]})

    def cleanup(self):
        errors = []
        pending=getattr(self,'pending_native_stop',None)
        if pending is not None and pending.is_alive():
            pending.join(timeout=150)
            if pending.is_alive():
                self.save('native-service-cleanup',{'errors':[{'step':'wait-owned-stop',
                    'error':'native stop still running; no concurrent cleanup was issued'}]})
                raise RuntimeError('Owned native stop did not finish; cleanup deferred without a second disable')
        self.phase = 'cleanup'
        def attempt(label, action):
            try:
                return action()
            except BaseException as error:
                errors.append({'step': label, 'type': type(error).__name__, 'error': str(error)})
        if self.service_installed:
            query = (['sudo', '-n', 'launchctl', 'print', 'system/' + self.label] if sys.platform == 'darwin'
                else ['systemctl', '--user', 'show', self.unit, '-p', 'LoadState', '-p', 'FragmentPath', '-p', 'ActiveState'])
            attempt('native-manager-before-disable', lambda: self.native_observe('native-manager-before-disable', query))
            # Do not let a missing profile/dead PID/failed setup skip removal
            # of a definition already registered by the actual OS manager.
            if (self.hub_state / 'hub.json').exists():
                attempt('product-disable', lambda: self.cli('hub', 'disable'))
            if sys.platform == 'darwin':
                status = None
                def query_mac_before():
                    nonlocal status
                    status = self.native_observe('cleanup-registration-before', ['sudo', '-n', 'launchctl', 'print', 'system/' + self.label])
                    assert status['code'] in {0, 113}
                attempt('query-mac-before-removal', query_mac_before)
                if status is not None and status['code'] == 0:
                    attempt('native-bootout', lambda: self.native('cleanup-bootout', ['sudo', '-n', 'launchctl', 'bootout', 'system/' + self.label]))
                def mac_definition():
                    self.save('native-definition-before', {'exists': self.plist.exists(),
                        'definition': plistlib.loads(self.plist.read_bytes()) if self.plist.exists() else None})
                attempt('definition-before', mac_definition)
                attempt('remove-mac-definition', lambda: self.native('cleanup-plist', ['sudo', '-n', 'rm', '-f', '--', str(self.plist)]))
                def query_mac():
                    self.native('registration-after', ['sudo', '-n', 'launchctl', 'print', 'system/' + self.label], code=113)
                    assert not self.plist.exists()
                attempt('verify-mac-removal', query_mac)
            else:
                attempt('definition-before', lambda: self.native('cleanup-unit-before', ['systemctl', '--user', 'show', self.unit, '-p', 'LoadState', '-p', 'FragmentPath']))
                # disable --now also removes enablement symlinks after a setup
                # failed before a usable Hub profile was persisted.
                attempt('native-disable', lambda: self.native('cleanup-native-disable', ['systemctl', '--user', 'disable', '--now', self.unit]))
                attempt('unlink-unit', lambda: self.unit_path.unlink(missing_ok=True))
                attempt('reload-removed-unit', lambda: self.native('reload-removed-unit', ['systemctl', '--user', 'daemon-reload']))
                def query_linux():
                    after = self.native('registration-after', ['systemctl', '--user', 'show', self.unit, '-p', 'LoadState', '-p', 'FragmentPath'])
                    assert not self.unit_path.exists() and 'LoadState=not-found' in after and 'FragmentPath=\n' in after
                attempt('verify-linux-removal', query_linux)
            attempt('owned-port-stopped', lambda: stopped([self.service_pid] if self.service_pid else [], [('127.0.0.1', self.ports['hub'])]))
            self.service_pid = None
        try:
            super().cleanup()
        except BaseException as error:
            errors.append({'step': 'foreground-cleanup', 'error': str(error)})
        if sys.platform == 'linux':
            def restore_linger():
                if self.initial_linger is not None and self.initial_linger != 'yes':
                    self.native('restore-linger', ['sudo', '-n', 'loginctl', 'disable-linger', str(os.getuid())])
                if self.initial_linger is not None:
                    actual = self.native('restored-linger', ['loginctl', 'show-user', str(os.getuid()), '-p', 'Linger', '--value']).strip()
                    assert actual == self.initial_linger
            def restore_manager():
                if self.initial_manager is not None and self.initial_manager != 'active':
                    self.native('restore-user-manager', ['sudo', '-n', 'systemctl', 'stop', 'user@' + str(os.getuid()) + '.service'])
                if self.initial_manager is not None:
                    actual = self.native('restored-user-manager', ['systemctl', 'show', 'user@' + str(os.getuid()) + '.service', '-p', 'ActiveState', '--value']).strip()
                    assert actual == self.initial_manager
            attempt('restore-linger', restore_linger)
            attempt('restore-manager', restore_manager)
        self.save('native-service-cleanup', {'errors': errors, 'finished_at': now()})
        assert not errors, errors

    def native_observe(self, label, argv):
        result = subprocess.run(argv, capture_output=True, env=self.env('hub'), timeout=45)
        self.keep('native/' + label + '.stdout', result.stdout)
        self.keep('native/' + label + '.stderr', result.stderr)
        record = {'argv': list(map(str, argv)), 'code': result.returncode,
            'stdout': result.stdout.decode('utf-8', errors='replace'),
            'stderr': result.stderr.decode('utf-8', errors='replace')}
        self.save(label, record)
        return record

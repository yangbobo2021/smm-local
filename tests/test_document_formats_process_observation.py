"""Verified process exit is distinct from an unreadable live task identity."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import uuid4

import psutil
import pytest

from document_helpers import observe
from document_formats_platform import (spawn_identity,process_tree,matching_process,
    same_existing_path,refresh_owned_records,terminate_verified)
from smm_local.document_supervisor import matching


CHILD = '''import json,os,sys
from pathlib import Path
p=Path(sys.argv[1]);temporary=p.with_suffix('.new')
temporary.write_text(json.dumps({'pid':os.getpid(),'token':sys.argv[2],'executable':sys.executable}),encoding='utf-8')
temporary.replace(p)
sys.stdin.buffer.read(1)
'''


def start_owned(root, index, owned):
    ready = root / ('ready-' + str(index) + '.json')
    token = uuid4().hex
    argv = [sys.executable, '-B', '-u', '-c', CHILD, str(ready), token]
    with (root / (str(index) + '.stdout')).open('wb') as stdout, (root / (str(index) + '.stderr')).open('wb') as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                 start_new_session=os.name != 'nt', cwd=root)
    value = {'child': child, 'token': token, 'index': index, 'argv': argv,
             'launcher': None, 'members': [], 'stamp': None, 'identity': None,
             'reported': None, 'prepare_error': None}
    owned.append(value)  # Cleanup responsibility exists before any handshake assertion.
    launcher = None
    executables = [sys.executable, psutil.Process().exe()]
    value['executables'] = executables
    try:
        launcher = spawn_identity(psutil.Process(child.pid))
        value['launcher'] = launcher
        deadline = time.monotonic() + 5
        while not ready.exists():
            assert child.poll() is None, 'owned preparation child exited before its handshake'
            assert time.monotonic() < deadline, 'owned preparation handshake timed out'
            time.sleep(.005)
        actual = json.loads(ready.read_text(encoding='utf-8'))
        value['reported'] = actual
        assert actual['token'] == token
        deadline = time.monotonic() + 5
        while True:
            members = process_tree(launcher)
            remember_members(value,members)
            identities = {item['pid']: item for item in members}
            if actual['pid'] in identities:
                break
            assert time.monotonic() < deadline, 'reported interpreter is not our launcher or descendant'
            time.sleep(.005)
        actual_identity = identities[actual['pid']]
        assert actual_identity['argv'][1:] == argv[1:]
        assert any(same_existing_path(actual_identity['exe'], exe) for exe in executables)
        process = matching_process(actual_identity)
        assert process is not None and same_existing_path(process.cwd(), root)
        assert any(same_existing_path(actual['executable'], exe) for exe in executables)
        value['stamp'] = {'pid': actual_identity['pid'], 'created': actual_identity['created']}
        value.update(process=process, launcher=launcher, identity=actual_identity,
                     executables=executables)
        observe('process-observation-owned', {'index': index, 'stamp': value['stamp'],
                'launcher': launcher, 'identity': actual_identity, 'members': members,
                'token': token, 'argv': argv, 'reported': actual,
                'actual_executable': process.exe(), 'actual_status': process.status(),
                'actual_cwd': process.cwd()})
        return value
    except BaseException as error:
        value['prepare_error'] = {'type': type(error).__name__, 'message': str(error)}
        observe('process-observation-prepare-error', {'index': index, 'error': value['prepare_error'],
                'launcher': value['launcher'], 'reported': value['reported'],
                'registered_members': value['members']})
        raise


def release(child):
    if child.stdin is not None and not child.stdin.closed:
        try:
            child.stdin.write(b'x')
            child.stdin.flush()
        except BrokenPipeError:
            pass
        finally:
            child.stdin.close()


def remember_members(value, members):
    # Never lose a previously established descendant when its launcher exits.
    recorded = {(v['pid'], v['created']): v for v in value['members']}
    for member in members:
        recorded.setdefault((member['pid'], member['created']), member)
    value['members'] = list(recorded.values())


def finish_owned(value):
    child = value['child']
    if value['launcher'] is not None:
        remember_members(value, process_tree(value['launcher']))
    registered = list(value['members'])
    release(child)
    launcher_timed_out = False
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        launcher_timed_out = True
    # Always recheck all historical identities, even if launcher.wait succeeded.
    remaining = refresh_owned_records(registered, value['executables'])
    if remaining:
        terminate_verified(remaining, owner=child)
    elif launcher_timed_out:
        raise AssertionError('owned launcher did not exit but no complete identity can be reverified')
    code = child.wait(timeout=5)
    observations = []
    for member in registered:
        current = matching_process(member)
        observations.append({'identity': member, 'gone': current is None})
    result = {'stamp': value['stamp'], 'launcher': value['launcher'],
              'identity': value['identity'], 'registered_members': registered,
              'member_exit_observations': observations, 'exit_code': code,
              'forced_kill': bool(remaining), 'cleanup_escalation_candidates': remaining,
              'prepare_error': value['prepare_error'], 'reported': value['reported']}
    observe('process-observation-owned-cleanup', result)
    assert all(item['gone'] for item in observations), 'registered task member is still alive'
    return result


def deny_reads(patch, values, events, *, status=False):
    targets = {v['stamp']['pid'] for v in values}
    original_cmdline = psutil.Process.cmdline
    original_status = psutil.Process.status
    def cmdline(process):
        if process.pid in targets:
            events.append({'pid': process.pid, 'read': 'cmdline', 'exception': 'psutil.AccessDenied'})
            raise psutil.AccessDenied(process.pid)
        return original_cmdline(process)
    def state(process):
        if status and process.pid in targets:
            events.append({'pid': process.pid, 'read': 'status', 'exception': 'psutil.AccessDenied'})
            raise psutil.AccessDenied(process.pid)
        return original_status(process)
    patch.setattr(psutil.Process, 'cmdline', cmdline)
    if status:
        patch.setattr(psutil.Process, 'status', state)
    # The error probe is independently reachable on real owned live objects;
    # a correct implementation may classify a zombie before calling cmdline.
    for value in values:
        with pytest.raises(psutil.AccessDenied):
            value['process'].cmdline()
    assert psutil.Process(os.getpid()).cmdline() == original_cmdline(psutil.Process(os.getpid()))


def test_verified_exit_and_live_identity_denial_are_distinct(tmp_path, monkeypatch):
    # TC-008-process-identity-observation. Never fabricate PID/time/exit state.
    owned = []
    cleanup = []
    try:
        for index in range(2):
            start_owned(tmp_path, index, owned)
        assert len({v['stamp']['pid'] for v in owned}) == 2
        for index, value in enumerate(owned):
            result = matching(value['stamp'], value['token'])
            assert result is not None and result.pid == value['stamp']['pid']
            assert result.create_time() == value['stamp']['created']
            assert matching({**value['stamp'], 'created': value['stamp']['created'] + 1}, value['token']) is None
            assert matching(value['stamp'], owned[1 - index]['token']) is None
        for status_denied in (False, True):
            events = []
            before = [{'stamp': v['stamp'], 'status': v['process'].status()} for v in owned]
            with monkeypatch.context() as patch:
                deny_reads(patch, owned, events, status=status_denied)
                for value in owned:
                    with pytest.raises(psutil.AccessDenied) as error:
                        matching(value['stamp'], value['token'])
                    assert error.value.pid == value['stamp']['pid']
            for value in owned:
                assert value['process'].is_running() and value['process'].status() != psutil.STATUS_ZOMBIE
            observe('process-observation-live-denial', {'status_denied': status_denied,
                    'actual_live_before': before, 'events': events, 'both_failed_explicitly': True})
        for value in owned:
            release(value['child'])
        if os.name != 'nt':
            for value in owned:
                deadline = time.monotonic() + 5
                while value['process'].status() != psutil.STATUS_ZOMBIE:
                    assert time.monotonic() < deadline, 'owned child did not enter an observable zombie state'
                    time.sleep(.005)
                assert value['process'].create_time() == value['stamp']['created']
                observe('process-observation-real-zombie', {'stamp': value['stamp'],
                        'status': value['process'].status(), 'not_yet_waited': value['child'].returncode is None})
            events = []
            with monkeypatch.context() as patch:
                # The live positive control has already established the probe.
                # Here errors apply to the actual exited identities only.
                original = psutil.Process.cmdline
                targets = {v['stamp']['pid'] for v in owned}
                def denied(process):
                    if process.pid in targets:
                        events.append({'pid': process.pid, 'read': 'cmdline', 'exception': 'psutil.AccessDenied'})
                        raise psutil.AccessDenied(process.pid)
                    return original(process)
                patch.setattr(psutil.Process, 'cmdline', denied)
                for value in owned:
                    try:
                        result = matching(value['stamp'], value['token'])
                    except BaseException as error:
                        observe('process-observation-exit-error', {'stamp': value['stamp'],
                                'actual_status': value['process'].status(),
                                'error_class': type(error).__name__, 'error': str(error), 'events': events})
                        raise
                    assert result is None
                    observe('process-observation-exit-classified', {'stamp': value['stamp'],
                            'actual_status': value['process'].status(), 'events': events})
        else:
            observe('process-observation-platform-scope', {'platform': sys.platform,
                    'posix_zombie': 'not applicable; live denial controls executed, no Windows Job/service claim'})
    finally:
        cleanup_errors = []
        for value in owned:
            try:
                cleanup.append(finish_owned(value))
            except BaseException as error:
                cleanup_errors.append({'index': value['index'], 'prepare_error': value['prepare_error'],
                        'error_type': type(error).__name__, 'error': str(error),
                        'registered_members': value['members']})
        observe('process-observation-cleanup', {'owned': cleanup, 'errors': cleanup_errors})
        assert not cleanup_errors, cleanup_errors
    assert len(cleanup) == 2 and all(v['exit_code'] == 0 and not v['forced_kill'] for v in cleanup)
    for value in owned:
        assert matching(value['stamp'], value['token']) is None
    observe('process-observation-complete', {'owned_count': 2, 'platform': sys.platform,
            'actual_posix_zombie': os.name != 'nt', 'original_identity_gone_after_wait': True})

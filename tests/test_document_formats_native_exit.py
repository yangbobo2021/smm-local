"""Known live, real exited and actual zombie controls for native-stop evidence."""
from pathlib import Path
import os
import subprocess
import sys
import threading
import time

import psutil
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from document_formats_native_exit import sample, watch_stop, wait_stop_calls
from document_formats_platform import process_identity
from document_helpers import observe


def test_live_identity_cannot_be_reported_stopped():
    stamp = process_identity(psutil.Process())
    saved = []
    assert sample(stamp)['waiting'] is True
    with pytest.raises(AssertionError, match='native stop observation deadline'):
        watch_stop([stamp], stamp, lambda: None, saved.append, timeout=.05)
    assert len(saved) == 1 and saved[0]['result'] is None and saved[0]['stop_call_returned']
    assert sample(stamp)['waiting'] is True
    with pytest.raises(AssertionError, match='identity changed'):
        sample({**stamp, 'created': stamp['created'] + 1})
    observe('native-exit-live-negative', saved[0])


def test_cleanup_clock_excludes_native_command_return_delay():
    children = []
    try:
        for _ in range(2):
            children.append(subprocess.Popen([getattr(sys, '_base_executable', sys.executable),
                                              '-I', '-c', 'import time;time.sleep(30)']))
        members = [process_identity(psutil.Process(c.pid)) for c in children]
        saved = []

        def stop():
            for child in children:
                child.terminate()
            for child in children:
                child.wait(timeout=5)
            time.sleep(.2)

        value = watch_stop(members, members[0], stop, saved.append, timeout=5)
        assert value['status'] == 'verified' and value['cleanup_upper_bound_seconds'] < 1
        assert value['stop_seconds'] >= .2
        assert any(not any(v['waiting'] for v in rows) for rows in saved[0]['samples'])
        assert saved[0]['stop_errors'] == [] and saved[0]['stop_call_returned']
        observe('native-exit-real-stopped', saved[0])
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)


def test_denied_or_unconfirmed_creation_is_never_exit(monkeypatch):
    stamp = process_identity(psutil.Process())
    for error in (psutil.AccessDenied(stamp['pid']), psutil.ZombieProcess(stamp['pid'])):
        def denied(pid):
            raise error
        with monkeypatch.context() as patch:
            patch.setattr(psutil, 'Process', denied)
            result = sample(stamp)
            assert result['waiting'] is True
            observe('native-exit-unknown-negative', result)


def test_stop_callback_error_cannot_be_verified():
    stamp = process_identity(psutil.Process())
    saved = []
    def fail():
        raise RuntimeError('known native command failure')
    with pytest.raises(AssertionError, match='known native command failure'):
        watch_stop([stamp], stamp, fail, saved.append, timeout=1)
    assert saved[0]['result'] is None and saved[0]['stop_call_returned']
    assert len(saved[0]['stop_errors']) == 1
    observe('native-exit-command-error', saved[0])


def test_live_stop_command_ownership_survives_observation_failure():
    stamp = process_identity(psutil.Process())
    release = threading.Event()
    saved = []
    owned = []
    try:
        with pytest.raises(AssertionError, match='native stop observation deadline'):
            watch_stop([stamp], stamp, lambda: release.wait(5), saved.append,
                       timeout=.05, join_timeout=.01, own_thread=owned.append)
        assert len(owned) == 1 and owned[0].is_alive()
        assert saved[0]['result'] is None and saved[0]['stop_call_returned'] is False
        observe('native-exit-stop-ownership', saved[0])
    finally:
        release.set()
        for worker in owned:
            worker.join(timeout=2)
            assert not worker.is_alive()


def test_sample_exit_bound_includes_query_latency(monkeypatch):
    stamp = process_identity(psutil.Process())
    actual = psutil.Process(stamp['pid'])
    was_running = actual.is_running()
    assert was_running
    class SlowMetadata:
        def create_time(self):
            time.sleep(.03)
            return actual.create_time()
        def status(self):
            return actual.status()
        def is_running(self):
            return was_running
    monkeypatch.setattr(psutil, 'Process', lambda pid: SlowMetadata())
    before = time.monotonic()
    result = sample(stamp)
    after = time.monotonic()
    assert before <= result['started'] < result['finished'] <= after
    assert result['finished'] - result['started'] >= .03 and result['waiting']
    observe('native-exit-sample-latency', result)


def test_cleanup_checks_stop_command_registered_during_outer_join():
    from types import SimpleNamespace
    register = threading.Event()
    release = threading.Event()
    saved = []
    probe = SimpleNamespace(save=lambda label, value: saved.append((label, value)))
    def outer():
        assert register.wait(2)
        probe.pending_native_command_stop = threading.Thread(target=lambda: release.wait(5))
        probe.pending_native_command_stop.start()
    probe.pending_native_stop = threading.Thread(target=outer)
    timer = threading.Timer(.03, register.set)
    probe.pending_native_stop.start()
    timer.start()
    try:
        with pytest.raises(RuntimeError, match='cleanup deferred without a second disable'):
            wait_stop_calls(probe, timeout=.15)
        assert not probe.pending_native_stop.is_alive() and probe.pending_native_command_stop.is_alive()
        assert saved[0][1]['errors'][0]['step'] == 'wait-pending_native_command_stop'
        observe('native-exit-late-command-ownership', saved)
    finally:
        register.set();release.set();timer.cancel();timer.join(timeout=2)
        probe.pending_native_stop.join(timeout=2)
        if hasattr(probe, 'pending_native_command_stop'):
            probe.pending_native_command_stop.join(timeout=2)
            assert not probe.pending_native_command_stop.is_alive()


@pytest.mark.skipif(os.name == 'nt', reason='POSIX zombie state only')
def test_real_zombie_is_exit_only_after_creation_identity_is_confirmed():
    child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(.3)'])
    try:
        stamp = process_identity(psutil.Process(child.pid))
        until = time.monotonic() + 5
        while psutil.Process(child.pid).status() != psutil.STATUS_ZOMBIE:
            assert time.monotonic() < until
            time.sleep(.01)
        result = sample(stamp)
        assert result['state'] == psutil.STATUS_ZOMBIE and result['waiting'] is False
        assert result['actual_created'] == stamp['created']
        observe('native-exit-real-zombie', result)
    finally:
        if psutil.pid_exists(child.pid) and psutil.Process(child.pid).status() != psutil.STATUS_ZOMBIE:
            child.kill()
        child.wait(timeout=5)

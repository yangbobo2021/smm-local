"""Probe self-check: never confuse confirmed rules with completed transfer."""
import importlib.util
from pathlib import Path

import pytest
from types import SimpleNamespace


def probe(monkeypatch, states):
    path = Path(__file__).resolve().parents[1] / 'scripts/acceptance/selective_upload_platform.py'
    spec = importlib.util.spec_from_file_location('selective_probe', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    runner = module.Run.__new__(module.Run)
    runner.cli = lambda *args: {'url': 'http://127.0.0.1:1', 'running': True, 'result': None}
    runner.save = lambda *args: None
    requests = []
    sequence = iter(states)
    def api(address, route, payload=None, **kwargs):
        requests.append(route)
        return next(sequence) if route == '/api/status' else {'running': True}
    runner.api = api
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    return module, runner, requests


def state(running, pending, transfer='backfilling', policy='confirmed'):
    return {'sync': {'running': running}, 'upload': {'state': policy, 'transfer_state': transfer,
        'allowed_pending_messages': pending, 'inflight_messages': 1 if running else 0}}


def test_probe_waits_for_job_and_allowed_backfill_not_just_confirmed_rule(monkeypatch):
    complete = state(False, 0, 'complete')
    _, runner, requests = probe(monkeypatch, [state(True, 2), state(False, 1), complete])
    assert runner.sync_done('task-archive', wait_for_upload=True) is complete
    assert requests == ['/api/status', '/api/status', '/api/sync', '/api/status']
    assert len(runner.sync_observations) == 3


def test_probe_can_wait_for_control_only_without_requiring_body_permission(monkeypatch):
    stopped = state(False, 0, 'blocked', 'needs_selection')
    _, runner, requests = probe(monkeypatch, [state(True, 0, 'blocked'), stopped])
    assert runner.sync_done('task-archive') is stopped
    assert requests == ['/api/status', '/api/status']


def test_probe_never_turns_pending_transfer_into_success_at_timeout(monkeypatch):
    module, runner, _ = probe(monkeypatch, [state(False, 1)])
    ticks = iter([0, 1, 3]); monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(AssertionError, match='did not complete'):
        runner.sync_done('task-archive', wait_for_upload=True, seconds=2)


@pytest.mark.parametrize('platform,code', [('win32', 1), ('linux', -15)])
def test_probe_accepts_platform_exit_only_after_requested_stop(monkeypatch, platform, code):
    module, runner, _ = probe(monkeypatch, [])
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform=platform))
    process = SimpleNamespace(pid=123, returncode=None)
    process.poll = lambda: process.returncode
    process.terminate = lambda: setattr(process, 'returncode', code)
    process.wait = lambda **kwargs: code
    runner.process = process; runner.process_stop_requested = False
    runner.args = SimpleNamespace(mode='client'); runner.identities = []
    runner.stop_hub()
    runner.stop_hub()  # Idempotent final cleanup after the explicit stop.
    assert runner.identities[-1]['stop_requested'] is True
    assert runner.identities[-1]['exit_code'] == code


@pytest.mark.parametrize('early,code', [(True, 1), (True, 0), (False, 7)])
def test_probe_keeps_early_or_unexpected_hub_exit_as_failure(monkeypatch, early, code):
    module, runner, _ = probe(monkeypatch, [])
    monkeypatch.setattr(module, 'sys', SimpleNamespace(platform='win32'))
    process = SimpleNamespace(pid=123, returncode=code if early else None)
    process.poll = lambda: process.returncode
    process.terminate = lambda: setattr(process, 'returncode', code)
    process.wait = lambda **kwargs: code
    runner.process = process; runner.process_stop_requested = False
    runner.args = SimpleNamespace(mode='client'); runner.identities = []
    with pytest.raises(AssertionError):
        runner.stop_hub()
    assert runner.identities[-1]['exit_code'] == code

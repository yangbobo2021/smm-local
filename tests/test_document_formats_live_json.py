"""Live observation retries only open uncertainty, never malformed identity."""
import errno
import json
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
from document_formats_live_json import read_live_json
from document_helpers import observe


def test_open_uncertainty_is_preserved_before_real_json_success(tmp_path, monkeypatch):
    path = tmp_path / 'active.json';path.write_bytes(b'{"token":"owned-aid"}\n')
    native = type(path).read_bytes;calls = [];records = [];current_calls = []
    def read(target):
        if target == path:
            calls.append(target)
            if len(calls) == 1: raise PermissionError(errno.EACCES, 'actual denial control', str(path))
            if len(calls) == 2: raise FileNotFoundError(errno.ENOENT, 'replacement gap control', str(path))
        return native(target)
    monkeypatch.setattr(type(path), 'read_bytes', read)
    result = read_live_json(path, time.monotonic() + 1, observe=records.append,
                            current=lambda: current_calls.append(True))
    assert result == {'token': 'owned-aid'} and len(calls) == 3 and len(current_calls) == 4
    assert [x['status'] for x in records] == ['open_failed', 'open_failed', 'read']
    assert [x['type'] for x in records[-1]['attempts']] == ['PermissionError', 'FileNotFoundError']
    assert [x['errno'] for x in records[-1]['attempts']] == [errno.EACCES, errno.ENOENT]
    assert all(x['filename'] == str(path) for x in records[-1]['attempts'])
    assert records[-1]['bytes'] == path.stat().st_size
    observe('live-json-open-uncertainty-control', records)


@pytest.mark.parametrize('kind', ['permission', 'missing', 'malformed', 'identity', 'late'])
def test_persistent_or_invalid_observation_cannot_pass(tmp_path, monkeypatch, kind):
    path = tmp_path / 'active.json';path.write_text('{"token":"owned-aid"}')
    native = type(path).read_bytes;records = [];calls = []
    def read(target):
        calls.append(True)
        if kind == 'permission': raise PermissionError(errno.EACCES, 'persistent denial control', str(path))
        if kind == 'missing': raise FileNotFoundError(errno.ENOENT, 'persistent missing control', str(path))
        if kind == 'late': time.sleep(.04)
        return native(target)
    monkeypatch.setattr(type(path), 'read_bytes', read)
    if kind == 'malformed': path.write_bytes(b'{"token":')
    def current():
        if kind == 'identity': raise AssertionError('enrolled process creation changed')
    error = {'permission': PermissionError, 'missing': FileNotFoundError,
             'malformed': json.JSONDecodeError, 'identity': AssertionError, 'late': TimeoutError}[kind]
    with pytest.raises(error):
        read_live_json(path, time.monotonic() + .025, observe=records.append, current=current)
    if kind == 'identity': assert calls == [] and records == []
    elif kind == 'malformed': assert len(calls) == 1 and records[-1]['status'] == 'invalid_json'
    elif kind == 'late': assert len(calls) == 1 and records[-1]['status'] == 'deadline_exceeded'
    else:
        assert records and all(r['status'] == 'open_failed' for r in records)
        assert all(r['attempts'] for r in records)
    observe('live-json-negative-' + kind, {'records': records, 'read_calls': len(calls)})


def test_successful_read_cannot_pass_after_evidence_save_exceeds_deadline(tmp_path):
    path = tmp_path / 'active.json';path.write_text('{"token":"owned-aid"}')
    records = []
    def save(value):
        records.append(value);time.sleep(.04)
    with pytest.raises(TimeoutError, match='evidence exceeded'):
        read_live_json(path, time.monotonic() + .025, observe=save, current=lambda: None)
    assert len(records) == 1 and records[0]['status'] == 'read'
    observe('live-json-evidence-deadline-negative', records)

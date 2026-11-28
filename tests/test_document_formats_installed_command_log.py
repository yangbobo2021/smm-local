"""Durable original acceptance commands, independent of product processing."""
import base64
from contextlib import contextmanager
import errno
import hashlib
import json
from pathlib import Path

import pytest

from scripts.acceptance.document_formats_installed_protocols import FormatProbe


def recorder(root):
    probe = FormatProbe.__new__(FormatProbe)
    probe.out = root
    return probe


def test_installed_commands_freeze_each_observation_and_preserve_original_bytes(tmp_path):
    probe = recorder(tmp_path)
    raw = b'\xff\x00\r\n'
    body = {'query': '中文 😀'}
    calls = [{'request': body, 'stdout_bytes_base64': base64.b64encode(raw).decode()}]
    probe.save('commands', calls)
    first = (tmp_path / 'commands.jsonl').read_bytes()
    body['query'] = 'later mutation'
    calls.append({'request': {'query': 'second'}, 'exit_code': 0})
    probe.save('commands', calls)
    saved = (tmp_path / 'commands.jsonl').read_bytes()
    assert saved.startswith(first)
    rows = [json.loads(line) for line in saved.splitlines()]
    assert rows[0]['request']['query'] == '中文 😀'
    assert base64.b64decode(rows[0]['stdout_bytes_base64']) == raw
    assert rows[1] == calls[1]
    index = json.loads((tmp_path / 'commands.json').read_text(encoding='utf-8'))
    assert index['schema'] == 'smm-008-command-jsonl-v1'
    assert index['records'] == 2 and index['bytes'] == len(saved)
    assert index['sha256'] == hashlib.sha256(saved).hexdigest()
    probe.save('commands', calls)
    assert (tmp_path / 'commands.jsonl').read_bytes() == saved
    with pytest.raises(AssertionError, match='append-only'):
        probe.save('commands', [])


def test_installed_summary_keeps_prior_receipt_if_storage_fails_mid_write(tmp_path, monkeypatch):
    probe = recorder(tmp_path)
    probe.save('summary', {'complete': 'previous original'})
    original = (tmp_path / 'summary.json').read_bytes()
    normal_open = Path.open

    class BrokenWriter:
        def __init__(self, stream): self.stream = stream
        def write(self, text):
            self.stream.write(text[:8])
            self.stream.flush()
            raise OSError(errno.ENOSPC, 'synthetic test-only disk exhaustion')

    @contextmanager
    def fail_temporary_write(path, *args, **kwargs):
        with normal_open(path, *args, **kwargs) as stream:
            yield BrokenWriter(stream)

    def opened(path, *args, **kwargs):
        if path.parent == tmp_path and path.name.startswith('summary.json.') and path.suffix == '.tmp':
            return fail_temporary_write(path, *args, **kwargs)
        return normal_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', opened)
        with pytest.raises(OSError) as raised:
            probe.save('summary', {'complete': 'next receipt'})
        assert raised.value.errno == errno.ENOSPC
    assert (tmp_path / 'summary.json').read_bytes() == original
    assert json.loads(original) == {'complete': 'previous original'}
    assert not list(tmp_path.glob('*.tmp'))
    probe.save('summary', {'complete': 'next receipt'})
    assert json.loads((tmp_path / 'summary.json').read_text()) == {'complete': 'next receipt'}


@pytest.mark.parametrize('fault', ['second-write', 'partial-write', 'flush', 'fsync', 'index'])
def test_installed_commands_retry_failed_io_without_duplicates_or_changed_observations(tmp_path, monkeypatch, fault):
    probe = recorder(tmp_path)
    calls = [{'id': 0}]
    probe.save('commands', calls)
    prefix = (tmp_path / 'commands.jsonl').read_bytes()
    prior_index = (tmp_path / 'commands.json').read_bytes()
    calls.extend([{'id': 1, 'body': {'value': 'original'}}, {'id': 2}])
    normal_open = Path.open
    import os
    normal_fsync = os.fsync
    counters = {'writes': 0, 'fsync': 0}

    class BrokenStream:
        def __init__(self, stream): self.stream = stream
        def __getattr__(self, name): return getattr(self.stream, name)
        def write(self, raw):
            counters['writes'] += 1
            if fault == 'second-write' and counters['writes'] == 2:
                raise OSError(errno.ENOSPC, 'synthetic command append interruption')
            if fault == 'partial-write':
                self.stream.write(raw[:7])
                raise OSError(errno.ENOSPC, 'synthetic partial command append')
            return self.stream.write(raw)
        def flush(self):
            if fault == 'flush':
                raise OSError(errno.ENOSPC, 'synthetic command flush interruption')
            return self.stream.flush()

    @contextmanager
    def wrapped(path, *args, **kwargs):
        with normal_open(path, *args, **kwargs) as stream:
            yield BrokenStream(stream)

    def opened(path, *args, **kwargs):
        if path == tmp_path / 'commands.jsonl': return wrapped(path, *args, **kwargs)
        if fault == 'index' and path.name.startswith('commands.json.') and path.suffix == '.tmp':
            raise OSError(errno.ENOSPC, 'synthetic index interruption')
        return normal_open(path, *args, **kwargs)

    def fsync(fd):
        counters['fsync'] += 1
        if fault == 'fsync' and counters['fsync'] == 1:
            raise OSError(errno.ENOSPC, 'synthetic command fsync interruption')
        return normal_fsync(fd)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', opened)
        patch.setattr(os, 'fsync', fsync)
        with pytest.raises(OSError) as raised:
            probe.save('commands', calls)
        assert raised.value.errno == errno.ENOSPC
    assert (tmp_path / 'commands.jsonl').read_bytes().startswith(prefix)
    assert (tmp_path / 'commands.json').read_bytes() == prior_index
    calls[1]['body']['value'] = 'mutated after failed observation'
    probe.save('commands', calls)
    raw = (tmp_path / 'commands.jsonl').read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    assert rows == [{'id': 0}, {'id': 1, 'body': {'value': 'original'}}, {'id': 2}]
    index = json.loads((tmp_path / 'commands.json').read_bytes())
    assert index['records'] == len(rows) == 3 and index['bytes'] == len(raw)
    assert index['sha256'] == hashlib.sha256(raw).hexdigest()
    probe.save('commands', calls)
    assert (tmp_path / 'commands.jsonl').read_bytes() == raw


def test_installed_commands_accept_short_writes_and_reject_changed_durable_prefix(tmp_path, monkeypatch):
    probe = recorder(tmp_path)
    normal_open = Path.open

    class ShortWriter:
        def __init__(self, stream): self.stream = stream
        def __getattr__(self, name): return getattr(self.stream, name)
        def write(self, raw): return self.stream.write(raw[:3])

    @contextmanager
    def wrapped(path, *args, **kwargs):
        with normal_open(path, *args, **kwargs) as stream: yield ShortWriter(stream)

    def opened(path, *args, **kwargs):
        if path == tmp_path / 'commands.jsonl': return wrapped(path, *args, **kwargs)
        return normal_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'open', opened)
        probe.save('commands', [{'value': '中文'}])
    raw = (tmp_path / 'commands.jsonl').read_bytes()
    assert json.loads(raw) == {'value': '中文'}
    probe._commands_dirty = True
    (tmp_path / 'commands.jsonl').write_bytes(raw.replace(b'value', b'other'))
    with pytest.raises(AssertionError, match='durable command prefix changed'):
        probe.save('commands', [{'value': '中文'}, {'value': 'second'}])

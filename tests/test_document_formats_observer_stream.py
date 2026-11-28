"""Live audit records commit at LF and retain stable count-cursor prefixes."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
from document_formats_protocol_guards import events


def test_actual_split_writes_do_not_lose_late_earlier_timestamp(tmp_path):
    import os
    import threading
    import time
    a,b=tmp_path/'a.jsonl',tmp_path/'b.jsonl'
    a.touch();b.touch()
    probe=SimpleNamespace(protocol_guard_paths=[a,b])
    entered,release=threading.Event(),threading.Event()
    first={'monotonic_ns':time.monotonic_ns(),'kind':'source-open','path':'中文 source','allowed':False}
    raw=(json.dumps(first,ensure_ascii=False)+'\n').encode()
    split=raw.index('文'.encode())+1  # Actual incomplete UTF-8 as well as JSON.
    errors=[]
    def writer():
        fd=os.open(a,os.O_WRONLY|os.O_APPEND)
        try:
            assert os.write(fd,raw[:split])==split;entered.set()
            assert release.wait(5)
            assert os.write(fd,raw[split:])==len(raw)-split
        except BaseException as error:errors.append(error)
        finally:os.close(fd)
    thread=threading.Thread(target=writer);thread.start()
    try:
        assert entered.wait(5)
        second={'monotonic_ns':time.monotonic_ns(),'kind':'network-call','allowed':True}
        b.write_text(json.dumps(second)+'\n')
        prefix=events(probe);assert prefix==[second]
        with pytest.raises(AssertionError):events(probe,require_complete=True)
        release.set();thread.join(5);assert not thread.is_alive() and not errors
        complete=events(probe,require_complete=True)
        assert complete==[second,first] and complete[:len(prefix)]==prefix
        assert complete[len(prefix):]==[first]  # Forbidden late record is observed.
        assert events(probe)==complete  # No duplicate or skipped record.
    finally:release.set();thread.join(5)


def test_complete_malformed_and_truncated_records_remain_failures(tmp_path):
    path=tmp_path/'audit.jsonl';path.write_bytes(b'{broken}\n')
    probe=SimpleNamespace(protocol_guard_paths=[path])
    with pytest.raises(json.JSONDecodeError):events(probe)
    path.write_text('{"monotonic_ns":1}\n')
    assert events(probe)==[{'monotonic_ns':1}]
    path.write_bytes(b'')
    with pytest.raises(AssertionError,match='truncated'):events(probe)

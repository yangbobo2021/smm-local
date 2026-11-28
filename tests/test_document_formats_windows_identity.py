"""Actual Windows process-token samples must bind to the observed process."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/acceptance'))
import document_formats_windows_identity as identity

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows process tokens')


def test_actual_self_child_tokens_and_wrong_creation_rejected(monkeypatch):
    import psutil
    raw = subprocess.check_output(['whoami.exe', '/user', '/fo', 'csv', '/nh'])
    import re
    expected = re.findall(rb'S-\d-(?:\d+-)*\d+', raw)
    assert len(expected) == 1
    expected = expected[0].decode('ascii')
    current = identity.sample_process(psutil.Process())
    assert current['sid'] == expected
    # Windows venv's redirector can spawn another PID; use the real base
    # interpreter so this control owns the process whose token it samples.
    child = subprocess.Popen([sys._base_executable, '-I', '-c',
        'import os,sys;print(os.getpid(),flush=True);sys.stdin.buffer.read(1)'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        assert int(child.stdout.readline()) == child.pid
        actual = identity.sample_process(psutil.Process(child.pid))
        assert actual['pid'] == child.pid and actual['parent_pid'] == os.getpid()
        assert actual['sid'] == expected and actual['session_id'] == current['session_id']
        assert actual['creation_filetime'] > 0 and actual['created'] >= current['created']
        original = identity.process_token
        def wrong(pid):
            value = original(pid)
            value['created'] -= 10
            return value
        with monkeypatch.context() as patch:
            patch.setattr(identity, 'process_token', wrong)
            with pytest.raises(AssertionError):identity.sample_process(psutil.Process(child.pid))
        print(json.dumps({'self': current, 'child': actual, 'expected_whoami_sid': expected,
            'wrong_creation_rejected': True}))
    finally:
        child.stdin.write(b'x');child.stdin.flush();child.wait(timeout=10)
    with pytest.raises(OSError):identity.process_token(0)
    from copy import deepcopy
    # Feed actual sampled tokens to the shared chain validator. Only the
    # structural worker command is a synthetic control, not service evidence.
    worker = {**actual, 'argv': ['python', 'smm_hub._archive.document_worker', '--task-token', 'a'*32]}
    ocr = {**actual, 'parent_pid': worker['pid']}
    kwargs = dict(sid=expected, session=current['session_id'], attempt_id='a'*32, ancestors=[current['pid']])
    identity.validate_chain(ocr, worker, current, **kwargs)
    for target, field, bad in [('ocr','sid','S-1-5-19'), ('worker','session_id',current['session_id']+1),
                               ('ocr','parent_pid',-1), ('worker','argv',['python','smm_hub._archive.document_worker','--task-token','b'*32])]:
        values = {'ocr':deepcopy(ocr),'worker':deepcopy(worker),'service':deepcopy(current)}
        # A controller could itself be LocalService; always choose a wrong SID.
        if field == 'sid' and bad == expected:bad='S-1-5-18'
        values[target][field]=bad
        with pytest.raises(AssertionError):identity.validate_chain(**values, **kwargs)
    with pytest.raises(AssertionError):identity.validate_chain(ocr,worker,current,**{**kwargs,'ancestors':[]})

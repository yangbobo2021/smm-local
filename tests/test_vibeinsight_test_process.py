"""Real descendants distinguish launcher exit from a completed test Hub stop."""
import json
import os
import subprocess
import sys

import psutil
import pytest

from document_formats_platform import process_tree, spawn_identity, utf8_environment, terminate_verified
from document_formats_exit_observer import waiting_for_owned_exit
from test_vibeinsight_sync import stop_enrolled_test_hub


@pytest.mark.parametrize('natural', [True, False])
def test_test_hub_stop_waits_for_real_descendants_and_preserves_foreign_process(natural):
    child_code = ('import psutil,sys,time\n'
                  'parent=psutil.Process(int(sys.argv[1]))\n'
                  'try:parent.wait(timeout=30)\n'
                  'except psutil.TimeoutExpired:pass\n') if natural else 'import time;time.sleep(40)'
    parent_code = ('import json,os,subprocess,sys\n'
                   'child=subprocess.Popen([sys.executable,"-B","-c",sys.argv[1],str(os.getpid())])\n'
                   'print(json.dumps({"pid":os.getpid(),"child":child.pid}),flush=True)\n'
                   'sys.stdin.buffer.read(1)\n')
    foreign = subprocess.Popen([sys.executable, '-B', '-c', 'import time;time.sleep(40)'])
    parent = subprocess.Popen([sys.executable, '-B', '-c', parent_code, child_code],
                              env=utf8_environment(os.environ), stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    seed = spawn_identity(psutil.Process(parent.pid))
    members = []
    try:
        value = json.loads(parent.stdout.readline())
        members = process_tree(seed)
        assert {value['pid'], value['child']} <= {r['pid'] for r in members}
        assert foreign.pid not in {r['pid'] for r in members}
        parent._smm_test_members = members
        if natural:
            receipt = stop_enrolled_test_hub(parent)
            assert receipt['remaining'] == []
        else:
            with pytest.raises(AssertionError, match='descendants did not exit'):
                stop_enrolled_test_hub(parent, timeout=.5)
        assert all(not waiting_for_owned_exit(r) for r in members)
        assert foreign.poll() is None
    finally:
        if parent.poll() is None:
            terminate_verified(members or process_tree(seed), owner=parent)
        parent.wait(timeout=5)
        parent.stdin.close()
        parent.stdout.close()
        parent.stderr.close()
        foreign.terminate()
        foreign.wait(timeout=5)

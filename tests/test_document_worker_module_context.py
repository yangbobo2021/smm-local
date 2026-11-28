"""A real site-disabled service parent can launch its document worker."""
import json
import os
from pathlib import Path
import subprocess
import sys

from document_helpers import observe


def test_site_disabled_parent_bootstraps_only_its_package_root(tmp_path):
    root = Path(__file__).resolve().parents[1]
    # A hostile cwd/PYTHONPATH module must not be used by the service worker.
    wrong = tmp_path / 'smm_local'
    wrong.mkdir()
    (wrong / '__init__.py').write_text("raise RuntimeError('wrong working-directory package')", encoding='utf-8')
    code = '''import json,subprocess,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from smm_local.document_supervisor import module_command
assert sys.flags.no_site==1
command=module_command('smm_local.document_worker','--task-token','a'*32,'--help')
child=subprocess.run(command,capture_output=True,timeout=15)
print(json.dumps({'argv':command,'returncode':child.returncode,'stdout':child.stdout.decode('utf-8'),'stderr':child.stderr.decode('utf-8')}))
'''
    parent = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(root / 'src')],
        cwd=tmp_path, env={**os.environ, 'PYTHONPATH': str(tmp_path)}, capture_output=True, timeout=25)
    observe('real-no-site-worker-module-context', {'parent_exit': parent.returncode,
        'parent_stdout': parent.stdout.decode('utf-8'), 'parent_stderr': parent.stderr.decode('utf-8')})
    assert parent.returncode == 0 and not parent.stderr
    child = json.loads(parent.stdout)
    assert child['returncode'] == 0 and not child['stderr'], child
    assert '--task-token' in child['stdout'] and 'wrong working-directory package' not in child['stdout']


def test_normal_parent_still_starts_real_module_entry(tmp_path):
    from smm_local.document_supervisor import module_command
    command = module_command('smm_local.document_worker', '--task-token', 'b' * 32, '--help')
    child = subprocess.run(command, capture_output=True, timeout=15)
    observe('normal-worker-module-context', {'argv': command, 'exit': child.returncode,
        'stdout': child.stdout.decode('utf-8'), 'stderr': child.stderr.decode('utf-8')})
    assert child.returncode == 0 and not child.stderr
    assert '--task-token' in child.stdout.decode('utf-8')

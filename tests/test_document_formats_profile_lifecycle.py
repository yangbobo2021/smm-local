"""A real weakref callback must not disable either acceptance observer."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/acceptance'))
from document_formats_guard_primitives import AUDIT_PRIMITIVES, IDENTITY_SOURCE
from document_formats_protocol_guards import HOOK
from document_formats_cross_os import RECEIVER_HOOK


@pytest.mark.parametrize('observer', ['protocol', 'receiver'])
def test_actual_weakref_callback_with_none_module_keeps_profile_active(tmp_path, observer):
    phase = tmp_path / 'phase.txt'
    phase.write_text('archive-only', encoding='utf-8')
    sources = tmp_path / 'sources.json'
    sources.write_text('[]', encoding='utf-8')
    wire = tmp_path / 'wire'
    wire.mkdir()
    config = {'log': str(tmp_path / 'observer.jsonl'), 'phase': str(phase), 'wire': str(wire),
        'sources': str(tmp_path / 'originals'), 'source_paths': str(sources),
        'expected_identity': {}, 'network_endpoints': [], 'listen_endpoints': [],
        'mcp_wrapper': str(tmp_path / 'unused-mcp.py'), 'mcp_argv': [], 'local_db': str(tmp_path / 'unused.sqlite3')}
    if observer == 'receiver':
        config['source_paths'] = []
    hook = HOOK if observer == 'protocol' else RECEIVER_HOOK
    code = 'import json\nC=json.loads(' + repr(json.dumps(config)) + ')\n' + IDENTITY_SOURCE + '\n' + AUDIT_PRIMITIVES + '\n' + hook
    script = '''import gc,json,weakref
from pathlib import Path
namespace={'__name__':'_smm_008_observer_control'}
exec(compile(CODE,'actual-observer.py','exec'),namespace)
marker=Path(MARKER)
closing_globals={'__name__':'closing_module','marker':marker}
exec(compile("def closed_module_callback(reference):\\n marker.write_text('completed',encoding='utf-8')\\n",'closing-module.py','exec'),closing_globals)
closing_globals['__name__']=None
class Target:pass
target=Target()
reference=weakref.ref(target,closing_globals['closed_module_callback'])
del target
gc.collect()
assert marker.read_text(encoding='utf-8')=='completed','actual weakref callback did not complete'
assert namespace['sys'].getprofile() is namespace['profile'],'observer was disabled by callback'
print(json.dumps({'callback_completed':True,'profile_still_active':True}))
'''.replace('CODE', repr(code)).replace('MARKER', repr(str(tmp_path / 'callback-completed')))
    process = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', script], capture_output=True, timeout=20)
    evidence = Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR', str(tmp_path / 'evidence'))) / ('profile-' + observer)
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'stdout').write_bytes(process.stdout)
    (evidence / 'stderr').write_bytes(process.stderr)
    (evidence / 'source.py').write_text(script, encoding='utf-8')
    assert process.returncode == 0, process.stderr.decode('utf-8', errors='replace')
    assert b'Exception ignored' not in process.stderr and not process.stderr
    assert json.loads(process.stdout) == {'callback_completed': True, 'profile_still_active': True}

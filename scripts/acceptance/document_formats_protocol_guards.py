"""Observation hooks for task-only copied installed environments.

No product module is modified. The hooks reject content work during reads and
retain real source opens, worker starts and interpreter identities.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HOOK = r'''
import ctypes,json,os,sys,threading,time
from pathlib import Path
def phase():return Path(C['phase']).read_text(encoding='utf-8').strip()
def emit(kind,**value):
 with Path(C['log']).open('a',encoding='utf-8') as out:out.write(json.dumps({'kind':kind,'pid':os.getpid(),'phase':phase(),'time':time.time(),'monotonic_ns':time.monotonic_ns(),**value},ensure_ascii=False)+'\n')
actor={'executable':sys.executable,'prefix':sys.prefix,'argv':sys.argv,'isolated':sys.flags.isolated,'utf8_mode':sys.flags.utf8_mode,'cwd':os.getcwd(),'path':os.environ.get('PATH')}
if os.name=='nt':
 from ctypes import wintypes as w
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);advapi=ctypes.WinDLL('advapi32',use_last_error=True)
 kernel.GetCurrentProcess.restype=w.HANDLE;advapi.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)];advapi.OpenProcessToken.restype=w.BOOL
 advapi.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)];advapi.GetTokenInformation.restype=w.BOOL
 advapi.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.LPWSTR)];advapi.ConvertSidToStringSidW.restype=w.BOOL
 kernel.CloseHandle.argtypes=[w.HANDLE];kernel.LocalFree.argtypes=[ctypes.c_void_p]
 token=w.HANDLE();assert advapi.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token))
 try:
  size=w.DWORD();advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size));buffer=ctypes.create_string_buffer(size.value)
  assert advapi.GetTokenInformation(token,1,buffer,size,ctypes.byref(size));sid=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_void_p)).contents.value;text=w.LPWSTR()
  assert advapi.ConvertSidToStringSidW(sid,ctypes.byref(text))
  try:actor['sid']=text.value
  finally:kernel.LocalFree(ctypes.cast(text,ctypes.c_void_p))
 finally:kernel.CloseHandle(token)
 actor['is_admin']=bool(ctypes.windll.shell32.IsUserAnAdmin())
else:actor.update(uid=os.getuid(),gid=os.getgid())
emit('identity',**actor)
protected=os.path.normcase(os.path.abspath(C['sources']))
def protected_source(path):
 if path==os.path.normcase(os.path.abspath(C['source_paths'])):return False
 if path==protected or path.startswith(protected+os.sep):return True
 values=json.loads(Path(C['source_paths']).read_text(encoding='utf-8'))
 return path in values
processing={'prepare','explicit-refresh','explicit-upload','lifecycle-refresh','lifecycle-update','resume-captured'}
source_allowed={'explicit-refresh','lifecycle-refresh','guard-source-positive'}
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
  if protected_source(path):
   allowed=phase() in source_allowed;emit('source-open',path=path,allowed=allowed)
   if not allowed:raise AssertionError('SMM008 read attempted original source')
 elif event=='subprocess.Popen':
  mode=phase();transport=False;requested=None;frame=sys._getframe()
  while frame is not None:
   if frame.f_code.co_filename==C['mcp_wrapper']:
    requested=frame.f_globals.get('argv')
    transport=isinstance(requested,list) and requested[0]==sys.executable and 'smm_local.mcp_server' in requested and '--db' in requested and requested[requested.index('--db')+1]==C['local_db']
    break
   frame=frame.f_back
  allowed=mode in processing or mode in {'service-control','cleanup'} or transport
  emit('transport-start' if transport else 'child-start',executable=args[0],argv=args[1],requested_argv=requested,allowed=allowed)
  if not allowed:raise AssertionError('SMM008 read attempted child process')
def profile(frame,event,arg):
 if event!='call':return
 module=frame.f_globals.get('__name__','');name=frame.f_code.co_name
 processing_call=(module in {'smm_local.document_processing','smm_hub._archive.document_processing'} and name in {'process','_process'}) or (module.startswith(('smm_local.document_formats.','smm_hub._archive.document_formats.')) and name in {'parse','intermediate','recognize'})
 if processing_call:
  allowed=phase() in processing;emit('content-processing',module=module,function=name,allowed=allowed)
  if not allowed:raise AssertionError('SMM008 read attempted content processing')
sys.addaudithook(audit);sys.setprofile(profile);threading.setprofile(profile)
'''


def install(probe):
    probe.source_paths = probe.out / 'protected-source-paths.json'
    probe.source_paths.write_text('[]\n', encoding='utf-8')
    receipts = []
    for owner in ('local', 'hub'):
        source_python = Path(probe.config[owner + '_python'])
        source_prefix = source_python.parent.parent
        target = probe.out / 'programs' / (owner + '-env')
        target.parent.mkdir(exist_ok=True)
        shutil.copytree(source_prefix, target, symlinks=True)
        python = target / source_python.relative_to(source_prefix)
        probe.config[owner + '_python'] = str(python)
        p = subprocess.run([str(python), '-I', '-X', 'utf8', '-c', 'import sysconfig;print(sysconfig.get_path("purelib"))'],
                           capture_output=True, text=True, encoding='utf-8', timeout=20)
        assert p.returncode == 0, p.stderr
        site = Path(p.stdout.strip())
        assert site.resolve().is_relative_to(target.resolve())
        hook = site / 'sitecustomize.py'
        assert not hook.exists(), 'task copy already has an unexpected startup hook'
        config = {'phase': str(probe.out / 'phase.txt'), 'sources': str(probe.fixtures),
                  'source_paths': str(probe.source_paths),
                  'log': str(probe.out / (owner + '-protocol-guard.jsonl')),
                  'mcp_wrapper': str(Path(__file__).with_name('local_documents_mcp_worker.py').resolve()),
                  'local_db': str(probe.db['a'])}
        code = 'import json\nC=json.loads(' + repr(json.dumps(config)) + ')\n' + HOOK
        hook.write_text(code, encoding='utf-8')
        receipts.append({'owner': owner, 'source_prefix': str(source_prefix), 'private_copy': str(target),
                         'python': str(python), 'hook': str(hook), 'hook_sha256': hashlib.sha256(hook.read_bytes()).hexdigest(),
                         'scope': 'task-only environment copy; product assets independently checked against original wheel'})
    probe.save('protocol-guard-installation', receipts)


def events(probe):
    return sorted([json.loads(line) for owner in ('local', 'hub')
                   for line in (probe.out / (owner + '-protocol-guard.jsonl')).read_text(encoding='utf-8').splitlines()],
                  key=lambda event: event['monotonic_ns'])


def assert_read_only(probe, start):
    actual = events(probe)[start:]
    denied_kinds = {'source-open', 'content-processing', 'child-start'}
    assert not [e for e in actual if e['kind'] in denied_kinds], actual
    probe.save('read-only-observation-' + str(start), {'events': actual, 'unexpected_content_work': []})


def controls(probe):
    allowed = probe.out / 'allowed-control.bin'
    allowed.write_bytes(b'independent allowed bytes')
    for owner in ('local', 'hub'):
        protected_paths = [next(i['path'] for i in probe.items if i['role'] == ('a' if owner == 'local' else 'hub') and i['acquisition'] == kind)
                           for kind in ('path', 'chooser')]
        python = probe.config[owner + '_python']
        module = 'smm_local.document_processing' if owner == 'local' else 'smm_hub._archive.document_processing'
        for index, protected in enumerate(protected_paths):
            probe.phase = 'guard-source-positive'
            p = subprocess.run([python, '-I', '-X', 'utf8', '-c', 'from pathlib import Path;import sys;assert Path(sys.argv[1]).read_bytes()', str(protected)], capture_output=True, timeout=20)
            assert p.returncode == 0, p.stderr
            probe.keep('guards/' + owner + '-source-positive-' + str(index) + '.stdout', p.stdout)
            probe.keep('guards/' + owner + '-source-positive-' + str(index) + '.stderr', p.stderr)
            probe.phase = 'read-only'
            before = len(events(probe))
            p = subprocess.run([python, '-I', '-X', 'utf8', '-c', 'from pathlib import Path;import sys;Path(sys.argv[1]).read_bytes()', str(protected)], capture_output=True, timeout=20)
            probe.keep('guards/' + owner + '-source-negative-' + str(index) + '.stdout', p.stdout)
            probe.keep('guards/' + owner + '-source-negative-' + str(index) + '.stderr', p.stderr)
            assert p.returncode != 0 and b'SMM008 read attempted original source' in p.stderr
            actual = [e for e in events(probe)[before:] if e['kind'] != 'identity']
            assert len(actual) == 1 and actual[0]['kind'] == 'source-open' and actual[0]['allowed'] is False
        probe.phase = 'read-only'
        positive = subprocess.run([python, '-I', '-X', 'utf8', '-c', 'from pathlib import Path;import sys;assert Path(sys.argv[1]).read_bytes()==b"independent allowed bytes"', str(allowed)], capture_output=True, timeout=20)
        assert positive.returncode == 0, positive.stderr
        for code, marker in [('from ' + module + ' import process;process(None,None)', 'content processing'),
                             ('import subprocess,sys;subprocess.run([sys.executable,"-c","pass"])', 'child process')]:
            before = len(events(probe))
            p = subprocess.run([python, '-I', '-X', 'utf8', '-c', code, str(protected)], capture_output=True, timeout=20)
            probe.keep('guards/' + owner + '-' + marker.replace(' ', '-') + '.stdout', p.stdout)
            probe.keep('guards/' + owner + '-' + marker.replace(' ', '-') + '.stderr', p.stderr)
            assert p.returncode != 0 and ('SMM008 read attempted ' + marker).encode() in p.stderr
            actual = [e for e in events(probe)[before:] if e['kind'] != 'identity']
            assert len(actual) == 1 and actual[0]['allowed'] is False
    probe.save('protocol-guard-controls', {'owners': ['local', 'hub'], 'actual_allowed_source_and_cache': True,
                                        'actual_source_processing_child_denied_per_owner': 4,
                                        'source_classes': ['external path', 'managed upload path']})

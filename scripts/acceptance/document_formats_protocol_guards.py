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
import inspect

from document_formats_guard_primitives import AUDIT_PRIMITIVES, IDENTITY_SOURCE, actual_identity

def resume_task_matches(module, name, capture, argv, aid):
    if module in {'smm_local.document_processing','smm_hub._archive.document_processing'} and name in {'process','_process'}:
        return isinstance(capture,dict) and capture.get('attempt_id')==aid
    return '--task-token' in argv and argv[argv.index('--task-token')+1:argv.index('--task-token')+2]==[aid]


HOOK = inspect.getsource(resume_task_matches) + r'''
import ctypes,hashlib,json,os,socket,sys,threading,time
from pathlib import Path
def phase():return Path(C['phase']).read_text(encoding='utf-8').strip()
def emit(kind,**value):
 with Path(C['log']).open('a',encoding='utf-8') as out:out.write(json.dumps({'kind':kind,'owner':C.get('owner'),'pid':os.getpid(),'phase':phase(),'time':time.time(),'monotonic_ns':time.monotonic_ns(),**value},ensure_ascii=False,default=str)+'\n')
actor={'executable':sys.executable,'prefix':sys.prefix,'argv':sys.argv,'isolated':sys.flags.isolated,'utf8_mode':sys.flags.utf8_mode,'cwd':os.getcwd(),'path':os.environ.get('PATH')}
actor.update(actual_identity())
for field in ('sid','session_id','euid','egid'):
 if field in C['expected_identity']:assert actor[field]==C['expected_identity'][field],('wrong product process identity',field,actor)
emit('identity',**actor)
protected=os.path.normcase(os.path.abspath(C['sources']))
def protected_source(path):
 if path==os.path.normcase(os.path.abspath(C['source_paths'])):return False
 if path==protected or path.startswith(protected+os.sep):return True
 values=json.loads(Path(C['source_paths']).read_text(encoding='utf-8'))
 return path in values
processing={'prepare','explicit-refresh','explicit-upload','lifecycle-refresh','lifecycle-update','resume-captured','conversation-import'}
source_allowed={'explicit-refresh','lifecycle-refresh','guard-source-positive','conversation-import'}
network_endpoints={tuple(endpoint) for endpoint in C['network_endpoints']}
def audit(event,args):
 if event=='http.client.send':
  data=args[1]
  if not isinstance(data,(bytes,bytearray,memoryview)):raise AssertionError('unobserved HTTP client payload representation')
  raw=bytes(data);digest=hashlib.sha256(raw).hexdigest();target=Path(C['wire'])/digest
  if not target.exists():
   temporary=target.with_name(digest+'.'+str(os.getpid())+'.'+str(threading.get_ident())+'.tmp')
   with temporary.open('xb') as out:out.write(raw)
   temporary.replace(target)
  else:assert target.read_bytes()==raw
  emit('http-send',sha256=digest,bytes=len(raw),host=args[0].host,port=args[0].port)
 elif event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
  if protected_source(path):
   allowed=phase() in source_allowed;emit('source-open',path=path,allowed=allowed)
   if not allowed:raise AssertionError('SMM008 read attempted original source')
 elif event in NETWORK_EVENTS:
  allowed,internal,local_name,address,reply=network_decision(event,args,sys._getframe(1),network_endpoints,network_endpoints)
  emit('network-call',event=event,address=address,internal_socketpair=internal,local_name_metadata=local_name,server_reply=reply,allowed=allowed)
  if not allowed:raise AssertionError('SMM008 attempted network outside configured task endpoints')
 elif event in PROCESS_EVENTS:
  mode=phase();transport=False;requested=None
  effective,validation_source=effective_process_arguments(event,args,sys._getframe(1));frame=sys._getframe()
  while frame is not None:
   if frame.f_code.co_filename==C['mcp_wrapper']:
    requested=frame.f_globals.get('argv')
    transport=(isinstance(requested,list) and requested==C['mcp_argv'] and bool(requested)
               and same_image(requested[0],sys.executable)
               and 'smm_local.mcp_server' in requested and requested.count('--db')==1
               and same_image(requested[requested.index('--db')+1],C['local_db'])
               and exact_child_command(event,effective,requested))
    break
   frame=frame.f_back
  allowed=mode in processing or mode in {'service-control','cleanup'} or transport
  emit('transport-start' if transport else 'child-start',event=event,executable=args[0] if args else None,argv=args[1] if len(args)>1 else None,requested_argv=requested,validation_source=validation_source,effective_arguments=effective,allowed=allowed)
  if not allowed:raise AssertionError('SMM008 read attempted child process')
def profile(frame,event,arg):
 if event!='call':return
 module=frame.f_globals.get('__name__') or '';name=frame.f_code.co_name
 processing_call=(module in {'smm_local.document_processing','smm_hub._archive.document_processing'} and name in {'process','_process'}) or (module.startswith(('smm_local.document_formats.','smm_hub._archive.document_formats.')) and name in {'parse','intermediate','recognize'})
 if processing_call:
  allowed=phase() in processing
  resume_path=C.get('resume_attempt');resume=Path(resume_path).read_text().strip() if resume_path else ''
  if resume:allowed=allowed and resume_task_matches(module,name,frame.f_locals.get('capture'),sys.argv,resume)
  emit('content-processing',module=module,function=name,allowed=allowed)
  if not allowed:raise AssertionError('SMM008 read attempted content processing')
sys.addaudithook(audit);sys.setprofile(profile);threading.setprofile(profile)
'''


def install(probe, owners=('local', 'hub')):
    probe.source_paths = probe.out / 'protected-source-paths.json'
    probe.source_paths.write_text('[]\n', encoding='utf-8')
    receipts = []
    wire = probe.out / 'actual-outbound-http'
    wire.mkdir()
    probe.resume_attempt_path=probe.out/'current-resume-attempt.txt'
    probe.resume_attempt_path.write_text('')
    assert owners and set(owners) <= {'local', 'hub'}
    for owner in owners:
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
        hook = site / '_smm_008_private_acceptance.py'
        startup = site / '_smm_008_private_acceptance.pth'
        assert not hook.exists() and not startup.exists(), 'task copy already has this acceptance hook'
        config = {'owner': owner, 'phase': str(probe.out / 'phase.txt'), 'sources': str(probe.fixtures),
                  'source_paths': str(probe.source_paths),
                  'log': str(probe.out / (owner + '-protocol-guard.jsonl')),
                  'wire': str(wire), 'resume_attempt':str(probe.resume_attempt_path),
                  'mcp_wrapper': str(Path(__file__).with_name('local_documents_mcp_worker.py').resolve()),
                  'local_db': str(probe.db['a']),
                  'mcp_argv': list(map(str,probe.argv('a','smm_local.mcp_server','--db',probe.db['a']))),
                  'network_endpoints': [['127.0.0.1', port] for port in probe.ports.values()],
                  'expected_identity': probe.config.get(owner+'_expected_identity',actual_identity())}
        code = 'import json\nC=json.loads(' + repr(json.dumps(config)) + ')\n' + IDENTITY_SOURCE + '\n' + AUDIT_PRIMITIVES + '\n' + HOOK
        hook.write_text(code, encoding='utf-8')
        # Some base interpreters provide a stdlib sitecustomize which precedes
        # the venv on sys.path. A unique task-only .pth import avoids shadowing
        # either that existing module or this observer, including under -I.
        startup.write_text('import _smm_008_private_acceptance\n', encoding='utf-8')
        check = ('import json,sys,_smm_008_private_acceptance as observer;'
                 'print(json.dumps({"file":observer.__file__,"isolated":sys.flags.isolated}))')
        loaded = subprocess.run([str(python), '-I', '-X', 'utf8', '-c', check],
                                capture_output=True, timeout=20)
        probe.keep('guards/' + owner + '-startup.stdout', loaded.stdout)
        probe.keep('guards/' + owner + '-startup.stderr', loaded.stderr)
        assert loaded.returncode == 0 and not loaded.stderr, loaded.stderr
        actual = json.loads(loaded.stdout)
        assert Path(actual['file']).resolve() == hook.resolve() and actual['isolated'] == 1
        assert Path(config['log']).is_file() and json.loads(Path(config['log']).read_text().splitlines()[0])['kind']=='identity'
        receipts.append({'owner': owner, 'source_prefix': str(source_prefix), 'private_copy': str(target),
                         'python': str(python), 'hook': str(hook), 'hook_sha256': hashlib.sha256(hook.read_bytes()).hexdigest(),
                         'startup': str(startup), 'startup_sha256': hashlib.sha256(startup.read_bytes()).hexdigest(),
                         'actual_isolated_startup': actual,
                         'scope': 'task-only environment copy; product assets independently checked against original wheel'})
    probe.save('protocol-guard-installation', receipts)


def events(probe, *, require_complete=False):
    import threading
    paths = getattr(probe, 'protocol_guard_paths', None)
    if paths is None:paths = [probe.out / (owner + '-protocol-guard.jsonl') for owner in ('local', 'hub')]
    if not hasattr(probe,'_protocol_event_lock'):
        probe._protocol_event_lock=threading.RLock()
        probe._protocol_event_positions={}
        probe._protocol_event_cache=[]
    with probe._protocol_event_lock:
        new,positions=[],{}
        for value in paths:
            path=Path(value)
            with path.open('rb') as stream:
                stat=os.fstat(stream.fileno())
                previous=probe._protocol_event_positions.get(str(path))
                offset=previous['offset'] if previous else 0
                assert stat.st_size>=offset,'observer log truncated'
                if previous:assert (stat.st_dev,stat.st_ino)==previous['identity'],'observer log replaced'
                stream.seek(offset);raw=stream.read()
            end=raw.rfind(b'\n')+1
            if require_complete:assert end==len(raw),('incomplete observer record after shutdown',str(path),len(raw)-end)
            new.extend(json.loads(line) for line in raw[:end].decode('utf-8').splitlines())
            positions[str(path)]={'offset':offset+end,'identity':(stat.st_dev,stat.st_ino)}
        # A completed record arriving after another file was sampled must not
        # be sorted back into the already-consumed prefix of a count cursor.
        probe._protocol_event_cache.extend(sorted(new,key=lambda event:event['monotonic_ns']))
        probe._protocol_event_positions.update(positions)
        return list(probe._protocol_event_cache)


def assert_read_only(probe, start):
    actual = events(probe)[start:]
    denied_kinds = {'source-open', 'content-processing', 'child-start'}
    assert not [e for e in actual if e['kind'] in denied_kinds], actual
    assert not [e for e in actual if e['kind']=='network-call' and not e['allowed']], actual
    probe.save('read-only-observation-' + str(start), {'events': actual, 'unexpected_content_work': []})


def control_observations(probe, start, owner, argv):
    """Separate this real -c interpreter from already-running service traffic."""
    window = events(probe)[start:]
    identities = [event for event in window if event['kind']=='identity' and event['owner']==owner
                  and event['argv']==argv]
    assert len(identities)==1, identities
    identity = identities[0]
    assert identity['isolated']==1 and identity['utf8_mode']==1
    expected=probe.config.get(owner+'_expected_identity')
    if expected is None:expected=actual_identity()
    for field in ('sid','session_id','euid','egid','is_admin'):
        if field in expected:assert identity[field]==expected[field]
    python=Path(probe.config[owner+'_python'])
    assert os.path.normcase(os.path.abspath(identity['executable']))==os.path.normcase(os.path.abspath(python))
    assert Path(identity['prefix']).resolve()==python.parent.parent.resolve()
    own = [event for event in window if event['pid']==identity['pid'] and event['owner']==owner]
    # Legitimate configured-Hub HTTP can continue in a live service. Keep all
    # original events; another process doing forbidden work is still failure.
    foreign = [event for event in window if event not in own and
               (event['kind'] in {'source-open','content-processing','child-start'} or
                (event['kind']=='network-call' and not event['allowed']))]
    assert not foreign, foreign
    return own


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
            actual = [e for e in control_observations(probe, before, owner, ['-c', str(protected)]) if e['kind'] != 'identity']
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
            actual = [e for e in control_observations(probe, before, owner, ['-c', str(protected)]) if e['kind'] != 'identity']
            expected_kind='content-processing' if marker=='content processing' else 'child-start'
            assert len(actual) == 1 and actual[0]['kind']==expected_kind and actual[0]['allowed'] is False
        child_controls = [('system', 'import os;os.system("exit 0" if os.name=="nt" else ":")'),
            ('spawn', 'import os,sys;os.spawnv(os.P_WAIT,sys.executable,[sys.executable,"-c","pass"])'),
            ('mcp-actual-mismatch', 'import _smm_008_private_acceptance as g,sys;namespace={"argv":g.C["mcp_argv"],"sys":sys};exec(compile("import subprocess\\nsubprocess.run([sys.executable,\\"-I\\",\\"-c\\",\\"print(73428)\\"])" ,g.C["mcp_wrapper"],"exec"),namespace)')]
        if hasattr(os, 'posix_spawn'):
            child_controls.append(('posix-spawn', 'import os,sys;pid=os.posix_spawn(sys.executable,[sys.executable,"-c","pass"],os.environ);os.waitpid(pid,0)'))
        for name, code in child_controls:
            before = len(events(probe))
            denied = subprocess.run([python, '-I', '-X', 'utf8', '-c', code], capture_output=True, timeout=20)
            probe.keep('guards/' + owner + '-child-' + name + '.stdout', denied.stdout)
            probe.keep('guards/' + owner + '-child-' + name + '.stderr', denied.stderr)
            assert denied.returncode != 0 and b'SMM008 read attempted child process' in denied.stderr, (name, denied.stderr)
            observed = [e for e in control_observations(probe, before, owner, ['-c']) if e['kind'] == 'child-start']
            assert len(observed) == 1 and observed[0]['allowed'] is False
        # Real socketpair must remain available to asyncio/stdio on Windows;
        # no blanket loopback whitelist is used for application connections.
        pair = subprocess.run([python, '-I', '-X', 'utf8', '-c',
            'import socket;a,b=socket.socketpair();a.sendall(b"pair");assert b.recv(4)==b"pair";a.close();b.close()'],
            capture_output=True, timeout=20)
        probe.keep('guards/' + owner + '-socketpair.stdout', pair.stdout)
        probe.keep('guards/' + owner + '-socketpair.stderr', pair.stderr)
        assert pair.returncode == 0, pair.stderr
        import socket
        with socket.socket() as temporary:
            temporary.bind(('127.0.0.1', 0)); blocked_port = temporary.getsockname()[1]
        assert blocked_port not in probe.ports.values()
        for name, code in (
            ('dns', 'import socket;socket.getaddrinfo("models.example.invalid",443)'),
            ('connect', 'import socket;socket.socket().connect(("127.0.0.1",' + str(blocked_port) + '))'),
            ('connect-ex', 'import socket;socket.socket().connect_ex(("127.0.0.1",' + str(blocked_port) + '))'),
            ('sendto', 'import socket;socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b"blocked",("127.0.0.1",' + str(blocked_port) + '))'),
        ):
            before = len(events(probe))
            denied = subprocess.run([python, '-I', '-X', 'utf8', '-c', code], capture_output=True, timeout=20)
            probe.keep('guards/' + owner + '-network-' + name + '.stdout', denied.stdout)
            probe.keep('guards/' + owner + '-network-' + name + '.stderr', denied.stderr)
            assert denied.returncode != 0 and b'SMM008 attempted network outside configured task endpoints' in denied.stderr
            observed = [e for e in control_observations(probe, before, owner, ['-c']) if e['kind']=='network-call']
            assert len(observed) == 1 and observed[0]['allowed'] is False
    probe.save('protocol-guard-controls', {'owners': ['local', 'hub'], 'actual_allowed_source_and_cache': True,
                                        'actual_source_processing_child_denied_per_owner': 4,
                                        'source_classes': ['external path', 'managed upload path']})

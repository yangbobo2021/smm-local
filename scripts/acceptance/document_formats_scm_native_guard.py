"""Protected, task-only dual-role observer for genuine SCM H acceptance.

Administrator maintenance is observable, but only LocalService may execute
content processing or start a document worker/OCR process. Normal E rules are
unchanged. No product module or processing return value is substituted.
"""
from pathlib import Path
import hashlib
import inspect
import json
import subprocess

from document_formats_protocol_guards import HOOK, resume_task_matches
from document_formats_guard_primitives import IDENTITY_SOURCE, AUDIT_PRIMITIVES


def install(manager):
    shared = manager.out / 'native-observation'
    shared.mkdir()
    manager.native_shared = shared
    for name, raw in [('phase.txt','prepare'),('sources.json','[]')]:
        (shared / name).write_text(raw, encoding='utf-8')
    (shared/'wire').mkdir()
    (shared/'hub-guard.jsonl').touch()
    manager.run('native-observation-acl', ['icacls.exe', shared, '/inheritance:r', '/grant:r',
        '*S-1-5-32-544:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-19:(OI)(CI)M','*S-1-5-32-545:(OI)(CI)RX'])
    # Base administrator source reads remain limited to explicit captures.
    actor = manager.actor()
    import document_formats_guard_primitives as primitives
    admin = primitives.actual_identity()
    expected = {'sid': admin['sid'], 'session_id': admin['session_id']}
    config = {'owner':'hub','phase':str(shared/'phase.txt'),'sources':str(manager.out/'ordinary-client/platform/资料 空格'),
        'source_paths':str(shared/'sources.json'),'log':str(shared/'hub-guard.jsonl'),'wire':str(shared/'wire'),
        'mcp_wrapper':'__not_a_hub_mcp_transport__','mcp_argv':[], 'local_db':'__none__',
        'network_endpoints':[['127.0.0.1',manager.ports['hub']]], 'expected_identity':expected,
        'ocr_executable':manager.materials['ocr_executable'],
        'ocr_data_dirs':[manager.materials['ocr_data_dir'],str(shared/'languages')],
        'storage_ancestor':str(manager.storage_ancestor),
        'storage_root':str(manager.hub_state),
        'resume_attempt':str(shared/'resume-attempt.txt')}
    (shared/'resume-attempt.txt').write_text('')
    original = "for field in ('sid','session_id','euid','egid'):\n if field in C['expected_identity']:assert actor[field]==C['expected_identity'][field],('wrong product process identity',field,actor)"
    replacement = "service_actor=actor.get('sid')=='S-1-5-19' and actor.get('session_id')==0\nmaintenance_actor=all(actor.get(k)==v for k,v in C['expected_identity'].items())\nassert service_actor or maintenance_actor,('unexpected native actor',actor)"
    assert original in HOOK
    hook = HOOK.replace(original, replacement)
    needle = "allowed=mode in processing or mode in {'service-control','cleanup'} or transport"
    assert needle in hook
    hook = hook.replace(needle, needle + "\n  invocation=native_argv(effective[1]) if effective is not None and len(effective)>1 else []\n  worker_command=any('document_worker' in str(v) or 'document_watchdog' in str(v) for v in invocation)\n  ocr_command=bool(invocation) and 'tesseract' in str(invocation[0]).lower()\n  maintenance_probe=bool(invocation) and same_image(invocation[0],C['ocr_executable']) and (invocation[1:]==['--version'] or (len(invocation)==4 and invocation[1]=='--tessdata-dir' and invocation[3]=='--list-langs' and any(same_image(invocation[2],p) for p in C['ocr_data_dirs'])))\n  if worker_command or (ocr_command and not maintenance_probe):\n   if not service_actor:emit('native-role-denial',invocation=invocation)\n   assert service_actor,('administrator attempted business processing child',invocation)")
    needle = "allowed=phase() in processing\n"
    assert needle in hook
    hook = hook.replace(needle, "allowed=phase() in processing and service_actor\n")
    value = subprocess.run([manager.config['hub_python'],'-I','-c','import sysconfig;print(sysconfig.get_path("purelib"))'],capture_output=True,timeout=20)
    assert value.returncode==0,value.stderr
    site = Path(value.stdout.decode().strip())
    assert site.resolve().is_relative_to(Path(manager.config['hub_python']).parent.parent.resolve())
    module = site/'_smm_008_native_guard.py';startup=site/'_smm_008_native_guard.pth'
    assert not module.exists() and not startup.exists()
    code = 'import json\nC=json.loads('+repr(json.dumps(config))+')\n'+IDENTITY_SOURCE+'\n'+AUDIT_PRIMITIVES+'\n'+hook
    code += '''
if service_actor:
 import ctypes as _c
 from ctypes import wintypes as _w
 _k=_c.WinDLL('kernel32',use_last_error=True)
 _k.CreateFileW.argtypes=[_w.LPCWSTR,_w.DWORD,_w.DWORD,_c.c_void_p,_w.DWORD,_w.DWORD,_w.HANDLE]
 _k.CreateFileW.restype=_w.HANDLE
 _k.CloseHandle.argtypes=[_w.HANDLE]
 _results=[]
 for _name,_path,_access,_denied in [('ancestor-list',C['storage_ancestor'],1,True),
    ('ancestor-security',C['storage_ancestor'],0x20000,True),
    ('state-list-and-security',C['storage_root'],0x20081,False)]:
  _handle=_k.CreateFileW(_path,_access,7,None,3,0x02200000,None)
  _failed=_handle==_c.c_void_p(-1).value
  _error=_c.get_last_error() if _failed else 0
  if not _failed:_k.CloseHandle(_handle)
  _results.append({'check':_name,'desired_access':_access,'denied':_failed,'winerror':_error})
 emit('native-storage-ancestor-control',checks=_results,identity=actor)
 assert all(row['denied']==(row['check']!='state-list-and-security') and
    (not row['denied'] or row['winerror']==5) for row in _results),_results
'''
    module.write_text(code,encoding='utf-8');startup.write_text('import _smm_008_native_guard\n',encoding='utf-8')
    manager.config['native_observation']={'root':str(shared),'log':str(shared/'hub-guard.jsonl'),
        'maintenance_identity':expected,'service_name':'smm-hub-'+hashlib.sha256(str(manager.hub_state.resolve()).encode()).hexdigest()[:12]}
    manager.save('native-guard-installation',{'hook':str(module),'hook_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),
        'startup':str(startup),'startup_sha256':hashlib.sha256(startup.read_bytes()).hexdigest(),
        'config':config,'maintenance_identity':actor,'scope':'actual maintenance allowed; actual content processing restricted to LocalService19/session0'})


def validate_storage_access(observations, *, service_name, state):
    """A .pth import error may be printed and swallowed: require every receipt."""
    identities=[(index,event) for index,event in enumerate(observations)
        if event['kind']=='identity' and event['owner']=='hub' and event.get('sid')=='S-1-5-19'
        and event.get('session_id')==0]
    assert identities,'No actual LocalService startup identity'
    accepted=[];main=False;worker=False
    for index,identity in identities:
        end=next((offset for offset,event in enumerate(observations[index+1:],index+1)
            if event['kind']=='identity' and event['pid']==identity['pid'] and event['owner']=='hub'),len(observations))
        controls=[event for event in observations[index+1:end]
            if event['kind']=='native-storage-ancestor-control' and event['owner']=='hub' and event['pid']==identity['pid']]
        assert len(controls)==1,('Missing/duplicate service-process storage access receipt',identity,controls)
        control=controls[0]
        for field in ('sid','session_id','argv','executable','prefix','cwd'):
            assert control['identity'][field]==identity[field],(field,identity,control)
        assert control['checks']==[
            {'check':'ancestor-list','desired_access':1,'denied':True,'winerror':5},
            {'check':'ancestor-security','desired_access':0x20000,'denied':True,'winerror':5},
            {'check':'state-list-and-security','desired_access':0x20081,'denied':False,'winerror':0}],control
        main|=identity['argv']==['-c',service_name,str(state)]
        worker|='smm_hub._archive.document_worker' in identity['argv']
        accepted.append({'startup_identity':identity,'actual_control':control})
    assert main and worker,'Both actual SCM service and actual document worker controls are required'
    return accepted

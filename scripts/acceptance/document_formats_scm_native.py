"""Dedicated actual Windows SCM H1-H5, with a separate standard Local/browser.

Only fixed task maintenance and verified current-task faults use administrator
RPC. Content is processed by the stock protected LocalService service.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'tests')]
import hub_documents_scm_platform as scm
from document_formats_scm_formats import FormatsAdministrator, FormatsClient
from document_formats_windows_identity import sample_process
from document_formats_upload_transport import upload,wait,rows
from document_formats_installed_lifecycle import snapshot,library_entry,retry,unchanged_publication,reject_old
from document_formats_protocol_guards import events,assert_read_only
from hub_documents_platform import Probe,now


def identifier(value):
    assert isinstance(value,str) and re.fullmatch('[0-9a-f]{32}',value)
    return value


def cli_arguments(args, child_output):
    """Accept canonical, nonduplicated task maintenance arguments only."""
    assert isinstance(args,list) and len(args)>=2 and all(isinstance(a,str) for a in args)
    assert args[0] in {'documents','project'}
    action=args[1]
    schemas={
        ('project','list'):(0,{}),('project','ensure-global'):(0,{}),('project','create'):(1,{}),
        ('documents','sources'):(0,{}),('documents','files'):(0,{'--source-id':'id'}),
        ('documents','add'):(1,{'--project-id':'int'}),('documents','refresh'):(0,{'--source-id':'id'}),
        ('documents','set'):(1,{'--project-id':'int'}),('documents','remove'):(1,{}),
        ('documents','search'):(1,{'--scope':'scope','--project-id':'int','--limit':'int'}),
        ('documents','read'):(0,{'--reference':'text','--view':'view','--start':'int','--end':'int','--table-id':'text',
            '--row-start':'int','--row-end':'int','--column-start':'int','--column-end':'int','--original-output':'output'}),
        ('documents','reprocess'):(0,{'--document-id':'id','--capture-id':'id','--expected-attempt-id':'id',
            '--expected-version':'int','--expected-processing-version':'int'}),
    }
    key=tuple(args[:2]);assert key in schemas
    count,schema=schemas[key];assert len(args)>=2+count
    positional=args[2:2+count];tail=args[2+count:];assert len(tail)%2==0
    flags={}
    for flag,value in zip(tail[::2],tail[1::2],strict=True):
        assert flag in schema and flag not in flags and not value.startswith('--')
        kind=schema[flag]
        if kind=='id':identifier(value)
        elif kind=='int':assert value.isdigit()
        elif kind=='scope':assert value=='project'
        elif kind=='view':assert value in {'text','table','original-info'}
        elif kind=='output':
            path=Path(value)
            assert path.is_absolute() and path.parent.absolute()==child_output.absolute()
            assert not child_output.is_symlink() and not child_output.is_junction()
            assert not path.is_symlink()
        flags[flag]=value
    required={('documents','add'):{'--project-id'},('documents','refresh'):{'--source-id'},
        ('documents','set'):{'--project-id'},('documents','read'):{'--reference'},
        ('documents','search'):{'--scope','--project-id','--limit'},
        ('documents','reprocess'):set(schemas[('documents','reprocess')][1])}
    assert required.get(key,set())<=flags.keys()
    if key==('documents','add'):
        assert Path(positional[0]).resolve()==(child_output/'资料 空格/native-path.docx').resolve()
    elif key in {('documents','set'),('documents','remove')}:identifier(positional[0])
    return args


class NativeAdministrator(FormatsAdministrator):
    def __init__(self,config,output):
        super().__init__(config,output)
        # LocalService may traverse an administrator's parent directory
        # without being allowed to list it or read its security descriptor.
        # Exercise that real boundary; never broaden ancestor permissions to
        # accommodate the product's private snapshot directory implementation.
        parent=self.out/'traverse-only-state';parent.mkdir()
        state=parent/'hub'
        self.hub_state.rename(state)
        self.hub_state=state;self.hub_db=state/'smm-hub.sqlite3'
        self.storage_ancestor=parent
        self.run('protect-storage-ancestor',['icacls.exe',parent,'/inheritance:r','/grant:r',
            '*S-1-5-32-544:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-19:(X,RA)'])
        self.client_timeout_seconds=1800
        from document_formats_scm_native_guard import install
        install(self)
        self.private_data=self.native_shared/'languages'
        self.private_data.mkdir()
        self.restore_languages()
        self.fault_raw=self.native_shared/'fault.docx'
        from document_formats_fixtures import docx_fixture
        self.fault_raw.write_bytes(docx_fixture('NATIVESCMPARSERFAULT')[0])
        self.gate=self.native_shared/'gate';self.gate.mkdir()
        self.cli_outputs=self.native_shared/'cli-originals';self.cli_outputs.mkdir()
        self.run('protect-cli-original-outputs',['icacls.exe',self.cli_outputs,'/inheritance:r','/grant:r',
            '*S-1-5-32-544:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-545:(OI)(CI)RX'])
        self.install_gate()
        self.guard_controls()

    def guard_controls(self):
        code="""import json,subprocess,sys
from smm_hub._archive.document_formats.word import parse
blocked=[]
try:parse(b'', '0'*64,{})
except AssertionError:blocked.append('administrator-parser')
try:subprocess.run([sys.executable,'-I','-m','smm_hub._archive.document_worker','--task-token','0'*32],check=True)
except AssertionError:blocked.append('administrator-worker')
assert blocked==['administrator-parser','administrator-worker'],blocked
for args in [[sys.argv[1],'--version'],[sys.argv[1],'--tessdata-dir',sys.argv[2],'--list-langs']]:
 result=subprocess.run(args,capture_output=True);assert result.returncode==0,result.stderr
print(json.dumps({'blocked':blocked,'exact_real_maintenance_probes':2}))
"""
        output=self.run('native-guard-actual-administrator-controls',
            [self.config['hub_python'],'-I','-X','utf8','-c',code,self.materials['ocr_executable'],self.private_data],role='hub')
        value=json.loads(output);assert value['exact_real_maintenance_probes']==2
        self.save('native-guard-controls',value)
        protected=self.native_shared/'case-source-control.bin';protected.write_bytes(b'independent case-source bytes')
        self.child_output=self.out/'ordinary-client/platform'
        self.source_registry([str(protected).swapcase()])
        probe="""from pathlib import Path
import json,sys
blocked=False
try:Path(sys.argv[1]).read_bytes()
except AssertionError as error:
 assert 'original source' in str(error);blocked=True
assert blocked
print(json.dumps({'case_equivalent_source_read_rejected':True}))
"""
        (self.native_shared/'phase.txt').write_text('read-only')
        try:
            raw=self.run('native-guard-case-source-negative',
                [self.config['hub_python'],'-I','-X','utf8','-c',probe,str(protected)],role='hub')
            assert json.loads(raw)['case_equivalent_source_read_rejected']
        finally:
            (self.native_shared/'phase.txt').write_text('prepare');self.source_registry([])

    def restore_languages(self):
        for language in ('chi_sim','eng'):
            shutil.copyfile(Path(self.materials['ocr_data_dir'])/(language+'.traineddata'),self.private_data/(language+'.traineddata'))

    def install_gate(self):
        site=Path(subprocess.check_output([self.config['hub_python'],'-I','-c','import sysconfig;print(sysconfig.get_path("purelib"))']).decode().strip())
        code=(ROOT/'tests/document_formats_lifecycle_hook.py').read_bytes()
        module=site/'_smm_008_native_fault.py';startup=site/'_smm_008_native_fault.pth'
        assert not module.exists() and not startup.exists()
        module.write_bytes(code)
        raw=str(self.hub_state/'.document-snapshots/raw'/hashlib.sha256(self.fault_raw.read_bytes()).hexdigest())
        startup.write_text('import _smm_008_native_fault; _smm_008_native_fault.install('+repr(str(self.gate))+','+repr([raw])+',[])\n',encoding='utf-8')
        self.save('native-fault-installation',{'module':str(module),'sha256':hashlib.sha256(code).hexdigest(),
            'gate':str(self.gate),'raw_sha256':hashlib.sha256(self.fault_raw.read_bytes()).hexdigest()})

    def source_registry(self, paths):
        assert isinstance(paths,list) and all(isinstance(p,str) for p in paths)
        roots=[self.out.resolve(),self.child_output.resolve()]
        for value in paths:assert any(Path(value).resolve().is_relative_to(root) for root in roots)
        scm.atomic_json(self.native_shared/'sources.json',sorted({os.path.normcase(os.path.abspath(path)) for path in paths}))
        return {'registered':len(set(paths))}

    def rpc(self,request):
        operation=request['operation']
        if operation=='disable':
            import psutil
            from document_formats_platform import spawn_identity,matching_process
            root=psutil.Process(self.service_pid)
            stamps=[]
            for process in [root,*root.children(recursive=True)]:
                try:stamps.append(spawn_identity(process))
                except (psutil.NoSuchProcess,psutil.ZombieProcess):continue
            result=super().rpc(request)
            deadline=time.monotonic()+8
            while any(matching_process(stamp) is not None for stamp in stamps):
                assert time.monotonic()<deadline,'native service descendant survived stop';time.sleep(.01)
            self.save('native-stopped-tree-'+str(len(self.service_events)),{'members':stamps,'all_gone':True,'at':now()})
            return {**result,'actual_tree':stamps,'all_gone':True}
        if operation=='native_phase':
            assert set(request)=={'operation','phase'}
            assert request['phase'] in {'prepare','explicit-refresh','explicit-upload','resume-captured','archive-only','read-only','service-control','cleanup'}
            (self.native_shared/'phase.txt').write_text(request['phase'],encoding='utf-8');return {'phase':request['phase']}
        if operation=='native_sources':
            assert set(request)=={'operation','paths'}
            return self.source_registry(request['paths'])
        if operation=='native_fault_raw':
            assert set(request)=={'operation'}
            import base64
            return {'raw_base64':base64.b64encode(self.fault_raw.read_bytes()).decode(),'sha256':hashlib.sha256(self.fault_raw.read_bytes()).hexdigest()}
        if operation=='native_configure':
            assert set(request)=={'operation','loss'} and type(request['loss']) is bool
            self.restore_languages()
            status=self.cli('hub','documents','processing-status')
            configured=self.cli('hub','documents','processing-configure','--expected-revision',status['config']['revision'],
                '--ocr-executable',self.materials['ocr_executable'],'--ocr-data-dir',self.private_data,'--languages','chi_sim+eng')
            assert configured['ocr']['ready'] is True
            if request['loss']:(self.private_data/'chi_sim.traineddata').unlink()
            return configured
        if operation=='native_cli':
            assert set(request)=={'operation','args','code'}
            assert request['code'] in (0,2)
            args=cli_arguments(request['args'],self.child_output)
            destination=None
            if '--original-output' in args:
                from uuid import uuid4
                args=list(args);destination=self.cli_outputs/(uuid4().hex+'.bin')
                args[args.index('--original-output')+1]=str(destination)
            value=self.cli('hub',*args,code=request['code'])
            command=self.calls[-1]
            if args[:2]==['documents','refresh']:
                self.storage_acl_receipt()
            result={'value':value,'command':command}
            if destination is not None:
                import base64
                raw=destination.read_bytes()
                result['original']={'actual_cli_output':str(destination),'sha256':hashlib.sha256(raw).hexdigest(),
                    'bytes':len(raw),'base64':base64.b64encode(raw).decode(),
                    'transport':'actual Hub CLI writes administrator-owned task file; byte-verified IPC receipt to standard actor'}
            return result
        if operation=='native_unlink':
            assert set(request)=={'operation','document_id'};ident=identifier(request['document_id'])
            entry=next(v for v in self.cli('hub','documents','files') if v['id']==ident)
            path=Path(entry['path']);assert path.resolve().is_relative_to(self.hub_state.resolve())
            path.unlink(missing_ok=True);return {'document_id':ident,'removed_source_copy':str(path)}
        if operation=='native_raw_acl_path':
            assert set(request)=={'operation','sha256'} and re.fullmatch('[0-9a-f]{64}',request['sha256'])
            path=self.hub_state/'.document-snapshots/raw'/request['sha256'];assert path.is_file()
            return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        if operation=='native_arm_fault':
            assert set(request)=={'operation'}
            (self.gate/'armed').write_text(hashlib.sha256(self.fault_raw.read_bytes()).hexdigest());return {'armed':True}
        if operation=='native_hold_fault':
            assert set(request)=={'operation','attempt_id'}
            _,sample,state,stamps=self.fault_worker(identifier(request['attempt_id']))
            value={'attempt_id':request['attempt_id'],'worker':sample,'supervision':state,'stamps':stamps}
            self.save('native-fault-held-before-read',value);return value
        if operation=='native_release_fault':
            assert set(request)=={'operation','attempt_id'}
            aid=request['attempt_id']
            if aid is not None:identifier(aid)
            (self.gate/'armed').unlink(missing_ok=True)
            (self.gate/((aid+'.release') if aid else 'abort')).touch()
            return {'released_attempt':aid,'armed':False}
        if operation=='native_fault':
            assert set(request)=={'operation','attempt_id'}
            return self.kill_fault(identifier(request['attempt_id']))
        if operation=='native_hold_ocr':
            assert set(request)=={'operation','attempt_id'}
            return self.hold_ocr(identifier(request['attempt_id']))
        if operation=='native_stop_held':
            assert set(request)=={'operation','attempt_id','release'} and type(request['release']) is bool
            return self.stop_held(identifier(request['attempt_id']),request['release'])
        if operation=='native_task_cleanup':
            assert set(request)=={'operation'}
            return self.task_cleanup()
        if operation=='native_resume':
            assert set(request)=={'operation','attempt_id'}
            aid=request['attempt_id']
            if aid is not None:
                identifier(aid)
                matches=[row for row in self.cli('hub','documents','files') if (row.get('latest_attempt') or {}).get('attempt_id')==aid]
                assert len(matches)==1 and matches[0]['published_snapshot'] is None
                assert matches[0]['latest_attempt']['status'] in {'pending','processing'}
            (self.native_shared/'resume-attempt.txt').write_text(aid or '')
            return {'allowed_current_attempt':aid}
        return super().rpc(request)

    def storage_acl_receipt(self):
        """Read real current storage ACLs; never repair them in acceptance."""
        import sqlite3
        paths=[self.hub_state,self.hub_state/'.document-snapshots']
        with sqlite3.connect(self.hub_db.as_uri()+'?mode=ro',uri=True) as c:
            captures=c.execute('SELECT id,raw_sha256,raw_bytes FROM document_captures').fetchall()
        for cid,digest,size in captures:
            assert re.fullmatch('[0-9a-f]{64}',digest)
            path=self.hub_state/'.document-snapshots/raw'/digest
            assert path.resolve().is_relative_to(self.hub_state.resolve())
            assert path.is_file() and path.stat().st_size==size
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
            paths.append(path)
        for name in ('raw','results','reclamation','services','tasks'):
            path=self.hub_state/'.document-snapshots'/name
            if path.is_dir():paths.append(path)
        records=[]
        for index,path in enumerate(dict.fromkeys(paths)):
            assert path.resolve().is_relative_to(self.hub_state.resolve())
            text=self.run('actual-storage-icacls-'+str(index),['icacls.exe',path],role='hub')
            records.append({'path':str(path),'icacls':text,'command':self.calls[-1]})
        encoded=json.dumps([str(path) for path in dict.fromkeys(paths)])
        import base64
        script="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';[Console]::OutputEncoding=[Text.UTF8Encoding]::new();$paths=ConvertFrom-Json ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+base64.b64encode(encoded.encode()).decode()+"')));$items=@(foreach($p in $paths){$a=Get-Acl -LiteralPath $p;@{path=$p;owner=$a.Owner;sddl=$a.Sddl}});ConvertTo-Json -Depth 6 -InputObject $items -Compress"
        sddl=json.loads(self.run('actual-storage-sddl',['powershell.exe','-NoProfile','-Command',script],role='hub'))
        self.save('actual-cli-capture-storage-acl',{'captures':captures,'icacls':records,'actual_sddl':sddl,
            'policy':'read-only diagnostic; original descriptor and bytes unchanged by acceptance'})

    def task_cleanup(self):
        from document_formats_platform import matching_process
        root=self.hub_state/'.document-snapshots/tasks';deadline=time.monotonic()+8
        while True:
            directories=[p for p in root.iterdir() if p.is_dir() and re.fullmatch('[0-9a-f]{32}',p.name)]
            if not (root/'active.json').exists() and all((p/'cleanup.json').is_file() for p in directories):break
            assert time.monotonic()<deadline,'unfinished task cleanup';time.sleep(.01)
        results=[]
        for directory in directories:
            value=json.loads((directory/'cleanup.json').read_text())
            assert {p.name for p in directory.iterdir()} <= {'supervision.json','worker.stdout','worker.stderr','watchdog.stderr','cleanup.json'}
            supervision=json.loads((directory/'supervision.json').read_text())
            members=[supervision['worker'],*supervision.get('children',[])]
            for member in members:assert matching_process(member) is None
            results.append({'attempt_id':directory.name,'cleanup':value,'supervision':supervision})
        for record in self.ocr_records:
            for key in ('ocr','worker'):
                sample=record[key]
                assert matching_process({'pid':sample['pid'],'created':sample['created']}) is None
        assert results;self.save('native-all-task-cleanup',results);return {'tasks':len(results),'all_workers_gone':True}

    def hold_ocr(self,aid):
        import psutil
        from document_formats_platform import spawn_identity
        deadline=time.monotonic()+30
        while True:
            service=psutil.Process(self.service_pid)
            assert sample_process(service)['creation_filetime']==self.sampled_service['creation_filetime']
            for process in service.children(recursive=True):
                try:
                    argv=process.cmdline()
                    if not os.path.samefile(process.exe(),self.materials['ocr_executable']):continue
                    if '--tessdata-dir' not in argv or '-l' not in argv:continue
                    if not Path(argv[1]).resolve().is_relative_to((self.hub_state/'.document-snapshots/tasks'/aid).resolve()):continue
                    token=sample_process(process)
                    assert token['sid']=='S-1-5-19' and token['session_id']==0
                    worker=psutil.Process(process.ppid());parent=sample_process(worker)
                    assert parent['sid']=='S-1-5-19' and parent['session_id']==0
                    assert parent['argv'][parent['argv'].index('--task-token')+1]==aid
                    process.suspend()
                    self.held={'attempt_id':aid,'stamp':spawn_identity(process),'ocr':token,'worker':parent,'service':sample_process(service)}
                    self.save('native-held-ocr-'+aid,self.held);return self.held
                except (psutil.NoSuchProcess,FileNotFoundError):continue
            assert time.monotonic()<deadline,'No real OCR observed for current attempt';time.sleep(.002)

    def stop_held(self,aid,release):
        import threading
        from document_formats_platform import matching_process
        assert self.held['attempt_id']==aid
        errors=[];start=time.monotonic()
        def stop():
            try:self.rpc({'operation':'disable'})
            except BaseException as error:errors.append(str(error))
        stopper=threading.Thread(target=stop);stopper.start()
        # Dispatch is the actual SCM stop-pending state, not thread creation.
        deadline=time.monotonic()+15
        while True:
            query=subprocess.run(['sc.exe','query',self.service_name],capture_output=True,timeout=10)
            raw=query.stdout
            if b'STOP_PENDING' in raw or b'STOPPED' in raw:break
            assert time.monotonic()<deadline and not errors,(errors,raw);time.sleep(.01)
        if release:
            process=matching_process(self.held['stamp'])
            if process is not None:process.resume()
        stopper.join(timeout=60)
        assert not stopper.is_alive() and not errors,errors
        assert matching_process(self.held['stamp']) is None,'OCR survived native stop'
        value={'held':self.held,'native_stop_status':raw.decode(errors='replace'),'release_after_stop_pending':release,
            'elapsed':time.monotonic()-start,'ocr_gone':True}
        self.save('native-ocr-stop-'+aid,value);return value

    def fault_worker(self,aid):
        import psutil
        from document_formats_platform import matching_process,spawn_identity
        deadline=time.monotonic()+30
        root=self.hub_state/'.document-snapshots/tasks'
        while True:
            path=self.gate/(aid+'.json')
            if path.is_file():break
            assert time.monotonic()<deadline;time.sleep(.01)
        record=json.loads(path.read_text());assert record['token']==aid
        process=psutil.Process(record['pid']);sample=sample_process(process)
        assert process.create_time()==record['created'] and sample['executable']==record['exe'] and sample['argv']==record['argv']
        assert sample['sid']=='S-1-5-19' and sample['session_id']==0
        assert 'smm_hub._archive.document_worker' in sample['argv'] and sample['argv'][sample['argv'].index('--task-token')+1]==aid
        service=sample_process(psutil.Process(self.service_pid));assert service['creation_filetime']==self.sampled_service['creation_filetime']
        assert self.service_pid in [p.pid for p in process.parents()]
        from document_formats_live_json import read_live_json
        def current():
            actual=matching_process({'pid':process.pid,'created':record['created']})
            assert actual is not None,'enrolled fault worker exited before observation'
        state=read_live_json(root/'active.json',deadline,current=current,
            observe=lambda value:self.save('native-fault-active-read-'+aid,value))
        assert state['token']==aid
        assert state['worker']=={'pid':process.pid,'created':process.create_time()}
        assert state['rss_limit']==1024**3 and state['temp_limit']==256*1024**2 and state['seconds_limit']==300
        assert state['gate_open'] and state['windows_job']['atomic']
        stamps=[spawn_identity(p) for p in [process,*process.children(recursive=True)]]
        return process,sample,state,stamps

    def kill_fault(self,aid):
        from document_formats_platform import matching_process
        try:
            root=self.hub_state/'.document-snapshots/tasks'
            process,sample,state,stamps=self.fault_worker(aid)
            service=sample_process(__import__('psutil').Process(self.service_pid))
            started=time.monotonic();process.kill()
            proof=root/aid/'cleanup.json'
            terminal=None
            while True:
                candidates=self.request('hub','/v1/documents/files')
                terminal=next((row for row in candidates if (row.get('latest_attempt') or {}).get('attempt_id')==aid),None)
                if (terminal is not None and terminal['latest_attempt']['status']=='failed' and terminal['published_snapshot'] is None
                        and proof.is_file() and not (root/'active.json').exists()
                        and all(matching_process(s) is None for s in stamps)):break
                assert time.monotonic()-started<=5;time.sleep(.01)
            assert time.monotonic()-started<=5
            assert {p.name for p in proof.parent.iterdir()} <= {'supervision.json','worker.stdout','worker.stderr','watchdog.stderr','cleanup.json'}
            value={'attempt_id':aid,'worker':sample,'service':service,'stamps':stamps,'supervision':state,
                'cleanup':json.loads(proof.read_text()),'terminal_document':terminal,'seconds':time.monotonic()-started}
            self.save('native-worker-fault',value);return value
        finally:
            (self.gate/'armed').unlink(missing_ok=True);(self.gate/(aid+'.release')).touch()


class NativeClient(FormatsClient):
    @property
    def phase(self):return self._phase
    @phase.setter
    def phase(self,value):
        Probe.phase.fset(self,value)
        if hasattr(self,'control'):self.rpc('native_phase',phase=value)

    def __init__(self,config,output):
        super().__init__(config,output)
        from document_formats_protocol_guards import install
        install(self,owners=('local',))
        self.config['read_guards']=True
        self.protocol_guard_paths=[self.out/'local-protocol-guard.jsonl',Path(config['native_observation']['log'])]

    def cli(self,role,*args,code=0):
        if role!='hub':return super().cli(role,*args,code=code)
        result=self.rpc('native_cli',args=list(map(str,args)),code=code)
        self.calls.append(result['command']);self.save('commands',self.calls)
        if 'original' in result:
            import base64
            receipt=result['original'];raw=base64.b64decode(receipt['base64'])
            assert len(raw)==receipt['bytes'] and hashlib.sha256(raw).hexdigest()==receipt['sha256']
            output=Path(args[args.index('--original-output')+1])
            with output.open('xb') as stream:stream.write(raw)
        return result['value']

    def origins(self):
        import sqlite3
        with sqlite3.connect(self.db['a'].as_uri()+'?mode=ro',uri=True) as c:
            local=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        self.archive_identities={'a':local,'hub':self.rpc('archive_identity')['archive_id']}
        self.device_identities={'a':json.loads(self.db['a'].with_suffix('.sqlite3.hub.json').read_text())['device_id'],
            'hub':self.hub_context['hub_id']}
        self.save('native-archive-identities',{'archives':self.archive_identities,'devices':self.device_identities})

    def register_source_paths(self):
        super().register_source_paths()
        self.rpc('native_sources',paths=sorted({str(i['path']) for i in self.items}))

    def start(self,role):
        previous=self.phase
        self.phase='resume-captured' if role=='hub' and getattr(self,'native_resume_aid',None) else 'service-control'
        try:
            if role=='hub':
                value=self.rpc('enable');self.native_registration=value;self.managed_hub_started=True;return value
            return super().start(role)
        finally:self.phase=previous

    def stop(self,role):
        previous=self.phase;self.phase='service-control'
        try:return super().stop(role)
        finally:self.phase=previous


def prepare(probe):
    probe.check_install();probe.start('hub');probe.start('a')
    info=probe.request('hub','/v1/info');probe.hub_context={k:info[k] for k in ('hub_id','document_epoch')}
    configured=probe.cli('a','configure-hub',probe.address['hub'],'008 native SCM standard Local','--token-file',probe.token_file)
    assert configured['connected'];probe.wait_idle('a')
    probe.request('a','/api/settings',{'sync_interval_seconds':3600},method='PUT')
    probe.projects={'a':[probe.cli('a','project','create','008 native Local scan')],'hub':[]}
    probe.phase='prepare'
    local=probe.cli('a','documents','processing-status')
    value=probe.cli('a','documents','processing-configure','--expected-revision',local['config']['revision'],
        '--ocr-executable',probe.materials['ocr_executable'],'--ocr-data-dir',probe.materials['ocr_data_dir'],'--languages','chi_sim+eng')
    assert value['ocr']['ready']
    probe.rpc('native_configure',loss=False)
    with probe.browser('hub','native-project-create') as browser:
        browser.page.locator('#hub-project-name').fill('008 native SCM browser project')
        project=browser.action(None,browser.page.locator('#hub-project-create').click,'/projects')
        browser.screenshot('created-project')
    assert project['owner']==info['hub_id'];probe.projects['hub']=[project]
    probe.origins()
    probe.browser_uploads(roles=('hub',),project_overrides={'hub':[project]},phase='native-web-upload',label_namespace='T')
    cli_project=probe.cli('hub','project','create','008 native SCM CLI path')
    probe.projects['hub'].append(cli_project)
    item=probe.material('docx','NATIVECLIPATH')
    path=probe.fixtures/'native-path.docx';path.write_bytes(item['raw'])
    item.update(role='hub',project=cli_project,path=path,acquisition='path',version=1,processing_version=1)
    source=probe.cli('hub','documents','add',path,'--project-id',cli_project['id'])
    probe.phase='explicit-refresh'
    probe.cli('hub','documents','refresh','--source-id',source['id'])
    probe.phase='archive-only'
    own=probe.cli('hub','documents','files','--source-id',source['id']);assert len(own)==1
    entry=own[0];assert entry['latest_attempt']['status']=='ready'
    item.update(id=entry['id'],entry=entry);probe.items.append(item)
    for item in probe.items:item.update(version=1,processing_version=1)
    probe.register_source_paths()
    for item in probe.items:snapshot(probe,item)
    observations=probe.rpc('formats_ocr_observations')
    aid=next(i['entry']['latest_attempt']['attempt_id'] for i in probe.items if i['kind']=='ocrpdf')
    assert not observations['errors'] and any(v['attempt_id']==aid for v in observations['records'])
    probe.save('H1-native-creation',{'document_ids':[i['id'] for i in probe.items],
        'actual_ocr':observations,'cli_path_source':source})


def receive_scan(probe):
    item=probe.material('ocrpdf','NATIVELOCALSCAN')
    item.update(role='a',project=probe.projects['a'][0],version=1,processing_version=1,query='73428')
    entry=upload(probe,item,item['raw']);assert entry['latest_attempt']['status']=='ready'
    item.update(id=entry['id'],entry=entry,path=Path(entry['path']));probe.items.append(item)
    probe.register_source_paths()
    native=snapshot(probe,item)
    probe.phase='archive-only';start=len(events(probe))
    item['path'].unlink()
    probe.policy('a',item['project']);synced=probe.cli('a','documents','sync')
    assert synced['errors']==[] and synced['pending'] is False
    projected=next(p for p in probe.cli('hub','project','list') if p['owner']==probe.device_identities['a'] and p['source_key']==item['project']['stable_key'])
    projected_item={**item,'read_role':'hub','read_project':projected}
    received=snapshot(probe,projected_item)
    for name in ('text','locations','coverage','profile','result_sha256','processing_status'):
        assert received['text'][name]==native['text'][name]
    assert_read_only(probe,start)
    # Real OS denial in the uninstrumented standard controller, not a hook.
    raw=probe.rpc('native_raw_acl_path',sha256=item['sha256']);assert raw['sha256']==item['sha256']
    os_denials=[]
    for path in (probe.hub_db,Path(raw['path'])):
        try:
            with path.open('rb') as stream:stream.read(1)
        except PermissionError as error:os_denials.append({'path':str(path),'winerror':error.winerror,'errno':error.errno})
        else:raise AssertionError('standard controller read protected Hub storage')
    probe.stop('a');probe.phase='read-only'
    unchanged_publication(snapshot(probe,projected_item,reference=received['reference']),received)
    probe.start('a');probe.phase='archive-only'
    sources=probe.cli('hub','documents','sources')
    source=next(s for s in sources if (s.get('origin') or {}).get('device_id')==probe.device_identities['a'])
    before=rows(probe,'hub')
    probe.phase='read-only';start=len(events(probe))
    for action,args in [('set',[source['id'],'--project-id',projected['id']]),('remove',[source['id']]),('refresh',['--source-id',source['id']])]:
        probe.cli('hub','documents',action,*args,code=2)
        assert '设备同步投影只读' in probe.calls[-1]['stderr']
    receiver=next(value for value in before.values() if value['origin']==probe.expected_origin(item))
    original=library_entry(probe,'a',item['id'])
    probe.cli('hub','documents','reprocess','--document-id',receiver['id'],
        '--capture-id',original['latest_attempt']['capture_id'],'--expected-attempt-id',original['latest_attempt']['attempt_id'],
        '--expected-version',1,'--expected-processing-version',1,code=2)
    assert any(message in probe.calls[-1]['stderr'] for message in ('设备同步投影只读','当前捕获没有有效采集来源'))
    from uuid import uuid4
    native_document=next(i for i in probe.items if i['role']=='hub' and i['kind']=='docx')
    local_before=rows(probe,'a')
    denied=probe.request('a','/api/documents/uploads',probe.body('a',project_id=native_document['project']['id'],
        project_key=native_document['project']['source_key'],submission_id=uuid4().hex,name='wrong-owner.docx',
        sha256=native_document['sha256'],bytes=len(native_document['raw'])),code=400)
    assert '本机项目身份已变化' in denied['detail']
    probe.cli('a','documents','reprocess','--document-id',native_document['id'],
        '--capture-id',native_document['entry']['latest_attempt']['capture_id'],
        '--expected-attempt-id',native_document['entry']['latest_attempt']['attempt_id'],
        '--expected-version',1,'--expected-processing-version',1,code=2)
    assert '文档不存在' in probe.calls[-1]['stderr']
    assert rows(probe,'a')==local_before
    assert rows(probe,'hub')==before;assert_read_only(probe,start)
    probe.save('H2-direct-index-and-protection',{'local_id':item['id'],'origin':probe.expected_origin(item),
        'projected':projected,'source':source,'actual_os_denials':os_denials,
        'wrong_end_response':denied,'stored_read_after_local_stop':True})
    probe.projected_item=projected_item
    return projected


def dependency_retry(probe):
    from document_formats_lifecycle_readback import failed_detail
    base=next(i for i in probe.items if i['role']=='hub' and i['kind']=='docx')
    stable=snapshot(probe,base)
    item=probe.material('ocrpdf','NATIVEFIRSTLOSS');item.update(role='hub',project=probe.projects['hub'][0],version=1,processing_version=1,query='73428')
    evidence=[]
    for replacement in (False,True):
        probe.phase='prepare';probe.rpc('native_configure',loss=True)
        previous=library_entry(probe,'hub',item['id']) if replacement else None
        newer=probe.material('ocrpdf','NATIVEREPLACEMENTLOSS') if replacement else item
        old=snapshot(probe,item) if replacement else None
        failed=upload(probe,item,newer['raw'],replacement=previous)
        assert failed['latest_attempt']['status']=='failed' and 'chi_sim.traineddata' in failed['latest_attempt']['error']
        if not replacement:
            assert failed['published_snapshot'] is None and failed['version']==failed['processing_version']==0
            item.update(id=failed['id'],path=Path(failed['path']))
        else:
            assert failed['published_snapshot']['capture_id']!=failed['latest_attempt']['capture_id']
            assert failed['version']==failed['processing_version']==1
            unchanged_publication(snapshot(probe,item,reference=old['reference']),old)
        failed_detail(probe,item,failed,'native-first-loss' if not replacement else 'native-replacement-loss')
        probe.phase='read-only';start=len(events(probe))
        for document in [i for i in probe.items if i['role']=='hub']:
            snapshot(probe,document)
        snapshot(probe,probe.projected_item)
        assert_read_only(probe,start)
        probe.phase='prepare';probe.rpc('native_configure',loss=False)
        probe.rpc('native_unlink',document_id=item['id'])
        finished=retry(probe,'hub',failed)
        assert finished['latest_attempt']['status']=='ready'
        item.update(**{k:newer[k] for k in ('raw','truth','sha256')},version=2 if replacement else 1,processing_version=2 if replacement else 1)
        snapshot(probe,item)
        if replacement:reject_old(probe,'hub',old)
        evidence.append({'replacement':replacement,'failed':failed,'ready':finished})
    probe.items.append(item);probe.register_source_paths()
    unchanged_publication(snapshot(probe,base,reference=stable['reference']),stable)
    probe.save('H4-actual-dependency-retries',evidence)


def worker_failure(probe):
    import base64
    frozen=probe.rpc('native_fault_raw');raw=base64.b64decode(frozen['raw_base64']);assert hashlib.sha256(raw).hexdigest()==frozen['sha256']
    control=next(i for i in probe.items if i['role']=='hub' and i['kind']=='docx')
    stable=snapshot(probe,control)
    receipt=None
    try:
        probe.rpc('native_arm_fault')
        item={'role':'hub','project':probe.projects['hub'][0],'label':'NATIVEWORKERFAULT','format':'docx'}
        receipt=upload(probe,item,raw,await_terminal=False)
        held=probe.rpc('native_hold_fault',attempt_id=receipt['attempt_id'])
        assert held['attempt_id']==receipt['attempt_id']
        probe.phase='archive-only'
        # Read while the real worker is held, before killing it.
        unchanged_publication(snapshot(probe,control,reference=stable['reference']),stable)
        observation=probe.rpc('native_fault',attempt_id=receipt['attempt_id'])
        failed=wait(probe,'hub',receipt['document_id'],timeout=5)
        assert failed['latest_attempt']['status']=='failed' and failed['published_snapshot'] is None
        unchanged_publication(snapshot(probe,control,reference=stable['reference']),stable)
    finally:
        probe.rpc('native_release_fault',attempt_id=receipt['attempt_id'] if receipt else None)
    item=probe.material('docx','NATIVENEXTLEGAL');item.update(role='hub',project=probe.projects['hub'][0],version=1,processing_version=1)
    ready=upload(probe,item,item['raw']);assert ready['latest_attempt']['status']=='ready'
    item.update(id=ready['id'],entry=ready,path=Path(ready['path']));probe.items.append(item);probe.register_source_paths();snapshot(probe,item)
    probe.save('H4-actual-worker-failure',{'receipt':receipt,'failed':failed,'supervision':observation,'next_ready':ready})


def active_ocr(probe):
    records=[]
    control=next(i for i in probe.items if i['role']=='hub' and i['kind']=='docx')
    for action in ('retain','remove','replace'):
        item=probe.material('ocrpdf','NATIVESCMACTIVE'+action.upper())
        item.update(role='hub',project=probe.projects['hub'][0],version=1,processing_version=1,query='73428')
        receipt=upload(probe,item,item['raw'],await_terminal=False);item['id']=receipt['document_id']
        held=probe.rpc('native_hold_ocr',attempt_id=receipt['attempt_id'])
        current=library_entry(probe,'hub',item['id'])
        assert current['published_snapshot'] is None and current['version']==current['processing_version']==0
        assert current['latest_attempt']['attempt_id']==receipt['attempt_id']
        item['path']=Path(current['path']);stable=snapshot(probe,control)
        if action=='remove':
            probe.request('hub','/v1/documents/library/'+item['id'],probe.body('hub',project_id=item['project']['id'],project_key=item['project']['source_key'],
                expected_version=0,expected_processing_version=0,expected_revision=current['source_revision'],capture_id=receipt['capture_id'],expected_attempt_id=receipt['attempt_id']),method='DELETE')
        elif action=='replace':
            newer=probe.material('nativepdf','NSR')
            finished=upload(probe,item,newer['raw'],replacement=current);assert finished['latest_attempt']['status']=='ready'
            assert finished['latest_attempt']['capture_id']!=receipt['capture_id']
            item.update(**{k:newer[k] for k in ('raw','truth','sha256','query','kind')})
        probe.phase='service-control'
        stopped=probe.rpc('native_stop_held',attempt_id=receipt['attempt_id'],release=action!='retain')
        probe.managed_hub_started=False
        offline={v['id']:v for v in probe.cli('hub','documents','files')}
        if action=='retain':
            assert offline[item['id']]['published_snapshot'] is None
            assert offline[item['id']]['version']==offline[item['id']]['processing_version']==0
            assert offline[item['id']]['latest_attempt']['capture_id']==receipt['capture_id']
        elif action=='remove':assert item['id'] not in offline
        else:assert offline[item['id']]['published_snapshot']['capture_id']!=receipt['capture_id']
        if action!='remove':probe.rpc('native_unlink',document_id=item['id'])
        pending=action=='retain' and offline[item['id']]['latest_attempt']['status'] in {'pending','processing'}
        resume_start=len(events(probe))
        if pending:
            probe.rpc('native_resume',attempt_id=receipt['attempt_id']);probe.native_resume_aid=receipt['attempt_id']
            probe.phase='resume-captured'
        probe.start('hub')
        if not pending:probe.phase='archive-only'
        mode='old_candidate_not_revived'
        if action=='retain':
            try:finished=wait(probe,'hub',item['id'])
            finally:
                probe.rpc('native_resume',attempt_id=None);probe.native_resume_aid=None;probe.phase='archive-only'
            resume_events=events(probe)[resume_start:]
            assert not [event for event in resume_events if event['kind'] in {'source-open','native-role-denial'}
                or (event['kind'] in {'content-processing','child-start','network-call'} and not event['allowed'])],resume_events
            probe.save('native-resume-observations-'+receipt['attempt_id'],{'events':resume_events,'fixture_denials':[]})
            mode='same_pending_attempt'
            if finished['latest_attempt']['status']=='failed':
                finished=retry(probe,'hub',finished);mode='explicit_saved_capture_retry'
            assert finished['latest_attempt']['status']=='ready' and finished['latest_attempt']['capture_id']==receipt['capture_id']
            if mode=='same_pending_attempt':assert finished['latest_attempt']['attempt_id']==receipt['attempt_id']
        elif action=='remove':assert item['id'] not in rows(probe,'hub')
        else:
            finished=library_entry(probe,'hub',item['id'])
            assert finished['latest_attempt']['status']=='ready' and finished['latest_attempt']['capture_id']!=receipt['capture_id']
        if action!='remove':snapshot(probe,item);probe.items.append(item)
        unchanged_publication(snapshot(probe,control,reference=stable['reference']),stable)
        records.append({'action':action,'receipt':receipt,'actual_held_process':held,'actual_stop':stopped,
            'offline_entry':offline.get(item['id']),'mode':mode,'final':None if action=='remove' else finished})
    probe.register_source_paths();probe.save('H3-actual-active-ocr-stop-start',records)


def restart_read_only(probe,start):
    """Include service startup, excluding only verified native management."""
    from document_formats_guard_primitives import AUDIT_PRIMITIVES
    primitives={};exec(AUDIT_PRIMITIVES,primitives)
    all_events=events(probe);window=all_events[start:]
    config=probe.config['native_observation'];name=config['service_name']
    image=probe.native_registration['service']['PathName']
    accepted=[]
    allowed=[['sc.exe','query',name],['sc.exe','start',name],
        ['sc.exe','config',name,'binPath=',image,'start=','auto','obj=',r'NT AUTHORITY\LocalService','DisplayName=','SMM aggregation server'],
        ['sc.exe','failure',name,'reset=','86400','actions=','restart/3000/restart/5000'],
        ['netsh.exe','advfirewall','firewall','delete','rule','name='+name],
        ['netsh.exe','advfirewall','firewall','add','rule','name='+name,'dir=in','action=allow','protocol=TCP','localport='+str(probe.ports['hub']),'remoteip=localsubnet','profile=any'],
        ['icacls.exe',str(probe.hub_state),'/inheritance:r','/grant:r','*S-1-5-32-544:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-19:(OI)(CI)M']]
    for event in window:
        assert event['kind'] not in {'content-processing','source-open','native-role-denial'},event
        if event['kind']=='network-call':assert event['allowed'],event
        if event['kind']!='child-start':continue
        identities=[e for e in all_events if e['kind']=='identity' and e['owner']==event['owner'] and e['pid']==event['pid']
            and e['monotonic_ns']<=event['monotonic_ns']]
        assert identities;identity=max(identities,key=lambda e:e['monotonic_ns'])
        assert event['owner']=='hub' and all(identity[k]==v for k,v in config['maintenance_identity'].items())
        argv=identity['argv'];assert 'smm_hub.cli' in argv and argv[-1]=='enable'
        assert os.path.normcase(os.path.abspath(argv[argv.index('--state-dir')+1]))==os.path.normcase(os.path.abspath(probe.hub_state))
        effective=event['effective_arguments'];assert effective is not None and len(effective)>1
        command=primitives['native_argv'](effective[1]);assert command
        command[0]=Path(command[0]).name.lower()
        assert command in allowed,command
        accepted.append({'event':event,'actual_administrator_identity':identity,'exact_native_command':command})
    assert accepted,'Native restart management transport was not actually observed'
    probe.save('H3-restart-zero-content-observation',{'all_events':window,'accepted_exact_native_management':accepted,
        'unexpected_source_processing_ocr_or_business_child':[]})


def ordinary(config,output):
    from document_formats_lifecycle_readback import targets,replay
    probe=NativeClient(config,output);result=None
    bindings=probe.version_bindings();probe.save('native-source-bindings',bindings)
    for name,digest in bindings.items():
        raw=(ROOT/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest;probe.keep('source-snapshot/'+name,raw)
    try:
        prepare(probe)
        receive_scan(probe)
        dependency_retry(probe)
        worker_failure(probe)
        active_ocr(probe)
        cases=targets(probe);probe.phase='read-only';start=len(events(probe))
        refs=replay(probe,cases,'native-before-restart');assert_read_only(probe,start)
        for item in probe.items:
            if item['role']=='hub' and item.get('acquisition')!='path':probe.rpc('native_unlink',document_id=item['id'])
            else:item['path'].unlink(missing_ok=True)
        probe.stop('a');probe.stop('hub')
        restart_start=len(events(probe))
        probe.start('hub');probe.start('a')
        assert probe.request('hub','/v1/info')['document_epoch']==probe.hub_context['document_epoch']
        probe.phase='read-only';start=len(events(probe))
        restart_read_only(probe,restart_start)
        replay(probe,cases,'native-after-restart',refs);assert_read_only(probe,start)
        observation=probe.rpc('formats_ocr_observations');assert not observation['errors'],observation['errors']
        from document_formats_scm_native_guard import validate_storage_access
        access=validate_storage_access(events(probe),service_name=probe.config['native_observation']['service_name'],
            state=probe.hub_state)
        probe.save('actual-service-worker-storage-access',access)
        probe.rpc('native_task_cleanup')
        assert probe.version_bindings()==bindings
        result={'status':'passed','scope':'dedicated actual SCM H1-H4 with standard Local/browser; H5 administrator cleanup separately required',
            'actor':probe.actor(),'documents':len(probe.items),'readback_cases':len(cases),'finished_at':now()}
    except BaseException:
        probe.save('failure',{'traceback':traceback.format_exc(),'at':now()});raise
    finally:probe.cleanup()
    probe.save('result',result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target-config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=json.loads(args.target_config.read_text(encoding='utf-8-sig'))
    if config.get('external_hub'):ordinary(config,args.output.resolve())
    else:
        managers=[]
        def factory(config,output):
            manager=NativeAdministrator(config,output);managers.append(manager);return manager
        try:scm.administrator(config,args.output.resolve(),manager_factory=factory,runner=Path(__file__).resolve(),
            wrapper=Path(__file__).with_name('document_formats_installed_standard_user.ps1'))
        finally:
            for manager in managers:manager.stop_monitor()

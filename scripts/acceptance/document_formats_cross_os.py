"""X1 candidate: genuine creator results replayed through an actual base-only Hub.

Synthetic transfer bundle contains only four raw/result pairs and their source
oracles. Credentials, databases, traces and private keys stay in private output.
"""
from pathlib import Path
import argparse,hashlib,json,os,socket,sqlite3,sys,time,traceback,uuid,zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/acceptance'),str(ROOT/'tests')]
from document_formats_installed_protocols import FormatProbe
from hub_documents_platform import Probe,now
from document_formats_guard_primitives import AUDIT_PRIMITIVES, IDENTITY_SOURCE, actual_identity
from document_formats_receiver_absence import OCR_ABSENCE_SOURCE


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


CONTENT=('text','text_length','start','end','start_line','end_line','locations','tables','coverage','processing_status','format','sha256','version','processing_version')
TABLE=('table_id','location','rows','columns','header_rows','sheet_state','cells','window','window_origin','header_context')


def source_packet(probe,item,source):
    with sqlite3.connect(probe.db['a'].as_uri()+'?mode=ro',uri=True) as connection:
        connection.row_factory=sqlite3.Row
        row=connection.execute('SELECT d.*,m.relative_path,m.qualification FROM documents d JOIN document_memberships m ON m.document_pk=d.pk WHERE d.id=? AND m.source_id=?',(item['id'],source['id'])).fetchone()
        state=connection.execute('SELECT * FROM document_snapshot_state WHERE document_pk=?',(row['pk'],)).fetchone()
    root=probe.db['a'].parent/'.document-snapshots'
    raw=(root/'raw'/row['sha256']).read_bytes();result=(root/'results'/state['result_sha256']).read_bytes();value=json.loads(result)
    assert raw==item['raw'] and sha(raw)==row['sha256'] and sha(result)==state['result_sha256']
    assert canonical(value)==result and value['text']==item['snapshot']['text']
    metadata={k:row[k] for k in ('version','sha256','text_sha256','path','captured_at','captured_by_source_id')}
    metadata.update(document_id=row['id'],display_name=item['path'].name,capture_sequence=row['publish_seq'],
        schema=value['schema'],format=value['format'],raw_bytes=len(raw),result_bytes=len(result),
        processing_version=state['processing_version'],result_sha256=state['result_sha256'],
        profile_sha256=sha(canonical(value['profile'])),capture_id=state['published_capture'])
    tables=[]
    for table in item['snapshot']['tables']:
        table_value=probe.request('a','/api/documents/read',{'reference':item['hit']['reference'],'view':'table','table_id':table['table_id'],
            'row_start':1,'row_end':table['rows']+1,'column_start':1,'column_end':table['columns']+1})
        tables.append({k:table_value[k] for k in TABLE if k in table_value})
    item_value={'label':item['label'],'kind':item['kind'],'query':item['query'],'metadata':metadata,
        'relative_path':row['relative_path'],'qualification':row['qualification'],
        'raw_member':'raw/'+sha(raw),'result_member':'results/'+sha(result),
        'source_text':{k:item['snapshot'][k] for k in CONTENT if k in item['snapshot']},
        'source_tables':tables,'source_truth':item['truth']}
    return item_value,{item_value['raw_member']:raw,item_value['result_member']:result}


def produce(config,output,bundle):
    config={**config,'read_guards':False,'browser_checks':False,'browser_uploads':False}
    probe=FormatProbe(config,output);cwd=output/'non-source-cwd';cwd.mkdir();os.chdir(cwd)
    bindings=probe.version_bindings();probe.save('source-bindings',bindings)
    files={};packet=None
    try:
        probe.check_install()
        for role in ('hub','a'):probe.start(role)
        info=probe.request('hub','/v1/info');probe.hub_context={k:info[k] for k in ('hub_id','document_epoch')}
        assert probe.cli('a','configure-hub',probe.address['hub'],'X actual producer','--token-file',probe.token_file)['connected']
        probe.wait_idle('a');probe.request('a','/api/settings',{'sync_interval_seconds':3600},method='PUT')
        project=probe.cli('a','project','create','X actual creator project');probe.projects={'a':[project],'hub':[]}
        probe.cli('a','documents','processing-configure','--expected-revision',0,'--ocr-executable',probe.materials['ocr_executable'],
            '--ocr-data-dir',probe.materials['ocr_data_dir'],'--languages','chi_sim+eng')
        directory=probe.fixtures/'creator';directory.mkdir()
        for kind,label in (('docx','XWORD'),('xlsx','XBOOK'),('nativepdf','XNP'),('ocrpdf','XSCAN')):
            item=probe.material(kind,label,'alpha' if kind=='ocrpdf' else None)
            if kind=='docx':
                from document_formats_upload_fixture import upload_input
                item['raw'],_=upload_input('docx',label);item['sha256']=sha(item['raw'])
                assert len(item['raw'])>1024*1024
            path=directory/(label+'.'+item['format']);path.write_bytes(item['raw'])
            item.update(role='a',project=project,path=path,acquisition='path',source_fingerprint={'sha256':sha(path.read_bytes()),'mtime_ns':path.stat().st_mtime_ns})
            probe.items.append(item)
        probe.phase='explicit-refresh';source=probe.cli('a','documents','add',directory,'--project-id',project['id'])
        probe.cli('a','documents','refresh','--source-id',source['id']);probe.phase='archive-only'
        rows=probe.cli('a','documents','files','--source-id',source['id']);assert len(rows)==4 and len({r['id'] for r in rows})==4
        for item in probe.items:
            row=next(r for r in rows if Path(r['path']).name==item['path'].name)
            assert row['latest_attempt']['status']=='ready' and row['version']==row['processing_version']==1
            assert sha(item['path'].read_bytes())==item['source_fingerprint']['sha256'] and item['path'].stat().st_mtime_ns==item['source_fingerprint']['mtime_ns']
            item.update(id=row['id'],entry=row)
        probe.origins();probe.complete_cli_http('actual-producer')
        documents=[]
        for item in probe.items:
            value,pairs=source_packet(probe,item,source);documents.append(value);files.update(pairs)
        source_actor=probe.actor();probe.save('actual-creator-identity',source_actor)
        packet={'schema':'smm-008-x-creator-v1','actual_platform':sys.platform,'creator_identity_receipt_sha256':sha((probe.out/'actual-creator-identity.json').read_bytes()),
            'archive_id':probe.archive_identities['a'],'project_key':project['stable_key'],'source_id':source['id'],
            'source_revision':source['revision'],'documents':documents,'product_wheel_sha256':sha(Path(config['local_wheel']).read_bytes()),
            'members':{name:{'sha256':sha(raw),'bytes':len(raw)} for name,raw in files.items()},
            'controller_sha256':sha(Path(__file__).read_bytes()),'source_bindings':bindings}
        assert probe.version_bindings()==bindings
    finally:probe.cleanup()
    # All source processes have actually stopped before a transferable packet exists.
    packet['creator_stopped']=True;files['packet.json']=canonical(packet)
    assert not bundle.exists();bundle.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(files.items()):archive.writestr(name,raw)
    with zipfile.ZipFile(bundle) as archive:assert archive.testzip() is None
    probe.save('result',{'status':'passed','actual_platform':sys.platform,'documents':4,'bundle_sha256':sha(bundle.read_bytes()),'bundle_bytes':bundle.stat().st_size,'creator_stopped':True})


RECEIVER_HOOK=r'''
import builtins,json,os,socket,sys,threading,time
from pathlib import Path
def emit(kind,**values):
 with Path(C['log']).open('a',encoding='utf-8') as stream:stream.write(json.dumps({'kind':kind,'pid':os.getpid(),'time_ns':time.time_ns(),**values},default=str)+'\n')
identity=actual_identity()
for field in ('sid','session_id','euid','egid'):
 if field in C['expected_identity']:assert identity[field]==C['expected_identity'][field],('wrong X receiver identity',field,identity)
emit('identity',**identity,python=sys.executable,prefix=sys.prefix,isolated=sys.flags.isolated,argv=sys.argv,cwd=os.getcwd())
original_import=builtins.__import__
forbidden={'PIL','pdfplumber','pdfminer','pypdfium2','defusedxml','psutil'}
def guarded_import(name,*args,**kwargs):
 if name.split('.')[0] in forbidden:
  emit('reader-import',name=name);raise AssertionError('X receiver imported optional processing component')
 return original_import(name,*args,**kwargs)
builtins.__import__=guarded_import
def audit(event,args):
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  raw=os.fsdecode(args[0]);normalized=os.path.normcase(os.path.abspath(raw))
  if raw in C['source_paths'] or normalized in {os.path.normcase(os.path.abspath(p)) for p in C['source_paths']}:
   emit('source-open',path=raw);raise AssertionError('X receiver attempted creator source file')
 if event in PROCESS_EVENTS:
  emit('child-start',event=event,executable=args[0] if args else None,argv=args[1] if len(args)>1 else None);raise AssertionError('X receiver attempted child process')
 if event in NETWORK_EVENTS:
  allowed,internal,local_name,address,reply=network_decision(event,args,sys._getframe(1),set(),{tuple(v) for v in C['listen_endpoints']})
  if allowed:emit('stdlib-socketpair' if internal else ('server-reply' if reply else 'local-name'),event=event,address=address);return
  emit('network',event=event,address=address);raise AssertionError('X receiver attempted outbound network')
def profile(frame,event,arg):
 if event!='call':return
 module=frame.f_globals.get('__name__') or '';name=frame.f_code.co_name
 if ((module=='smm_hub._archive.documents' and name=='_scan') or
     (module=='smm_hub._archive.document_snapshots' and name=='process') or
     (module=='smm_hub._archive.document_processing' and name in {'process','_process'}) or
     (module.startswith('smm_hub._archive.document_formats.') and name in {'parse','intermediate','recognize'})):
  emit('processing',module=module,function=name);raise AssertionError('X receiver attempted content processing')
sys.addaudithook(audit);sys.setprofile(profile);threading.setprofile(profile)
'''


class Receiver(FormatProbe):
    def __init__(self,config,out):
        if config.get('expected_actor_sid'):assert self.actor()['sid']==config['expected_actor_sid']
        Probe.__init__(self,config,out)


def load_packet(bundle):
    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
        packet=json.loads(archive.read('packet.json'));assert packet['schema']=='smm-008-x-creator-v1' and packet['creator_stopped'] is True
        expected=set(packet['members'])|{'packet.json'};assert len(archive.namelist())==len(expected) and set(archive.namelist())==expected
        files={name:archive.read(name) for name in packet['members']}
        for name,raw in files.items():assert packet['members'][name]=={'sha256':sha(raw),'bytes':len(raw)}
    assert len(packet['documents'])==4 and {v['kind'] for v in packet['documents']}=={'docx','xlsx','nativepdf','ocrpdf'}
    return packet,files


def binary(probe,path,raw):
    from urllib.request import Request
    request=Request(probe.address['hub']+path,data=raw,headers={'Authorization':'Bearer '+probe.token,'Content-Type':'application/octet-stream','X-Content-SHA256':sha(raw)},method='PUT')
    with probe.http.open(request,timeout=20) as response:
        data=response.read();assert response.status==200
    value=json.loads(data);probe.calls.append({'label':'actual-https-part','path':path,'request_bytes':len(raw),'request_sha256':sha(raw),'status':200,'response':value});probe.save('commands',probe.calls);return value


def content(value,keys):return {k:value[k] for k in keys if k in value}


def future_references(probe,packet,device):
    # Read the synthetic target's signing material only to build valid future
    # probes. Never write its DB or serialize the signing key. The exact same
    # references must succeed after real HTTPS publication, preventing a bogus
    # invalid-signature negative from passing this test.
    from smm_local.archive_protocol import sign,digest
    with sqlite3.connect(probe.hub_db.as_uri()+'?mode=ro',uri=True) as connection:
        archive=json.loads(connection.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        key=connection.execute('SELECT signing_key FROM archive_reference_material WHERE singleton=1').fetchone()[0]
    source=digest([device,packet['archive_id'],packet['project_key'],packet['source_id']])[:32]
    references={}
    for item in packet['documents']:
        meta=item['metadata'];ident=digest([device,packet['archive_id'],meta['document_id']])[:32]
        inner=sign({'format':1,'kind':'document','archive_id':archive,'document_id':ident,'version':meta['version'],
            'sources':[{'id':source,'revision':packet['source_revision'],'qualification':1}],
            'start':0,'end':min(2000,item['source_text']['text_length']),'processing_version':meta['processing_version'],
            'result_sha256':meta['result_sha256'],'raw_sha256':meta['sha256']},key)
        references[item['label']]=sign({'format':1,'kind':'hub_document','archive_id':archive,**probe.hub_context,
            'origin':{'device_id':device,'archive_id':packet['archive_id'],'document_id':meta['document_id']},
            'reference':inner,'version':meta['version'],'sha256':meta['sha256'],'text_sha256':meta['text_sha256'],
            'text_length':item['source_text']['text_length'],'processing_version':meta['processing_version'],'result_sha256':meta['result_sha256']},key)
    return references


def assert_unpublished(probe,packet,project,references,phase):
    context=probe.hub_context
    assert probe.request('hub','/v1/documents/files')==[]
    assert probe.request('hub','/v1/documents/library?project_id='+str(project))==[]
    for item in packet['documents']:
        assert probe.request('hub','/v1/documents/search',{**context,'query':item['query'],'scope':'project','project_id':project})['results']==[]
        body={**context,'reference':references[item['label']]}
        for fields in [{'view':'text'},{'view':'original-info'},*[{'view':'table','table_id':t['table_id']} for t in item['source_tables']]]:
            probe.request('hub','/v1/documents/read',{**body,**fields},code=400)
        probe.request('hub','/v1/documents/original',body,code=400)
    probe.save('unpublished-'+phase,{'files':0,'library':0,'documents':len(packet['documents']),
        'valid_future_reference_all_reads_rejected':True,'phase':phase})


def exact_published_set(probe,packet,device):
    from smm_local.archive_protocol import digest
    rows=probe.request('hub','/v1/documents/files')
    expected={digest([device,packet['archive_id'],item['metadata']['document_id']])[:32] for item in packet['documents']}
    origins={(device,packet['archive_id'],item['metadata']['document_id']) for item in packet['documents']}
    assert len(rows)==len({r['id'] for r in rows})==len(expected)==4
    assert {r['id'] for r in rows}==expected
    assert {tuple(r['origin'][k] for k in ('device_id','archive_id','document_id')) for r in rows}==origins


def read_received(probe,packet,files,device,project,saved=None,*,require_search_reference=True):
    references={};context=probe.hub_context
    for item in packet['documents']:
        metadata=item['metadata'];origin={'device_id':device,'archive_id':packet['archive_id'],'document_id':metadata['document_id']}
        found=probe.request('hub','/v1/documents/search',{**context,'query':item['query'],'scope':'project','project_id':project,'limit':50})['results']
        assert len(found)==1 and found[0]['origin']==origin
        hit=found[0];reference=saved[item['label']] if saved is not None else hit['reference']
        assert not require_search_reference or hit['reference']==reference
        assert hit['version']==metadata['version'] and hit['processing_version']==metadata['processing_version'] and hit['sha256']==metadata['sha256']
        references[item['label']]=reference
        value=probe.request('hub','/v1/documents/read',{**context,'reference':reference,'start':0,'end':item['source_text']['text_length']})
        assert value['origin']==origin and content(value,CONTENT)==item['source_text']
        for expected in item['source_tables']:
            table=probe.request('hub','/v1/documents/read',{**context,'reference':reference,'view':'table','table_id':expected['table_id'],
                'row_start':1,'row_end':expected['rows']+1,'column_start':1,'column_end':expected['columns']+1})
            assert table['origin']==origin and table['version']==metadata['version'] and table['processing_version']==metadata['processing_version'] and table['sha256']==metadata['sha256']
            assert content(table,TABLE)==expected
        info=probe.request('hub','/v1/documents/read',{**context,'reference':reference,'view':'original-info'})
        assert info['origin']==origin and info['sha256']==metadata['sha256'] and info['bytes']==metadata['raw_bytes'] and info['available'] is True
        assert probe.raw_original('hub',reference)==files[item['raw_member']]
        # Independent stored-result custody check; never writes Hub database.
        actual=(probe.hub_state/'.document-snapshots/results'/metadata['result_sha256']).read_bytes()
        assert actual==files[item['result_member']] and sha(actual)==metadata['result_sha256']
    return references


def receive(config,output,bundle,expected_source,*,component_only=False):
    import subprocess
    assert config['expected_platform']==sys.platform
    packet,files=load_packet(bundle);assert packet['actual_platform']==expected_source
    assert component_only or expected_source!=sys.platform, 'X requires genuinely different source/receiver OS'
    probe=Receiver(config,output);cwd=output/'non-source-cwd';cwd.mkdir();os.chdir(cwd)
    import shutil
    original_python=Path(config['hub_python']);original_prefix=original_python.parent.parent
    private_prefix=output/'programs/hub-env';private_prefix.parent.mkdir()
    shutil.copytree(original_prefix,private_prefix,symlinks=True)
    config['hub_python']=str(private_prefix/original_python.relative_to(original_prefix))
    python=config['hub_python'];guards=output/'receiver-guard.jsonl'
    check_code=IDENTITY_SOURCE+'\n'+OCR_ABSENCE_SOURCE+'\nimport json;print(json.dumps({"identity":actual_identity(),"ocr_absence":ocr_absence()}))'
    absence=subprocess.run([python,'-I','-X','utf8','-c',check_code],env=probe.env('hub'),capture_output=True,timeout=30)
    probe.keep('base-ocr-absence.stdout',absence.stdout);probe.keep('base-ocr-absence.stderr',absence.stderr);assert absence.returncode==0,absence.stderr
    absent=json.loads(absence.stdout);assert absent['ocr_absence']['status']=='absent',absent
    for field in ('sid','session_id','euid','egid'):
        if field in probe.actor():assert absent['identity'][field]==probe.actor()[field]
    probe.save('base-ocr-absence',absent)
    info=subprocess.run([python,'-I','-X','utf8','-c','import sysconfig,importlib.util,json;names=["PIL","pdfplumber","pdfminer","pypdfium2","defusedxml","psutil","smm_local"];print(json.dumps({"site":sysconfig.get_path("purelib"),"components":{n:importlib.util.find_spec(n) is not None for n in names}}))'],capture_output=True,timeout=20)
    probe.keep('base-install.stdout',info.stdout);probe.keep('base-install.stderr',info.stderr);assert info.returncode==0
    actual=json.loads(info.stdout);assert not any(actual['components'].values()),actual
    mapping=json.loads(Path(config['hub_expected']).read_text());site_root=Path(actual['site'])
    for name,digest in mapping.items():assert sha((site_root/name).read_bytes())==digest
    probe.save('base-install-asset-verification',{'module_sha256':mapping,'wheel_sha256':sha(Path(config['hub_wheel']).read_bytes()),'no_processing_components':actual['components']})
    site=Path(actual['site']);assert site.resolve().is_relative_to(Path(python).parent.parent.resolve())
    hook=site/'_smm_008_x_receiver.py';pth=site/'_smm_008_x_receiver.pth';assert not hook.exists() and not pth.exists()
    hook.write_text('C='+repr({'log':str(guards),'source_paths':[d['metadata']['path'] for d in packet['documents']],'expected_identity':actual_identity(),'listen_endpoints':[['127.0.0.1',probe.ports['hub']]]})+'\n'+IDENTITY_SOURCE+'\n'+AUDIT_PRIMITIVES+'\n'+RECEIVER_HOOK,encoding='utf-8');pth.write_text('import _smm_008_x_receiver\n',encoding='utf-8')
    probe.keep('receiver-installed-hook.py',hook.read_bytes());probe.keep('receiver-installed-hook.pth',pth.read_bytes())
    bindings=probe.version_bindings();probe.save('receiver-source-bindings',bindings)
    checks=[('source','open('+repr(packet['documents'][0]['metadata']['path'])+',"rb")','X receiver attempted creator source file'),('startup','import sys,_smm_008_x_receiver as m;assert sys.flags.isolated==1;print(m.__file__)',None),
        ('socketpair','import socket;a,b=socket.socketpair();a.sendall(b"pair");assert b.recv(4)==b"pair";a.close();b.close()',None),
        ('import','import pdfplumber','X receiver imported optional processing component'),
        ('processing','from smm_hub._archive.document_processing import process;process(None,None)','X receiver attempted content processing'),
        ('child','import subprocess,sys;subprocess.run([sys.executable,"-c","pass"])','X receiver attempted child process'),
        ('network','import socket;socket.getaddrinfo("models.example.invalid",443)','X receiver attempted outbound network')]
    checks.extend([('system','import os;os.system("exit 0" if os.name=="nt" else ":")','X receiver attempted child process'),
        ('spawn','import os,sys;pid=os.spawnv(os.P_WAIT,sys.executable,[sys.executable,"-c","pass"])','X receiver attempted child process')])
    if hasattr(os,'posix_spawn'):
        checks.append(('posix-spawn','import os,sys;pid=os.posix_spawn(sys.executable,[sys.executable,"-c","pass"],os.environ);os.waitpid(pid,0)','X receiver attempted child process'))
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);udp.bind(('127.0.0.1',0));udp.settimeout(.15)
    checks.append(('udp-sendto','import socket;socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendto(b"blocked",'+repr(udp.getsockname())+')','X receiver attempted outbound network'))
    if hasattr(socket.socket,'sendmsg'):
        checks.append(('udp-sendmsg','import socket;socket.socket(socket.AF_INET,socket.SOCK_DGRAM).sendmsg([b"blocked"],[],0,'+repr(udp.getsockname())+')','X receiver attempted outbound network'))
    for label,code,marker in checks:
        control=subprocess.run([python,'-I','-X','utf8','-c',code],capture_output=True,timeout=20)
        probe.keep('controls/'+label+'.stdout',control.stdout);probe.keep('controls/'+label+'.stderr',control.stderr)
        if marker is None:
            assert control.returncode==0 and not control.stderr,(label,control.stderr)
            if label=='startup':assert Path(control.stdout.decode().strip()).resolve()==hook.resolve()
        else:assert control.returncode!=0 and marker.encode() in control.stderr,(label,control.stderr)
    try:
        unexpected=udp.recvfrom(100)
    except socket.timeout:
        unexpected=None
    finally:udp.close()
    assert unexpected is None,'forbidden UDP payload escaped observer'
    control_events=[json.loads(line) for line in guards.read_text().splitlines()]
    assert {e['kind'] for e in control_events if e['kind'] not in {'identity','stdlib-socketpair','local-name','server-reply'}}=={'reader-import','processing','child-start','network','source-open'}
    probe.save('receiver-guard-controls',{'positive':['actual isolated startup','real socketpair'],
        'negative':[label for label,code,marker in checks if marker is not None],'events':control_events})
    event_start=len(control_events)
    result=None
    try:
        probe.start('hub');info=probe.request('hub','/v1/info');probe.hub_context={k:info[k] for k in ('hub_id','document_epoch')};context=probe.hub_context
        device=uuid.uuid4().hex;probe.request('hub','/v1/upload-policy/register',{'hub_id':context['hub_id'],'device_id':device})
        binding={**context,'device_id':device,'archive_id':packet['archive_id'],'project_key':packet['project_key'],'generation':1}
        probe.request('hub','/v1/documents/control',{**binding,'sequence':1,'project_name':'Actual '+expected_source+' creator','enabled':True,'retained':[]})
        projects=probe.request('hub','/v1/projects');project=next(p['id'] for p in projects if p['owner']==device and p['source_key']==packet['project_key'])
        future=future_references(probe,packet,device)
        for item in packet['documents']:
            meta=item['metadata'];raw=files[item['raw_member']];encoded=files[item['result_member']]
            begun=probe.request('hub','/v1/documents/processed/begin',{**binding,'submission_id':uuid.uuid4().hex,'document':meta})
            ident=begun['transfer_id'];block=begun['block_bytes'];assert block==1024*1024
            offset=0
            if len(raw)>block:
                part=binary(probe,'/v1/documents/processed/'+ident+'/raw/0',raw[:block]);assert part['received']['raw']==block;offset=block
                probe.request('hub','/v1/documents/processed/commit',{'transfer_id':ident},code=400)
                assert_unpublished(probe,packet,project,future,item['label']+'-half-raw')
            for kind,data,start in (('raw',raw,offset),('results',encoded,0)):
                for pos in range(start,len(data),block):
                    chunk=data[pos:pos+block];ack=binary(probe,'/v1/documents/processed/'+ident+'/'+kind+'/'+str(pos),chunk)
                    assert ack['received'][kind]==pos+len(chunk)
                if kind=='raw':
                    probe.request('hub','/v1/documents/processed/commit',{'transfer_id':ident},code=400)
                    assert_unpublished(probe,packet,project,future,item['label']+'-missing-result')
            staged=probe.request('hub','/v1/documents/processed/commit',{'transfer_id':ident});assert staged['staged'] is True
            assert_unpublished(probe,packet,project,future,item['label']+'-staged')
        manifest={**binding,'control_sequence':1,'source_id':packet['source_id'],'revision':packet['source_revision'],'sequence':1,'submission_id':uuid.uuid4().hex,
            'files':[{**i['metadata'],'relative_path':i['relative_path'],'qualification':i['qualification']} for i in packet['documents']]}
        # Read HTTP headers to establish that the server consumed the complete
        # request. Discard the application receipt body without consuming it;
        # closing immediately after send can abort the request on Windows TLS.
        # Confirm publication independently before the idempotent retry.
        import http.client,ssl
        conn=http.client.HTTPSConnection('127.0.0.1',probe.ports['hub'],context=ssl.create_default_context(cafile=str(probe.ca)),timeout=15)
        raw=canonical(manifest)
        response=None
        try:
            conn.request('POST','/v1/documents/publish',body=raw,headers={'Authorization':'Bearer '+probe.token,'Content-Type':'application/json'})
            response=conn.getresponse()
            assert response.status==200, response.status
            response_status=response.status
        finally:
            if response is not None:response.close()
            conn.close()
        probe.save('actual-discarded-publication-response',{'request_sha256':sha(raw),'bytes':len(raw),'response_status':response_status,'headers_read':True,'body_read':False,'transport':'actual verified HTTPS; headers consumed, application receipt body discarded without read/JSON decoding; underlying buffering may prefetch bytes'})
        until=time.monotonic()+15
        while True:
            found=probe.request('hub','/v1/documents/files')
            if len(found)==4:break
            assert time.monotonic()<until;time.sleep(.05)
        ack=probe.request('hub','/v1/documents/publish',manifest);again=probe.request('hub','/v1/documents/publish',manifest);assert ack==again and ack['published']==4
        exact_published_set(probe,packet,device)
        read_received(probe,packet,files,device,project,future,require_search_reference=False)
        refs=read_received(probe,packet,files,device,project)
        probe.stop('hub');probe.start('hub');assert probe.request('hub','/v1/info')['document_epoch']==context['document_epoch']
        assert read_received(probe,packet,files,device,project,refs)==refs
        read_received(probe,packet,files,device,project,future,require_search_reference=False)
        exact_published_set(probe,packet,device)
        events=[json.loads(line) for line in guards.read_text().splitlines()][event_start:]
        assert events and any(e['kind']=='identity' for e in events)
        assert not [e for e in events if e['kind'] in {'reader-import','processing','child-start','network','source-open'}],events
        assert probe.version_bindings()==bindings
        result={'status':'passed','scope':'C1 same-OS protocol component only' if component_only else 'X1 genuine cross-OS receiver','x1_qualified':not component_only and expected_source!=sys.platform,'source_platform':expected_source,'actual_receiver_platform':sys.platform,'actor':probe.actor(),'documents':4,
            'source_stopped_before_packet':packet['creator_stopped'],'raw_bundle_sha256':sha(bundle.read_bytes()),'receiver_processing_calls':0,
            'incomplete_raw_rejected':True,'actual_unread_receipt_retry':True,'restart_old_references':True,'finished_at':now()}
    except BaseException:probe.save('failure',{'traceback':traceback.format_exc(),'at':now()});raise
    finally:probe.cleanup()
    probe.save('result',result)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['produce','receive']);p.add_argument('--target-config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source-platform');a=p.parse_args()
    config=json.loads(a.target_config.resolve().read_text());out=a.output.resolve();bundle=a.bundle.resolve()
    if a.phase=='produce':produce(config,out,bundle)
    else:receive(config,out,bundle,a.source_platform)


if __name__=='__main__':main()

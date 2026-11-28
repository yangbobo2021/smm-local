"""Real GC readers must not turn concurrent metadata publication into failure."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from zipfile import ZipFile, ZipInfo, ZIP_STORED

import psutil
import pytest

from document_helpers import ROOT, Fixture, observe, fingerprint
from document_formats_platform import spawn_identity, process_tree, terminate_verified, same_existing_path
from document_formats_fixtures import docx_fixture
from smm_local.archive_protocol import atomic_json, control_lock
from smm_local.core import Archive
from smm_local.documents import Documents
from smm_local.document_snapshots import Snapshots


# Profile only the actual file read.  The original io.open/CreateFile sharing
# flags and bytes remain untouched.  This also works if publication serializes
# against a short reader instead of allowing replacement while it stays open.
READER = r'''
import json,os,sys,time
from pathlib import Path
import psutil
sys.path.insert(0,sys.argv[1])
from smm_local.core import Archive
from smm_local.document_snapshots import Snapshots
db=Archive(Path(sys.argv[2]));name=sys.argv[3];gate=Path(sys.argv[4])
snap=Snapshots(db);target=(snap.root/'reclamation'/name).resolve()
entered=False
def profile(frame,event,arg):
 global entered
 if entered or event!='c_call' or getattr(arg,'__name__',None)!='read':return
 stream=getattr(arg,'__self__',None);path=getattr(stream,'name',None)
 if not isinstance(path,(str,os.PathLike)) or Path(path).resolve()!=target:return
 entered=True
 p=psutil.Process();packet={'pid':p.pid,'created':p.create_time(),'argv':p.cmdline(),'exe':p.exe(),'target':str(target),'descriptor':stream.fileno()}
 pending=gate/'entered.pending';pending.write_text(json.dumps(packet),encoding='utf-8');pending.replace(gate/'entered.json')
 until=time.monotonic()+10
 while not (gate/'release').exists():
  if time.monotonic()>until:raise AssertionError('reader gate was not released')
  time.sleep(.005)
sys.setprofile(profile)
try:value=snap._gc_read(name,None)
finally:sys.setprofile(None)
assert entered
print(json.dumps({'value':value,'reader':{'pid':os.getpid(),'target':str(target)}}))
'''


def original(label):
    raw,_=docx_fixture(label);out=io.BytesIO()
    with ZipFile(io.BytesIO(raw)) as source,ZipFile(out,'w',ZIP_STORED) as target:
        for name in source.namelist():
            info=ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o600<<16
            target.writestr(info,source.read(name))
    return out.getvalue()


def setup(tmp_path,name):
    f=Fixture(tmp_path);db=f.db;snap=Snapshots(db);project=f.project('metadata sharing')
    path=f.file('real-document.docx',raw=original('FirstGeneration'))
    source=f.add(path,[project]);f.refresh(source);first=f.files(source)[0]
    path.write_bytes(original('SecondGeneration'));f.refresh(source);current=f.files(source)[0]
    assert first['latest_attempt']['capture_id']!=current['latest_attempt']['capture_id']
    assert current['version']==current['processing_version']==2 and current['latest_attempt']['status']=='ready'
    with db.connect() as c:archive=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    owner=hashlib.sha256(json.dumps(['document-blob-owner-v2',archive,str(db.db_path.resolve())],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    before={key:json.loads(snap._gc_path(key).read_bytes()) for key in ('archives.json','owners.json','retired.json')}
    assert all(before.values()),'all old generations must contain real members'
    assert before['archives.json'][owner]=={'archive_id':archive,'database':str(db.db_path.resolve())}
    assert first['latest_attempt']['capture_id'] in before['retired.json']['captures']
    assert first['latest_attempt']['attempt_id'] in before['retired.json']['attempts']
    assert 'raw/'+hashlib.sha256(path.read_bytes()).hexdigest() in before['owners.json']
    expected=json.loads(json.dumps(before[name]))
    if name=='archives.json':
        neighbor=Archive(tmp_path/'neighbor.sqlite3');Documents(neighbor);writer=Snapshots(neighbor)
        with neighbor.connect() as c:other=json.loads(c.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
        key=hashlib.sha256(json.dumps(['document-blob-owner-v2',other,str(neighbor.db_path.resolve())],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        assert key not in expected;expected[key]={'archive_id':other,'database':str(neighbor.db_path.resolve())}
        def publish():
            with control_lock(snap.root/'capacity.lock'):writer._register_gc_owner()
    elif name=='owners.json':
        raw=original('ThirdGeneration');digest=hashlib.sha256(raw).hexdigest();assert 'raw/'+digest not in expected
        expected['raw/'+digest]=[owner]
        def publish():assert snap.put('raw',raw)==digest
    else:
        f.remove(source)
        assert json.loads(snap._gc_path(name).read_bytes())==before[name]
        expected={key:sorted(set(expected[key])|{current['latest_attempt'][field]}) for key,field in (('captures','capture_id'),('attempts','attempt_id'))}
        def publish():
            with control_lock(snap.root/'capacity.lock'):snap.reclaim_candidates()
    assert expected!=before[name]
    return db,snap,before,expected,publish,path


@pytest.mark.parametrize('name',['archives.json','owners.json','retired.json'])
def test_actual_gc_reader_does_not_break_concurrent_publication(tmp_path,name):
    # TC-008-gc-read-sharing; component evidence, not E/H identities or Web UI.
    db,snap,before,expected,publish,path=setup(tmp_path,name)
    source_before=fingerprint(path)
    unrelated=tmp_path/'unrelated.json';unrelated.write_bytes(b'{"unchanged":true}\n');mtime=unrelated.stat().st_mtime_ns
    gate=tmp_path/'reader-gate';gate.mkdir()
    command=[sys.executable,'-B','-X','utf8','-c',READER,str(ROOT/'src'),str(db.db_path),name,str(gate)]
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=tmp_path)
    stamp=spawn_identity(psutil.Process(child.pid));timer=None;error=None;out=err=b''
    try:
        until=time.monotonic()+10
        while not (gate/'entered.json').exists() and child.poll() is None and time.monotonic()<until:time.sleep(.01)
        assert (gate/'entered.json').exists(),'real product read did not reach its open descriptor'
        marker=json.loads((gate/'entered.json').read_bytes());members=process_tree(stamp)
        actual=next(p for p in members if p['pid']==marker['pid'] and p['created']==marker['created'])
        assert marker['argv']==actual['argv'] and marker['argv'][1:]==command[1:]
        assert same_existing_path(marker['exe'],actual['exe'])
        assert marker['target']==str((snap.root/'reclamation'/name).resolve())
        # Permit either concurrent replacement or short bounded serialization.
        # An immediate sharing failure still remains a failure after release.
        timer=threading.Timer(.2,lambda:(gate/'release').touch());timer.start()
        try:publish()
        except Exception as exc:error={'type':type(exc).__name__,'message':str(exc),'winerror':getattr(exc,'winerror',None)}
    finally:
        (gate/'release').touch()
        if timer:timer.join(2)
        try:out,err=child.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            terminate_verified(process_tree(stamp),owner=child);out,err=child.communicate(timeout=3)
        observe('gc-metadata-reader-'+name,{'platform':sys.platform,'name':name,'launcher':stamp,'marker':locals().get('marker'),'writer_error':error,'old_values':before,'expected_new_value':expected,'reader_stdout':out.decode('utf-8',errors='replace'),'reader_stderr':err.decode('utf-8',errors='replace'),'reader_exit':child.returncode})
    assert child.returncode==0,err
    assert json.loads(out)['value']==before[name]
    assert error is None,error
    for key,value in before.items():
        wanted=expected if key==name else value
        assert json.loads(snap._gc_path(key).read_bytes())==wanted
        assert snap._gc_read(key,None)==wanted
    assert fingerprint(path)==source_before
    assert unrelated.read_bytes()==b'{"unchanged":true}\n' and unrelated.stat().st_mtime_ns==mtime


@pytest.mark.skipif(os.name!='nt',reason='requires actual Windows delete-sharing semantics')
def test_external_noncooperating_reader_still_causes_real_sharing_failure(tmp_path):
    target=tmp_path/'external.json';atomic_json(target,{'old':True})
    with target.open('rb') as reader:
        with pytest.raises(PermissionError) as caught:atomic_json(target,{'new':True})
        assert caught.value.winerror in (5,32) and json.loads(reader.read())=={'old':True}
    assert json.loads(target.read_bytes())=={'old':True}
    atomic_json(target,{'new':True});assert json.loads(target.read_bytes())=={'new':True}
    observe('gc-metadata-real-windows-sharing-control',{'winerror':caught.value.winerror,'old_value_kept':True,'after_close_replace_succeeded':True})

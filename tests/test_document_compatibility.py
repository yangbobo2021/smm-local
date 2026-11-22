import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import pytest
from document_helpers import Fixture, ROOT, seed_conversation, observe
from test_005_contracts import pair, add_local, connect
from smm_local import federation


def retained_state(db):
    with db.connect() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in ['settings','messages','conversations'] or r[0].startswith(('local_upload_','upload_message_'))]
        return {name:[dict(r) for r in c.execute('SELECT * FROM '+name)] for name in sorted(tables)}


@pytest.mark.parametrize('mode',['none','hub','paused'])
def test_isolation(pair,tmp_path,monkeypatch,mode):
    original=add_local(pair,'original','OriginalProject','conversationnonce original')
    f=Fixture(tmp_path/'document-client',db=pair.local)
    if mode!='none':
        connect(pair);federation.choose_upload(pair.local,'only',[original['project_id']]);federation.push_pending(pair.local)
    if mode=='paused':f.db.set_settings(sync_paused=True)
    f.db.set_source_enabled('codex',False)
    before=retained_state(f.db);remote=retained_state(pair.remote);calls=len(pair.calls)
    def reject(*args,**kwargs):raise AssertionError('document operation attempted a Hub/network call')
    monkeypatch.setattr(federation,'_request',reject)
    original_connect=socket.socket.connect
    def no_network(self,address):
        if self.family in [socket.AF_INET,socket.AF_INET6]:raise AssertionError('document operation opened an Internet socket')
        return original_connect(self,address)
    monkeypatch.setattr(socket.socket,'connect',no_network)
    path=f.file('private-document.txt','docprivateneedle 本机文件 😀')
    source=f.add(path,[original['project_id']]);f.refresh(source)
    hit=f.search('docprivateneedle',scope='project',project_id=original['project_id'])['results'][0]
    assert f.read(hit)['text']=='docprivateneedle 本机文件 😀'
    f.set(source,project_ids=[]);f.refresh(source);f.remove(source)
    assert retained_state(f.db)==before and retained_state(pair.remote)==remote and len(pair.calls)==calls
    legacy=federation.read_archive(f.db,original['id'])
    assert [m['text'] for m in legacy['messages']]==['conversationnonce original']
    assert f.db.configured_sources()['codex']['enabled'] is False
    assert f.db.settings()['sync_paused']==(mode=='paused')
    observe('isolation-complete-state',{'mode':mode,'before':before,'after':retained_state(f.db),'remote_before':remote,'remote_after':retained_state(pair.remote),'outbound_calls_after_marker':len(pair.calls)-calls})


def test_compatibility(tmp_path):
    # This existing behavior is a pre-development baseline, not an expected red.
    f=Fixture(tmp_path);hit=seed_conversation(f)
    old=federation.read_archive(f.db,hit['id']);new=federation.read_archive(f.db,reference=hit['reference'])
    assert old['messages'][0]['text']==new['messages'][0]['text']=='conversationnonce original'
    assert hit['archive_scope']=='local' and 'matched_messages' in hit and 'content_kind' not in hit
    legacy=ROOT/'tests/fixtures/document_legacy_cli.py'
    metadata=json.loads(legacy.with_suffix('.json').read_text())
    import hashlib
    assert hashlib.sha256(legacy.read_bytes()).hexdigest()==metadata['sha256']
    driver="import pathlib,sys; p=pathlib.Path(sys.argv[1]); sys.argv=['cli.py',*sys.argv[2:]]; exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),{'__name__':'__main__','__package__':'smm_local','__file__':str(p)})"
    env=dict(os.environ,COLUMNS='80',PYTHONUTF8='1',PYTHONPATH=str(ROOT/'src'))
    observed={}
    for action in ['', 'list','validate','register','enable','disable','rollback','batches','purge-batch']:
        args=['source',*([action] if action else []),'--help']
        before=subprocess.run([sys.executable,'-B','-c',driver,str(legacy),*args],capture_output=True,text=True,encoding='utf-8',env=env,cwd=ROOT)
        after=subprocess.run([sys.executable,'-B','-m','smm_local.cli',*args],capture_output=True,text=True,encoding='utf-8',env=env,cwd=ROOT)
        assert before.returncode==after.returncode==0 and before.stdout==after.stdout
        observed[action or 'source']={'old_stdout':before.stdout,'new_stdout':after.stdout,'old_exit':before.returncode,'new_exit':after.returncode}
    observe('legacy-source-help',observed)

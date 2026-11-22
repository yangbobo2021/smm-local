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


def second_conversation(db,root):
    root.mkdir(parents=True,exist_ok=True)
    record={'type':'user','uuid':'second-message','sessionId':'second-session','cwd':str(root/'OtherProject'),
            'message':{'role':'user','content':'conversationnonce second independent'}}
    (root/'other.jsonl').write_text(json.dumps(record)+'\n',encoding='utf-8')
    db.sync_claude(root)
    with db.connect() as c:
        row=c.execute("SELECT id,project_id,source,source_session_id FROM conversations WHERE source_session_id='second-session'").fetchone()
    return dict(row)


def retained_state(db):
    with db.connect() as c:
        tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'") if r[0] in ['settings','messages','conversations'] or r[0].startswith(('local_upload_','upload_message_'))]
        return {name:[dict(r) for r in c.execute('SELECT * FROM '+name)] for name in sorted(tables)}


@pytest.mark.parametrize('mode',['none','hub','paused'])
def test_isolation(pair,tmp_path,monkeypatch,mode):
    original=add_local(pair,'original','OriginalProject','conversationnonce original')
    second=second_conversation(pair.local,tmp_path/'claude-fixture')
    f=Fixture(tmp_path/'document-client',db=pair.local)
    if mode!='none':
        connect(pair);federation.choose_upload(pair.local,'only',[original['project_id'],second['project_id']]);federation.push_pending(pair.local)
    if mode=='paused':f.db.set_settings(sync_paused=True)
    f.db.set_source_enabled('codex',False)
    f.db.set_source_enabled('claude-code',True)
    sources_before=f.db.configured_sources()
    # Windows asyncio emulates socketpair using loopback TCP. Establish the
    # TestClient's reusable portal before guarding product operations; keep
    # blocking every new IP connection, including a loopback Hub connection.
    with f.client:
        before=retained_state(f.db);remote=retained_state(pair.remote);calls=len(pair.calls)
        with monkeypatch.context() as guard:
            def reject(*args,**kwargs):raise AssertionError('document operation attempted a Hub/network call')
            guard.setattr(federation,'_request',reject)
            original_connect=socket.socket.connect
            def no_network(self,address):
                if self.family in [socket.AF_INET,socket.AF_INET6]:raise AssertionError('document operation opened an Internet socket')
                return original_connect(self,address)
            guard.setattr(socket.socket,'connect',no_network)
            for address in [('127.0.0.1',18770),('203.0.113.1',443)]:
                with socket.socket() as sentinel:
                    with pytest.raises(AssertionError,match='Internet socket'):sentinel.connect(address)
            path=f.file('private-document.txt','docprivateneedle 本机文件 😀')
            source=f.add(path,[original['project_id']]);f.refresh(source)
            hit=f.search('docprivateneedle',scope='project',project_id=original['project_id'])['results'][0]
            assert f.read(hit)['text']=='docprivateneedle 本机文件 😀'
            f.set(source,project_ids=[]);f.refresh(source);f.remove(source)
            assert retained_state(f.db)==before and retained_state(pair.remote)==remote and len(pair.calls)==calls
            for item,expected,source_name in [(original,'conversationnonce original','codex'),(second,'conversationnonce second independent','claude-code')]:
                legacy=federation.read_archive(f.db,item['id'])
                assert [m['text'] for m in legacy['messages']]==[expected] and legacy['source']==source_name
            assert f.db.configured_sources()==sources_before
            assert f.db.get_settings()['sync_paused']==(mode=='paused')
            observe('isolation-complete-state',{'mode':mode,'before':before,'after':retained_state(f.db),'remote_before':remote,'remote_after':retained_state(pair.remote),'outbound_calls_after_marker':len(pair.calls)-calls,'guard_blocks_loopback_and_external_ip':True})


def test_compatibility(tmp_path):
    # This existing behavior is a pre-development baseline, not an expected red.
    f=Fixture(tmp_path);hit=seed_conversation(f)
    second=second_conversation(f.db,tmp_path/'other-fixture')
    with f.db.connect() as c:
        first=dict(c.execute("SELECT id,source,source_session_id FROM conversations WHERE source_session_id='documents-compat-session'").fetchone())
    expected={first['id']:('codex','documents-compat-session','conversationnonce original'),second['id']:('claude-code','second-session','conversationnonce second independent')}
    results=federation.search_archive(f.db,'conversationnonce',local=True)['results']
    assert len(results)==2 and {h['id'] for h in results}==set(expected)
    for hit in results:
        source_name,session,text=expected[hit['id']]
        assert hit['source']==source_name and hit['source_session_id']==session
        old=federation.read_archive(f.db,hit['id']);new=federation.read_archive(f.db,reference=hit['reference'])
        for read in [old,new]:
            assert read['source']==source_name and read['source_session_id']==session and read['id']==hit['id']
            assert [m['text'] for m in read['messages']]==[text]
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

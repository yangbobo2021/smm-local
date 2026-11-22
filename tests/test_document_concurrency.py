import base64
import json
from pathlib import Path
import threading
import pytest
from document_helpers import Fixture, names, document_state, observe


def blocked_publish(monkeypatch,source_id):
    from smm_local.documents import Documents
    reached=threading.Event();release=threading.Event();original=Documents._publish
    def gate(self,source,*args,**kwargs):
        if source['id']==source_id and not reached.is_set():
            reached.set();assert release.wait(15),'test publication barrier timed out'
        return original(self,source,*args,**kwargs)
    monkeypatch.setattr(Documents,'_publish',gate)
    return reached,release


def background_refresh(f,source):
    result={}
    def run():
        try:
            r=f.client.post('/api/documents/refresh',json={'source_id':source['id']})
            result.update(status=r.status_code,body=r.json())
        except BaseException as e:result['exception']=repr(e)
    thread=threading.Thread(target=run,daemon=True);thread.start();return thread,result


def finish(thread,result,release):
    release.set();thread.join(20);assert not thread.is_alive() and 'exception' not in result,result
    assert result['status'] in [200,400,409],result
    observe('late-refresh-response',result)


@pytest.mark.parametrize('change',['new-refresh','set-config'])
def test_refresh_order(tmp_path,monkeypatch,change):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q')
    path=f.file('one.txt','needle original');source=f.add(path,[p]);f.refresh(source)
    path.write_text('needle oldloseruniqueterm',encoding='utf-8')
    reached,release=blocked_publish(monkeypatch,source['id']);thread,result=background_refresh(f,source)
    try:
        assert reached.wait(10)
        if change=='new-refresh':
            path.write_text('needle newwinneruniqueterm',encoding='utf-8');f.refresh(source)
            assert f.read(names(f)['one.txt'])['text']=='needle newwinneruniqueterm'
        else:
            f.set(source,project_ids=[q],exclude=['blocked/**'],recursive=False)
            assert f.source(source)['status']=='pending' and f.search()['results']==[]
        before=document_state(f)
    finally:finish(thread,result,release)
    assert document_state(f)==before
    if change=='new-refresh':
        assert len(f.search('newwinneruniqueterm')['results'])==1 and f.search('oldloseruniqueterm')['results']==[]
    else:
        assert f.source(source)['project_ids']==[q] and f.source(source)['status']=='pending'
    observe('refresh-order-expected',{'case':change,'winner_snapshot':before})


def test_refresh_remove(tmp_path,monkeypatch):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q')
    exclusive=f.file('exclusive.txt','needle exclusive original');shared=f.file('shared.txt','needle shared original')
    one=f.add(tmp_path/'docs',[p]);two=f.add(shared,[q]);f.refresh()
    old=names(f,project=p)
    exclusive.write_text('needle forbidden late exclusive',encoding='utf-8');shared.write_text('needle forbidden late shared',encoding='utf-8')
    reached,release=blocked_publish(monkeypatch,one['id']);thread,result=background_refresh(f,one)
    try:
        assert reached.wait(10);f.remove(one);before=document_state(f)
    finally:finish(thread,result,release)
    assert document_state(f)==before and {s['id'] for s in f.sources()}=={two['id']}
    assert names(f,project=p)=={} and set(names(f,project=q))=={'shared.txt'}
    assert f.read(names(f,project=q)['shared.txt'])['text']=='needle shared original'
    for h in old.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    assert f.search('forbidden')['results']==[]


@pytest.mark.parametrize('prior',['pending','ready'])
def test_overlap_order(tmp_path,monkeypatch,prior):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q')
    files=[f.file('one.txt','needle baseline one'),f.file('two.txt','needle baseline two')]
    one=f.add(tmp_path/'docs',[p])
    if prior=='ready':f.refresh(one)
    two=f.add(tmp_path/'docs',[q]);initial=names(f,project=p)
    for path in files:path.write_text('needle oldloseruniqueterm '+path.name,encoding='utf-8')
    reached,release=blocked_publish(monkeypatch,one['id']);thread,result=background_refresh(f,one)
    try:
        assert reached.wait(10)
        for path in files:path.write_text('needle newwinneruniqueterm '+path.name,encoding='utf-8')
        f.refresh(two);winner=document_state(f)['documents']
    finally:finish(thread,result,release)
    assert document_state(f)['documents']==winner
    for project in [p,q,None]:
        hits=names(f,project=project);assert set(hits)=={'one.txt','two.txt'}
        for name,h in hits.items():
            if prior=='ready':assert h['id']==initial[name]['id'] and h['version']!=initial[name]['version']
            assert h['captured_by_source_id']==two['id']
            assert f.read(h)['text']=='needle newwinneruniqueterm '+name
    assert f.search('oldloseruniqueterm')['results']==[]
    observe('overlap-newer-wins',{'initial':initial,'winner':winner,'final':names(f)})


@pytest.mark.parametrize('change',['links','source'])
def test_query_snapshot(tmp_path,monkeypatch,change):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q');r=f.project('R')
    f.db.link_projects(p,q)
    sources={};paths={}
    for project,name in [(p,'p.txt'),(q,'q.txt'),(r,'r.txt')]:
        path=f.file(name,'needle original '+name);paths[name]=path;sources[name]=f.add(path,[project])
    f.refresh()
    from smm_local import documents as module
    original=module._query_scope;done=[]
    original_revisions={s['id']:s['revision'] for s in f.sources()}
    def update(*args,**kwargs):
        answer=original(*args,**kwargs)
        if not done:
            done.append(True);f.db.link_projects(p,q,False);f.db.link_projects(p,r)
            if change=='source':
                f.set(sources['q.txt'],project_ids=[r]);paths['q.txt'].write_text('needle changed q.txt',encoding='utf-8');f.refresh(sources['q.txt'])
        return answer
    with monkeypatch.context() as patch:
        patch.setattr(module,'_query_scope',update)
        current=names(f,project=p)
    assert set(current)=={'p.txt','q.txt'}
    for name,h in current.items():
        assert h['text']=='needle original '+name
        encoded=h['reference'].split('.')[1];payload=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        for stamp in payload['sources']:assert stamp['revision']==original_revisions[stamp['id']]
    after=names(f,project=p)
    assert set(after)==({'p.txt','r.txt'} if change=='links' else {'p.txt','r.txt','q.txt'})
    assert f.read(current['p.txt'])['text']=='needle original p.txt'
    if change=='source':f.bad('POST','/api/documents/read',{'reference':current['q.txt']['reference']})
    else:assert f.read(current['q.txt'])['text']=='needle original q.txt'
    observe('frozen-query-scope',{'change':change,'old':current,'next':after})


def test_interrupted_refresh(tmp_path):
    f=Fixture(tmp_path);path=f.file('one.txt','needle persistent');source=f.add(path);f.refresh(source)
    old=f.search()['results'][0]
    with f.db.connect() as c:c.execute("UPDATE document_sources SET status='refreshing' WHERE id=?",(source['id'],))
    from smm_local.core import Archive
    from smm_local.documents import Documents
    restarted=Documents(Archive(f.db.db_path))
    assert restarted.sources()[0]['status']=='refreshing'
    f.bad('POST','/api/documents/read',{'reference':old['reference']})
    restarted.refresh(source['id'])
    after=f.search()['results'][0]
    assert after['id']==old['id'] and after['version']==old['version'] and f.source(source)['status']=='ready'
    assert f.read(old)['text']=='needle persistent'
    observe('persistent-interruption',{'scope':'database refreshing state injection, not a claimed process crash','old':old,'after':after})

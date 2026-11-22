from pathlib import Path
import pytest
from document_helpers import Fixture, observe, names


def test_project_scope(tmp_path):
    f=Fixture(tmp_path);p=f.project('same');q=f.project('same');r=f.project('R');g=f.db.ensure_global_project()['id']
    f.db.link_projects(p,q);f.db.link_projects(q,r)
    original_links={x['id']:x['linked_ids'] for x in f.db.projects()}
    for filename,projects in [('p.txt',[p]),('q.txt',[q]),('r.txt',[r]),('global.txt',[g]),('free.txt',[]),('shared.txt',[p,r])]:
        f.add(f.file(filename,'needle '+filename),projects)
    f.refresh()
    expected={p:{'p.txt','q.txt','shared.txt'},q:{'p.txt','q.txt','r.txt','shared.txt'},r:{'q.txt','r.txt','shared.txt'},g:{'global.txt'}}
    for project,wanted in expected.items():
        hits=names(f,project=project);assert set(hits)==wanted
        for filename,h in hits.items():assert f.read(h)['text']=='needle '+filename
    assert set(names(f))=={'p.txt','q.txt','r.txt','global.txt','free.txt','shared.txt'}
    assert {x['id']:x['linked_ids'] for x in f.db.projects()}==original_links
    duplicate=f.add(tmp_path/'docs'/'shared.txt',[p]);f.refresh(duplicate)
    raw=f.search(scope='project',project_id=p)['results']
    assert len(raw)==len({h['path'] for h in raw})==len({h['id'] for h in raw})==3
    observe('project-expected',{'P':p,'Q':q,'R':r,'G':g,'expected':{str(k):sorted(v) for k,v in expected.items()},'links':original_links})


def test_project_maintenance(tmp_path):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q');g=f.db.ensure_global_project()['id']
    one=f.add(f.file('one.txt','needle one'),[p]);both=f.add(f.file('both.txt','needle both'),[p,q]);f.refresh()
    old=names(f,project=p)
    f.db.rename_project(p,'renamed');assert set(names(f,project=p))=={'one.txt','both.txt'}
    assert f.source(one)['project_ids']==[p]
    f.db.merge_projects(p,q)
    assert f.source(one)['project_ids']==[q] and f.source(both)['project_ids']==[q]
    assert set(names(f,project=q))=={'one.txt','both.txt'}
    for h in old.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    state=f.sources();f.db.map_path(str(tmp_path/'docs'),g);assert f.sources()==state
    assert names(f,project=g)=={}
    with pytest.raises(ValueError):f.db.merge_projects(q,g)
    assert f.sources()==state
    assert f.source(one)['status']=='ready' and f.source(both)['status']=='ready'


@pytest.mark.parametrize('withdraw',['remove','failed','continuous'])
def test_overlap_version(tmp_path,monkeypatch,withdraw):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q')
    file=f.file('shared.txt','needle v1');other=f.file('control.txt','needle control')
    s1=f.add(file,[p]);s3=f.add(other,[p]);f.refresh(s1);f.refresh(s3)
    v1=names(f,project=p)['shared.txt'];assert f.read(v1)['text']=='needle v1'
    file.write_text('needle v2',encoding='utf-8');s2=f.add(file,[q]);f.refresh(s2)
    def unique(project,wanted):
        result=f.search(scope='project',project_id=project,limit=50)['results'] if project else f.search(limit=50)['results']
        assert {Path(h['path']).name for h in result}==wanted
        assert len(result)==len(wanted)==len({h['id'] for h in result})==len({h['path'] for h in result})
        return {Path(h['path']).name:h for h in result}
    unique(p,{'shared.txt','control.txt'});unique(q,{'shared.txt'});unique(None,{'shared.txt','control.txt'})
    current={key:names(f,project=project)['shared.txt'] for key,project in [('p',p),('q',q),('all',None)]}
    for h in current.values():
        assert h['id']==v1['id'] and h['version']!=v1['version']
        assert f.read(h)['text']=='needle v2' and h['captured_by_source_id']==s2['id']
    assert current['p']['source_ids']==[s1['id']] and current['q']['source_ids']==[s2['id']]
    assert set(current['all']['source_ids'])=={s1['id'],s2['id']}
    f.bad('POST','/api/documents/read',{'reference':v1['reference']})
    if withdraw=='remove':f.remove(s2)
    elif withdraw=='failed':
        from smm_local.documents import Documents
        def failure(*a,**kw):raise PermissionError('synthetic S2 enumeration/read unavailable')
        with monkeypatch.context() as patch:
            patch.setattr(Documents,'_scan',failure);f.refresh(s2)
        assert f.source(s2)['status']=='failed'
    assert set(names(f,project=p))=={'shared.txt','control.txt'}
    assert set(names(f,project=q))==({'shared.txt'} if withdraw=='continuous' else set())
    unique(p,{'shared.txt','control.txt'});unique(q,{'shared.txt'} if withdraw=='continuous' else set());unique(None,{'shared.txt','control.txt'})
    assert f.read(current['p'])['text']==f.read(current['all'])['text']=='needle v2'
    if withdraw!='continuous':f.bad('POST','/api/documents/read',{'reference':current['q']['reference']})
    else:assert f.read(current['q'])['text']=='needle v2'
    assert f.read(names(f,project=p)['control.txt'])['text']=='needle control'
    file.write_text('needle v3',encoding='utf-8');f.refresh(s1)
    assert f.read(names(f,project=p)['shared.txt'])['text']=='needle v3'
    for h in current.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    assert set(names(f,project=q))==({'shared.txt'} if withdraw=='continuous' else set())
    for project in [p,q,None]:
        hits=f.search(scope='project',project_id=project)['results'] if project else f.search()['results']
        assert len(hits)==len({h['id'] for h in hits})==len({h['path'] for h in hits})
        shared=[h for h in hits if Path(h['path']).name=='shared.txt']
        assert len(shared)==(0 if project==q and withdraw!='continuous' else 1)
        for h in shared:assert f.read(h)['text']=='needle v3'
    if withdraw!='continuous':
        final_refs=[unique(project,{'shared.txt','control.txt'})['shared.txt']['reference'] for project in [p,None]]
        from smm_local.documents import Documents
        def failure(*a,**kw):raise PermissionError('synthetic final S1 failure')
        with monkeypatch.context() as patch:
            patch.setattr(Documents,'_scan',failure);f.refresh(s1)
        assert set(names(f))=={'control.txt'} and names(f,project=q)=={}
        for ref in final_refs:f.bad('POST','/api/documents/read',{'reference':ref})
        assert f.read(names(f)['control.txt'])['text']=='needle control'
    observe('overlap-time-line',{'withdraw':withdraw,'v1':v1,'v2':current,'sources':f.sources(),'final':names(f)})

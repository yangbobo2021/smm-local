"""Additional integration regression for the existing project confirmation fence."""
from document_helpers import Fixture,names
from smm_local.project_control import change
from test_document_concurrency import blocked_publish,background_refresh,finish


def test_document_bindings_are_in_merge_confirmation(tmp_path):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q');r=f.project('R')
    source=f.add(f.file('one.txt','needle material'),[p]);f.refresh(source)
    preview=change(f.db,'merge',{'source_id':p,'target_id':q},always_preview=True)
    assert preview['document_sources']==[{'id':source['id'],'path':source['path'],'revision':1,'project_ids':[p]}]
    f.set(source,project_ids=[p,r]);f.refresh(source)
    import pytest
    with pytest.raises(ValueError,match='重新预览'):
        change(f.db,'merge',{'source_id':p,'target_id':q},preview['confirmation'])
    assert f.source(source)['project_ids']==[p,r]
    latest=change(f.db,'merge',{'source_id':p,'target_id':q},always_preview=True)
    assert change(f.db,'merge',{'source_id':p,'target_id':q},latest['confirmation'])['applied']
    assert set(f.source(source)['project_ids'])=={q,r} and f.read(names(f,project=q)['one.txt'])['text']=='needle material'


def test_merge_cancels_refresh_without_reviving_pending_config(tmp_path,monkeypatch):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q');file=f.file('one.txt','needle original')
    source=f.add(file,[p]);f.refresh(source)
    for pending in [False,True]:
        if pending:f.set(source,project_ids=[q]);p,q=q,f.project('Next')
        file.write_text('needle unpublished',encoding='utf-8')
        with monkeypatch.context() as patch:
            reached,release=blocked_publish(patch,source['id']);thread,result=background_refresh(f,source)
            try:
                assert reached.wait(10);f.db.merge_projects(p,q)
                assert f.source(source)['status']==('pending' if pending else 'ready')
                assert set(names(f,project=q))==(set() if pending else {'one.txt'})
                if not pending:assert f.read(names(f,project=q)['one.txt'])['text']=='needle original'
            finally:finish(thread,result,release)
        assert f.source(source)['status']==('pending' if pending else 'ready')

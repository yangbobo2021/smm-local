from pathlib import Path
import os
import pytest
from document_helpers import Fixture, fingerprint, observe, names


def test_version_lifecycle(tmp_path):
    f=Fixture(tmp_path);p=f.project()
    files=[f.file(n,'needle original '+n) for n in ['one.txt','two.txt']];source=f.add(tmp_path/'docs',[p]);f.refresh(source)
    initial=names(f,project=p)
    assert set(initial)=={'one.txt','two.txt'}
    f.refresh(source);same=names(f,project=p)
    assert set(same)==set(initial)
    assert {k:(v['id'],v['version']) for k,v in initial.items()}=={k:(v['id'],v['version']) for k,v in same.items()}
    for n,h in initial.items():assert f.read(h)['text']=='needle original '+n
    for file in files:file.write_text('needle updated '+file.name,encoding='utf-8')
    # Before refresh, the result is explicitly a captured snapshot, not a live read.
    before=names(f,project=p)
    assert set(before)==set(initial)
    for n,h in before.items():assert h['captured_at'] and f.read(h)['text']=='needle original '+n
    f.refresh(source);updated=names(f,project=p)
    assert set(updated)==set(initial)
    for n,h in updated.items():
        assert h['id']==initial[n]['id'] and h['version']!=initial[n]['version']
        assert f.read(h)['text']=='needle updated '+n
        f.bad('POST','/api/documents/read',{'reference':initial[n]['reference']})
    for file in files:file.write_text('needle original '+file.name,encoding='utf-8')
    f.refresh(source);reverted=names(f,project=p)
    assert set(reverted)==set(initial)
    for n,h in reverted.items():
        assert f.read(h)['text']=='needle original '+n
        assert h['version'] not in {initial[n]['version'],updated[n]['version']}
        for old in [initial[n],updated[n]]:f.bad('POST','/api/documents/read',{'reference':old['reference']})
    moved=files[0].with_name('moved.txt');files[0].rename(moved);files[1].unlink();f.refresh(source)
    final=names(f,project=p);assert set(final)=={'moved.txt'} and final['moved.txt']['id']!=initial['one.txt']['id']
    for h in reverted.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    assert f.read(final['moved.txt'])['text']=='needle original one.txt'


@pytest.mark.parametrize('failure',['file','source','missing'])
def test_qualification(tmp_path,monkeypatch,failure):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q');file=f.file('shared.txt','needle qualification')
    one=f.add(file,[p]);two=f.add(file,[q]);control=f.add(f.file('control.txt','needle control'),[q]);f.refresh()
    oldp=names(f,project=p)['shared.txt'];oldq=names(f,project=q)['shared.txt'];oldall=names(f)['shared.txt']
    f.refresh(one);f.refresh(two)
    for old in [oldp,oldq,oldall]:
        assert f.read(old)['text']=='needle qualification'
        assert names(f)['shared.txt']['version']==old['version']
    from smm_local.documents import Documents
    original=Documents._scan
    def fail(self,source,*a,**kw):
        if source['id']==one['id']:raise PermissionError('synthetic source failed')
        return original(self,source,*a,**kw)
    if failure=='source':
        with monkeypatch.context() as patch:patch.setattr(Documents,'_scan',fail);f.refresh(one)
    elif failure=='file':
        original_open=os.open
        def reject(path,*a,**kw):
            if str(path)==str(file.resolve()):raise PermissionError('synthetic member denied')
            return original_open(path,*a,**kw)
        with monkeypatch.context() as patch:patch.setattr(os,'open',reject);f.refresh(one)
    else:
        file.unlink();f.refresh(one);file.write_text('needle qualification',encoding='utf-8')
    f.bad('POST','/api/documents/read',{'reference':oldp['reference']})
    assert f.read(oldq)['text']==f.read(oldall)['text']=='needle qualification'
    f.refresh(one)
    assert names(f,project=p)['shared.txt']['version']==oldp['version']
    f.bad('POST','/api/documents/read',{'reference':oldp['reference']})
    assert f.read(oldq)['text']==f.read(oldall)['text']=='needle qualification'
    # Lose all original qualifications, then a new source cannot revive old references.
    f.remove(one);f.remove(two)
    f.bad('POST','/api/documents/read',{'reference':oldall['reference']})
    replacement=f.add(file,[p,q]);f.refresh(replacement)
    assert f.read(names(f)['shared.txt'])['text']=='needle qualification'
    for old in [oldp,oldq,oldall]:f.bad('POST','/api/documents/read',{'reference':old['reference']})
    assert f.read(names(f)['control.txt'])['text']=='needle control'


def test_source_lifecycle(tmp_path):
    f=Fixture(tmp_path);p=f.project('P');q=f.project('Q')
    one=f.file('one.txt','needle one');deep=f.file('sub/deep.txt','needle deep');shared=f.file('shared.txt','needle shared')
    a=f.add(tmp_path/'docs',[p]);b=f.add(shared,[q]);f.refresh()
    originals={str(x):fingerprint(x) for x in [one,deep,shared]};old=names(f,project=p)
    old_q=names(f,project=q)['shared.txt'];old_all=names(f)['shared.txt']
    f.set(a,project_ids=[q],exclude=['one.txt'],recursive=False)
    assert f.source(a)['status']=='pending' and names(f,project=p)=={}
    assert set(names(f,project=q))=={'shared.txt'}
    for h in old.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    assert f.read(old_q)['text']==f.read(old_all)['text']=='needle shared'
    f.refresh(a);assert set(names(f,project=q))=={'shared.txt'}
    assert f.read(old_q)['text']==f.read(old_all)['text']=='needle shared'
    for h in old.values():f.bad('POST','/api/documents/read',{'reference':h['reference']})
    before_remove=names(f)['shared.txt']
    f.remove(b);assert set(names(f,project=q))=={'shared.txt'}
    f.bad('POST','/api/documents/read',{'reference':old_q['reference']})
    f.bad('POST','/api/documents/read',{'reference':old_all['reference']})
    assert f.read(before_remove)['text']=='needle shared'
    final=names(f,project=q)['shared.txt'];f.remove(a)
    assert f.sources()==[] and f.search()['results']==[]
    f.bad('POST','/api/documents/read',{'reference':final['reference']})
    with f.db.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM documents WHERE text IS NOT NULL').fetchone()[0]==0
        assert c.execute('SELECT COUNT(*) FROM document_fts').fetchone()[0]==0
    assert {str(x):fingerprint(x) for x in [one,deep,shared]}==originals
    observe('source-lifecycle',{'old':old,'last':final,'source_bytes':originals})

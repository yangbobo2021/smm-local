from pathlib import Path
import os
import pytest
from document_helpers import Fixture, normal, fingerprint, observe


def test_scan_scope(tmp_path):
    f = Fixture(tmp_path); p = f.project()
    expected = {'root.MD':'needle 根😀\n', 'sub/deep.markdown':'needle 深层\n', 'sub/open.txt':'needle open\n', 'branch/keep.txt':'needle keep\n','star-dir/keep.txt':'needle star cannot cross directory\n'}
    for name,text in expected.items(): f.file(name,text)
    for name in ['.secret.txt','.hidden/a.txt','.git/a.md','.hg/a.txt','.svn/a.txt','node_modules/a.md','.venv/a.txt','venv/a.txt','build/a.txt','dist/a.txt','README.pdf']:
        f.file(name,'needle ignored')
    for name in ['private.txt','sub/private.txt','a/b/private.txt','skip1.txt','branch/skip2.txt','star-only.txt','cache/child.txt']:
        f.file(name,'needle custom excluded')
    source=f.add(tmp_path/'docs',[p],exclude=['**/private.txt','skip?.txt','branch/skip?.txt','star-*.txt','cache/'])
    before={str(x):fingerprint(x) for x in (tmp_path/'docs').rglob('*') if x.is_file()}
    f.refresh(source); hits=f.search('needle')['results']
    assert {Path(h['path']).relative_to(tmp_path/'docs').as_posix() for h in hits}==set(expected)
    for h in hits: assert f.read(h)['text']==expected[Path(h['path']).relative_to(tmp_path/'docs').as_posix()]
    assert f.source(source)['counts']['ignored_entries']>=10
    f.set(source, project_ids=[p],exclude=['**/private.txt','skip?.txt','branch/skip?.txt','star-*.txt','cache/'],recursive=False)
    f.refresh(source);assert {Path(h['path']).name for h in f.search()['results']}=={'root.MD'}
    explicit=f.add(tmp_path/'docs'/'build'/'a.txt');f.refresh(explicit)
    assert 'a.txt' in {Path(h['path']).name for h in f.search()['results']}
    hidden=f.add(tmp_path/'docs'/'.secret.txt');f.refresh(hidden)
    assert '.secret.txt' in {Path(h['path']).name for h in f.search()['results']}
    explicit_dir=f.add(tmp_path/'docs'/'.hidden');f.refresh(explicit_dir)
    assert str((tmp_path/'docs'/'.hidden'/'a.txt').resolve()) in {h['path'] for h in f.search()['results']}
    if os.name!='nt':
        outside=tmp_path/'outside';outside.mkdir();(outside/'escape.txt').write_text('escapeuniquemarker',encoding='utf-8')
        (tmp_path/'docs'/'link').symlink_to(outside,target_is_directory=True)
        (tmp_path/'docs'/'linked.txt').symlink_to(outside/'escape.txt')
        f.set(source,project_ids=[p],recursive=True);f.refresh(source)
        assert f.search('escapeuniquemarker')['results']==[]
        f.bad('POST','/api/documents/sources',{'path':str(tmp_path/'docs'/'link')})
    assert {str(x):fingerprint(x) for x in (tmp_path/'docs').rglob('*') if x.is_file() and not x.is_symlink()}==before
    observe('scan-expected',{'expected':expected,'before':before,'sources':f.sources()})


def test_decode_files(tmp_path, monkeypatch):
    f=Fixture(tmp_path)
    cases={'a.MD':'\ufeffneedle 中文😀\r\n组合e\u0301\r末行\n','b.markdown':'needle normal\n','c.TXT':'needle no ending','empty.txt':''}
    paths={n:f.file(n,t) for n,t in cases.items()}
    f.file('bad.txt',raw=b'\xff\xfe');f.file('nul.txt',raw=b'needle\x00body')
    denied=f.file('denied.txt','needle denied');source=f.add(tmp_path/'docs')
    from document_helpers import deny_source_reads
    # A real OS read rejection is shared logic here; platform cases use ordinary filesystem behavior.
    original=os.open
    def fail(path,*a,**kw):
        if str(path)==str(denied.resolve()):raise PermissionError('synthetic read access denied')
        return original(path,*a,**kw)
    with monkeypatch.context() as patch:
        patch.setattr(os,'open',fail);f.refresh(source)
    status=f.source(source);assert status['status']=='partial' and status['counts']['ready']==4 and status['counts']['failed']==3
    files={Path(x['path']).name:x for x in f.files(source)}
    assert all(files[n]['status']=='failed' and files[n]['error'] for n in ['bad.txt','nul.txt','denied.txt'])
    assert files['empty.txt']['status']=='ready' and files['empty.txt']['text_length']==0
    assert 'utf' in files['bad.txt']['error'].lower() and 'nul' in files['nul.txt']['error'].lower()
    assert any(word in files['denied.txt']['error'].lower() for word in ['denied','permission'])
    assert {Path(h['path']).name for h in f.search()['results']} == set(cases)-{'empty.txt'}
    for h in f.search()['results']:
        name=Path(h['path']).name
        assert name in cases and f.read(h)['text']==normal(cases[name])
        assert h['sha256']==fingerprint(paths[name])['sha256']
    f.file('bad.txt','needle recovered');f.file('nul.txt','needle repaired');f.refresh(source)
    assert f.source(source)['status']=='ready' and f.source(source)['counts']['ready']==7
    all_recovered=f.search(limit=50)['results']
    assert {Path(h['path']).name for h in all_recovered}==set(cases)-{'empty.txt'}|{'bad.txt','nul.txt','denied.txt'}
    recovered={**cases,'bad.txt':'needle recovered','nul.txt':'needle repaired','denied.txt':'needle denied'}
    for h in all_recovered:
        name=Path(h['path']).name
        assert f.read(h)['text']==normal(recovered[name])
        assert h['sha256']==fingerprint(tmp_path/'docs'/name)['sha256']
    observe('decode-expected',{'cases':cases,'status':status,'files':files})

from pathlib import Path
import os
import pytest
from document_helpers import Fixture, MIB, fingerprint, observe


@pytest.mark.parametrize('case',['single-equal','single-over','count-equal','count-over','total-equal','total-over','mixed-first','mixed-last','invalid-total-first','invalid-total-last','stat-failure'])
def test_budgets(tmp_path,monkeypatch,case):
    f=Fixture(tmp_path);baseline=f.file('baseline.txt','x');source=f.add(tmp_path/'docs');f.refresh(source)
    old=f.search('x')['results'][0]['reference']
    if case.startswith('single'):
        n=2*MIB+(case=='single-over');f.file('large.txt',raw=b'needle '+b' '*(n-7))
    elif case.startswith('count'):
        count=1000+(case=='count-over')
        for i in range(count-1):f.file(f'item-{i:04d}.txt','needle')
    elif case.startswith('total'):
        for i in range(8):
            n=2*MIB if i<7 else 2*MIB-1+(case=='total-over')
            f.file(f'large-{i}.txt',raw=b'needle '+b' '*(n-7))
    elif case.startswith('mixed'):
        prefix='aaa' if case=='mixed-first' else 'zzz'
        f.file(prefix+'-large.txt',raw=b'x'*(17*MIB))
        f.file(prefix+'-encoding.txt',raw=b'\xff\xfe')
        denied=f.file(prefix+'-denied.txt','unreadable')
        original=os.open
        def reject(path,*a,**kw):
            if str(path)==str(denied.resolve()):raise PermissionError('synthetic access rejected')
            return original(path,*a,**kw)
        monkeypatch.setattr(os,'open',reject)
    elif case.startswith('invalid-total'):
        for i in range(8):
            raw=(b'\xff' if i==0 else b'\x00' if i==1 else b'n')*(2*MIB)
            f.file(f'item-{i}.txt',raw=raw)
        denied=tmp_path/'docs'/'item-2.txt';original=os.open
        def reject(path,*a,**kw):
            if str(path)==str(denied.resolve()):raise PermissionError('synthetic read denied')
            return original(path,*a,**kw)
        monkeypatch.setattr(os,'open',reject)
    else:f.file('stat-failed.txt','not billed')
    originals={p.name:fingerprint(p) for p in (tmp_path/'docs').iterdir()}
    candidates=len(originals);bill=sum(x['bytes'] for x in originals.values() if x['bytes']<=2*MIB)
    if case=='stat-failure':
        bill-=originals['stat-failed.txt']['bytes'];original_stat=Path.stat
        def fail_stat(path,*a,**kw):
            if path==tmp_path/'docs'/'stat-failed.txt':raise PermissionError('synthetic stat denied')
            return original_stat(path,*a,**kw)
        monkeypatch.setattr(Path,'stat',fail_stat)
    if case.endswith(('first','last')):
        scandir=os.scandir;orders=[]
        class Ordered:
            def __init__(self,path):
                with scandir(path) as entries:self.entries=sorted(entries,key=lambda e:e.name,reverse=case.endswith('last'))
                orders.append([e.name for e in self.entries])
            def __enter__(self):return iter(self.entries)
            def __exit__(self,*a):pass
            def __iter__(self):return iter(self.entries)
            def close(self):pass
        monkeypatch.setattr(os,'scandir',Ordered)
    f.refresh(source);s=f.source(source);files=f.files(source)
    monkeypatch.undo()
    if case.endswith(('first','last')):assert orders and orders[0]==sorted(originals,reverse=case.endswith('last'))
    observe('budget-actual',{'case':case,'source':s,'actual_candidates':candidates,'actual_billed_bytes':bill,'source_bytes':originals,'files':files})
    assert s['counts']['candidates']==candidates and s['counts']['billed_bytes']==bill
    assert {p.name:fingerprint(p) for p in (tmp_path/'docs').iterdir()}==originals
    if case in ['count-over','total-over'] or case.startswith('invalid-total'):
        assert s['status']=='failed' and s['error']
        assert f.search('x needle',limit=50)['results']==[]
        f.bad('POST','/api/documents/read',{'reference':old})
    else:
        expected_fail=1 if case in ['single-over','stat-failure'] else 3 if case.startswith('mixed') else 0
        assert s['status']==('partial' if expected_fail else 'ready')
        assert s['counts']['ready']==candidates-expected_fail and s['counts']['failed']==expected_fail
        assert f.read(old)['text']=='x'
        results=f.search('x needle',limit=50)['results']
        assert len(results)==min(50,candidates-expected_fail)
        assert all(Path(x['path']).name=='baseline.txt' for x in results) if case.startswith('mixed') else True
        if case=='count-equal':
            assert {Path(x['path']).name for x in files if x['status']=='ready'}==set(originals)
        if case=='stat-failure':
            bad=next(x for x in files if Path(x['path']).name=='stat-failed.txt')
            assert bad['status']=='failed' and 'stat' in bad['error'].lower()
    if case=='single-equal':assert originals['large.txt']['bytes']==2*MIB
    if case=='single-over':assert originals['large.txt']['bytes']==2*MIB+1
    if case=='count-equal':assert candidates==1000
    if case=='count-over':assert candidates==1001
    if case=='total-equal':assert bill==16*MIB
    if case=='total-over':assert bill==16*MIB+1
    for path in (tmp_path/'docs').iterdir():
        if path.name!='baseline.txt':path.unlink()
    f.refresh(source)
    recovered=f.search('x')['results']
    assert f.source(source)['status']=='ready' and f.source(source)['counts']['ready']==1
    assert len(recovered)==1 and f.read(recovered[0])['text']=='x'
    if case in ['count-over','total-over'] or case.startswith('invalid-total'):
        f.bad('POST','/api/documents/read',{'reference':old})
    else:assert f.read(old)['text']=='x'


@pytest.mark.parametrize('case',['before-open-single','before-open-total','during-read','path-replace','enumeration'])
def test_read_races(tmp_path,monkeypatch,case):
    f=Fixture(tmp_path);n=9 if case=='before-open-total' else 1
    paths=[f.file(f'racy-{i}.txt',f'racyneedle initial {i}') for i in range(n)]
    control=f.file('z-control.txt','controlneedle unchanged');source=f.add(tmp_path/'docs');f.refresh(source)
    old={Path(h['path']).name:h for h in f.search('racyneedle controlneedle',limit=50)['results']}
    assert len(old)==n+1
    from smm_local import documents as module
    events=[]
    if case.startswith('before-open'):
        original=module._read_file
        def change(*a,**kw):
            if not events:
                events.append('after-budget-before-open')
                for p in paths:p.write_bytes(b'x'*(2*MIB+(case=='before-open-single')))
            return original(*a,**kw)
        with monkeypatch.context() as patch:
            patch.setattr(module,'_read_file',change);f.refresh(source)
    elif case in ['during-read','path-replace']:
        original=os.fstat;inode=paths[0].stat().st_ino
        def change(fd):
            s=original(fd)
            if s.st_ino==inode and not events:
                events.append('during-opened-read')
                if case=='during-read':paths[0].write_text('different body after fstat',encoding='utf-8')
                else:
                    replacement=tmp_path/'replacement';replacement.write_text('replaced path body',encoding='utf-8');os.replace(replacement,paths[0])
            return s
        with monkeypatch.context() as patch:
            patch.setattr(os,'fstat',change);f.refresh(source)
    else:
        original=os.scandir
        def fail(path):
            if str(path)==str((tmp_path/'docs').resolve()):
                events.append('enumeration-error');raise PermissionError('synthetic enumeration denied')
            return original(path)
        with monkeypatch.context() as patch:
            patch.setattr(os,'scandir',fail);f.refresh(source)
    assert events
    s=f.source(source)
    if case=='enumeration':
        assert s['status']=='failed' and f.search('racyneedle controlneedle')['results']==[]
        assert not any(x['status']=='missing' for x in f.files(source))
    else:
        assert s['status']=='partial' and s['counts']['failed']==n and s['counts']['ready']==1
        assert f.texts(f.search('racyneedle controlneedle',limit=50))=={'z-control.txt':'controlneedle unchanged'}
    for name,h in old.items():
        if name!='z-control.txt' or case=='enumeration':f.bad('POST','/api/documents/read',{'reference':h['reference']})
        else:assert f.read(h)['text']=='controlneedle unchanged'
    observe('read-race-observation',{'case':case,'events':events,'after':s,'sizes':{p.name:p.stat().st_size for p in paths}})
    f.refresh(source)
    if case=='before-open-total':
        assert f.source(source)['status']=='failed' and f.search('controlneedle')['results']==[]
    for i,p in enumerate(paths):p.write_text(f'racyneedle initial {i}',encoding='utf-8')
    f.refresh(source);assert f.source(source)['status']=='ready'
    assert len(f.search('racyneedle controlneedle',limit=50)['results'])==n+1
    # Once terminally rejected, the old qualification cannot revive even with identical bytes.
    for name,h in old.items():
        if name!='z-control.txt' or case in ['enumeration','before-open-total']:
            f.bad('POST','/api/documents/read',{'reference':h['reference']})
        else:assert f.read(h)['text']=='controlneedle unchanged'

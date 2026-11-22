import base64
import json
import math
from pathlib import Path
import pytest
from document_helpers import Fixture, normal, observe, deny_source_reads


def test_search_rank(tmp_path):
    f=Fixture(tmp_path)
    for i in range(51):f.file(f'file-{i:03d}.md','needle common')
    f.file('needle-only-filename.txt','unrelated document')
    special={'tail.txt':'padding '*1000+'tailuniquemarker',
             'boundary.txt':'x '*997+' crossboundaryword ending',
             'long.txt':'padding '*1800+'longuniquemarker suffix',
             'chinese.txt':'说明：中文检索资料，保留原始内容。',
             'a-low.txt':'relevancemarker '+'dilution '*500,
             'z-high.txt':'relevancemarker relevancemarker relevancemarker'}
    for name,text in special.items():f.file(name,text)
    source=f.add(tmp_path/'docs');f.refresh(source)
    duplicate=f.add(tmp_path/'docs'/'file-000.md');f.refresh(duplicate)
    first=f.search('needle',limit=1)['results'];fifty=f.search('needle',limit=50)['results']
    assert len(first)==1 and Path(first[0]['path']).name=='file-000.md'
    assert [Path(h['path']).name for h in fifty]==[f'file-{i:03d}.md' for i in range(50)]
    assert len({h['id'] for h in fifty})==50
    assert [(h['id'],h['bm25_score']) for h in fifty]==[(h['id'],h['bm25_score']) for h in f.search('needle',limit=50)['results']]
    assert all(math.isfinite(h['bm25_score']) for h in fifty)
    ranked=f.search('relevancemarker')['results']
    assert [Path(h['path']).name for h in ranked]==['z-high.txt','a-low.txt']
    for filename,query in [('tail.txt','tailuniquemarker'),('boundary.txt','crossboundaryword'),('long.txt','longuniquemarker'),('chinese.txt','中文检索')]:
        result=f.search(query)['results'];assert len(result)==1 and Path(result[0]['path']).name==filename
        h=result[0];read=f.read(h);text=special[filename]
        assert read['text']==text[h['start']:h['end']] and query in read['text'] and len(read['text'])<=2000
        assert h['text']==read['text'] and h['end']<=len(text)
    observe('rank-independent-expected',{'tie_paths':[f'file-{i:03d}.md' for i in range(50)],'special':special,'first':first,'fifty':fifty})


@pytest.mark.parametrize('text',['needle 😀 e\u0301\r\n第二行\r末行\n','needle 😀 e\u0301\nlast','a\nb\nneedle\n'])
def test_exact_read(tmp_path,monkeypatch,text):
    f=Fixture(tmp_path);path=f.file('位置.md','\ufeff'+text);source=f.add(path);f.refresh(source)
    h=f.search('needle')['results'][0];body=normal('\ufeff'+text)
    deny_source_reads(monkeypatch,path)
    default=f.read(h)
    assert h['start']==0 and h['end']==len(body) and h['text_length']==len(body)
    assert h['text']==default['text']==body
    for item in [h,default]:
        assert item['start']==0 and item['end']==len(body)
        assert item['start_line']==1 and item['end_line']==1+body[:-1].count('\n')
    for start,end in [(0,len(body)),(0,2),(1,3),(2,min(4,len(body))),(len(body)-1,len(body))]:
        r=f.read(h,start=start,end=end)
        assert r['text']==body[start:end] and r['start']==start and r['end']==end
        assert r['start_line']==1+body[:start].count('\n')
        assert r['end_line']==1+body[:end-1].count('\n')
    monkeypatch.undo()
    long='needle '+('😀e\u0301 x'*4000)
    path.write_text(long,encoding='utf-8');f.refresh(source);current=f.search()['results'][0]
    assert len(f.read(current)['text'])<=2000
    r=f.read(current,start=0,end=16000);assert r['text']==long[:16000] and len(r['text'])==16000
    f.bad('POST','/api/documents/read',{'reference':current['reference'],'start':0,'end':16001})
    f.bad('POST','/api/documents/read',{'reference':h['reference']})
    observe('coordinate-independent-expected',{'original':text,'normalized':body,'long_length':len(long),'first16000_sha_expected':__import__('hashlib').sha256(long[:16000].encode()).hexdigest()})


def test_invalid_read(tmp_path,monkeypatch):
    f=Fixture(tmp_path);paths=[f.file('one.txt','needle alpha 😀 e\u0301\nsecond\n'),f.file('two.txt','needle beta')]
    source=f.add(tmp_path/'docs');f.refresh(source);h=f.search('alpha')['results'][0];other=f.search('beta')['results'][0]
    foreign=Fixture(tmp_path/'foreign');foreign_source=foreign.add(foreign.file('foreign.txt','needle foreign'));foreign.refresh(foreign_source)
    foreign_ref=foreign.search()['results'][0]['reference'];f.bad('POST','/api/documents/read',{'reference':foreign_ref})
    prefix,encoded,signature=h['reference'].split('.')
    payload=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
    assert payload['kind']=='document' and payload['document_id']==h['id'] and payload['version']==h['version']
    def tamper(p):return prefix+'.'+base64.urlsafe_b64encode(json.dumps(p,ensure_ascii=False).encode()).decode().rstrip('=')+'.'+signature
    changes={'archive_id':['another-valid-looking-archive','invalid'],
             'document_id':[other['id'],'no-such-document'],
             'version':[h['version']+1,-1], 'kind':['citation','invalid']}
    deny_source_reads(monkeypatch,*paths)
    for field,values in changes.items():
        for value in values:
            mutated=json.loads(json.dumps(payload));assert mutated[field]!=value;mutated[field]=value
            f.bad('POST','/api/documents/read',{'reference':tamper(mutated)})
    for field in ['id','revision','qualification']:
        for invalid in [False,True]:
            mutated=json.loads(json.dumps(payload));stamp=mutated['sources'][0]
            stamp[field]=('unavailable-source' if invalid else foreign_source['id']) if field=='id' else (-1 if invalid else stamp[field]+1)
            f.bad('POST','/api/documents/read',{'reference':tamper(mutated)})
    for start,end in [(-1,2),(2,1),(1,1),(0,h['text_length']+1),(True,2),(0,2.5)]:
        f.bad('POST','/api/documents/read',{'reference':h['reference'],'start':start,'end':end})
    assert f.read(h)['text']=='needle alpha 😀 e\u0301\nsecond\n'
    # A real signed conversation citation from the same archive is a different kind.
    from document_helpers import seed_conversation
    conversation=seed_conversation(f)['reference']
    f.bad('POST','/api/documents/read',{'reference':conversation})
    monkeypatch.undo()
    f.set(source,project_ids=[]);f.refresh(source)
    f.bad('POST','/api/documents/read',{'reference':h['reference']})
    fresh=f.search('alpha')['results'][0];assert f.read(fresh)['text']=='needle alpha 😀 e\u0301\nsecond\n'


def test_empty_query(tmp_path):
    f=Fixture(tmp_path);p=f.project('P')
    empty=f.search('nonexistentuniqueterm')
    assert empty['results']==[] and empty['coverage']['indexed_files']==0 and empty['coverage']['sources']==[]
    path=f.file('one.txt','needle real');source=f.add(path,[p])
    untouched=f.add(f.file('untouched.txt','needle pending'),[p])
    def states(result):return {s['id']:s['status'] for s in result['coverage']['sources']}
    pending=f.search('nonexistentuniqueterm');assert pending['results']==[]
    assert pending['coverage']['indexed_files']==0 and states(pending)=={source['id']:'pending',untouched['id']:'pending'}
    for args in [{'query':''},{'query':'  '},{'query':'!!!'},{'query':'needle','scope':'invalid'},
                 {'query':'needle','scope':'project'},{'query':'needle','scope':'project','project_id':99999},
                 *[{'query':'needle','limit':x} for x in [0,-1,51,2.5,True]]]:
        f.bad('POST','/api/documents/search',args)
    f.refresh(source)
    valid=f.search('nonexistentuniqueterm');assert valid['results']==[] and valid['coverage']['indexed_files']==1
    assert states(valid)=={source['id']:'ready',untouched['id']:'pending'}
    path.write_bytes(b'\xff\xfe');f.refresh(source)
    partial=f.search('nonexistentuniqueterm');assert partial['results']==[] and partial['coverage']['indexed_files']==0
    assert states(partial)=={source['id']:'partial',untouched['id']:'pending'}
    with f.db.connect() as c:c.execute("UPDATE document_sources SET status='refreshing' WHERE id=?",(source['id'],))
    refreshing=f.search('nonexistentuniqueterm');assert states(refreshing)=={source['id']:'refreshing',untouched['id']:'pending'}
    assert refreshing['coverage']['indexed_files']==0
    path.unlink()
    f.refresh(source);failed=f.search('nonexistentuniqueterm')
    assert states(failed)=={source['id']:'failed',untouched['id']:'pending'} and failed['results']==[]
    observe('zero-hit-states',{'pending':pending,'ready':valid,'partial':partial,'refreshing':refreshing,'failed':failed})

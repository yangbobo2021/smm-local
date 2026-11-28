"""Real OCR quality and all-cell truth; skipped assets are never acceptance."""
import hashlib,json,re,os
from pathlib import Path
import pytest
from document_helpers import Fixture,fingerprint,observe,deny_source_reads
from document_formats_ocr_fixture import scanned_fixture
from test_document_formats_retry import ENGINE,DATA,FONT,keep,child_source_guard,cli

pytestmark=pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real OCR materials')


def normal(value):return re.sub(r'\s+','',value.replace('\r\n','\n'))


def distance(left,right):
    previous=list(range(len(right)+1))
    for i,a in enumerate(left,1):
        current=[i]
        for j,b in enumerate(right,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(a!=b)))
        previous=current
    return previous[-1]


def assert_box(actual,expected):
    assert len(actual)==4 and all(0<=v<=1 for v in actual)
    assert all(abs(a-b)<.01 for a,b in zip(actual,expected)),(actual,expected)


def test_two_scanned_pdfs_have_complete_text_and_tables(tmp_path,monkeypatch):
    # TC-008-pdf-ocr: no output from the product supplies any expected value.
    f=Fixture(tmp_path);project=f.project('008 OCR quality');items={}
    for key in ('alpha','beta'):
        raw,truth=scanned_fixture(FONT,key);path=f.file(key+'.pdf',raw=raw)
        keep('inputs/'+key+'.pdf',raw);keep('truth/'+key+'.json',json.dumps(truth,ensure_ascii=False).encode())
        items[path.name]={'path':path,'raw':raw,'truth':truth,'before':fingerprint(path)}
    status=cli(f,'processing-status')
    cli(f,'processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    source=f.add(f.root/'docs',projects=[project]);f.refresh(source)
    files=f.files(source);assert len(files)==2 and {Path(e['path']).name for e in files}==set(items)
    assert all(e['status']=='ready' for e in files),files
    for item in items.values():assert fingerprint(item['path'])==item['before']
    parent=deny_source_reads(monkeypatch,*[e['path'] for e in items.values()])
    audit=child_source_guard(f.root,[e['path'] for e in items.values()],monkeypatch)
    hits=f.search('ALPHA BETA',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==len({h['id'] for h in hits})==2 and {Path(h['path']).name for h in hits}==set(items)
    for hit in hits:
        item=items[Path(hit['path']).name];truth=item['truth']
        result=f.read(hit,start=0,end=hit['text_length']);actual=normal(result['text']);expected=normal(truth['text'])
        cer=distance(expected,actual)/len(expected);assert cer<=.01,(cer,expected,actual)
        assert hit['sha256']==item['before']['sha256']
        assert result['coverage']['errors']==[]
        assert len(result['tables'])==len({t['table_id'] for t in result['tables']})==2
        views=[]
        for page in truth['pages']:
            number=page['page'];assert normal(page['title']) in actual
            for field,region_field in [('title','title_region'),('paragraph','paragraph_region')]:
                expected=normal(page[field]);region=page[region_field]
                locs=[loc for loc in result['locations'] if loc['page']==page['page'] and normal(result['text'][loc['start']:loc['end']])==expected]
                assert len(locs)==1,(page,field,locs)
                rect=locs[0]['bbox'];assert len(rect)==4 and region[0]-.01<=rect[0]<rect[2]<=region[2]+.01 and region[1]-.01<=rect[1]<rect[3]<=region[3]+.01
                found=f.search(page[field],scope='project',project_id=project,local=True,limit=50)['results']
                own=[value for value in found if value['id']==hit['id']];assert len(own)==1
                located=[loc for loc in own[0]['locations'] if loc['page']==page['page'] and normal(result['text'][loc['start']:loc['end']])==expected]
                assert len(located)==1 and located[0]['bbox']==rect
            page_locations=[v for v in result['locations'] if v['page']==number]
            assert page_locations and all(v['method']=='ocr' and 0<=v['confidence']<=100 for v in page_locations)
            matches=[t for t in result['tables'] if t['location']['page']==number];assert len(matches)==1
            table=matches[0];assert_box(table['location']['bbox'],page['bbox'])
            view=f.read(hit,view='table',table_id=table['table_id']);views.append(view)
            assert (view['rows'],view['columns'])==(3,2)
            cells={(v['row'],v['column']):v for v in view['cells']};assert len(cells)==len(view['cells'])==6
            assert set(cells)=={(r,c) for r in range(1,4) for c in range(1,3)}
            for wanted in page['cells']:
                cell=cells[wanted['row'],wanted['column']]
                assert normal(cell['text'])==normal(wanted['text'])
                assert (cell['row_span'],cell['column_span'])==(1,1)
                assert cell['location']['page']==number and cell['location']['method']=='ocr'
                assert_box(cell['location']['bbox'],wanted['bbox'])
                matches=f.search(wanted['text'],scope='project',project_id=project,local=True,limit=50)['results']
                own=[v for v in matches if v['id']==hit['id']];assert len(own)==1
                locs=[v for v in own[0]['locations'] if v['page']==number and normal(result['text'][v['start']:v['end']])==normal(wanted['text'])]
                assert len(locs)==1;assert_box(locs[0]['bbox'],wanted['bbox'])
            assert view['header_context']['role']=='first_content_row'
            assert {(v['row'],v['column'],normal(v['text'])) for v in view['header_context']['cells']}=={(1,c+1,normal(t)) for c,t in enumerate(page['rows'][0])}
        download=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert download.status_code==200 and download.content==item['raw'];keep('downloads/'+item['path'].name,download.content)
        # Actual source fingerprints may be taken after removing the guard below.
        observe('ocr-complete-'+truth['key'],{'hit':hit,'read':result,'tables':views,'cer':cer,'original':item['before']})
    assert parent==[] and (not audit.exists() or audit.read_text()=='')


def test_ocr_truth_and_distance_reject_mutations():
    assert distance(normal('中文 A\r\n 123.45'),normal('中文A123.45'))==0
    assert distance('123.45','123.46')==1
    for key in ('alpha','beta'):
        raw,truth=scanned_fixture(FONT,key)
        assert raw.startswith(b'%PDF-') and len(truth['pages'])==2
        assert len([v for p in truth['pages'] for v in p['cells']])==12
        expected=normal(truth['text']);wrong=expected.replace(normal(truth['pages'][1]['cells'][-1]['text']),'WRONG')
        assert distance(expected,wrong)/len(expected)>.01

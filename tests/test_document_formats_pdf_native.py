"""Native PDF extraction and zero OCR subprocesses at public archive routes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import pdfplumber
from io import BytesIO
from document_helpers import Fixture,fingerprint,observe
from document_formats_pdf_fixture import native_pdf,WIDTH,HEIGHT


def prepare_audit(root,monkeypatch):
    directory=root/'audit';directory.mkdir();log=directory/'subprocess.jsonl'
    code=r'''import json,os,sys
from pathlib import Path
def audit(event,args):
    if event=='subprocess.Popen':
        with open(os.environ['SMM_TEST_PROCESS_LOG'],'a',encoding='utf-8') as out:out.write(json.dumps({'event':event,'executable':str(args[0]),'argv':str(args[1])})+'\n')
        raise RuntimeError('native PDF must not launch OCR/subprocess')
sys.addaudithook(audit)
'''
    (directory/'sitecustomize.py').write_text(code,encoding='utf-8')
    monkeypatch.setenv('PYTHONPATH',str(directory)+os.pathsep+os.environ.get('PYTHONPATH',''))
    monkeypatch.setenv('SMM_TEST_PROCESS_LOG',str(log))
    ok=subprocess.run([sys.executable,'-c','print("audit-ready")'],capture_output=True,text=True,timeout=10)
    assert ok.returncode==0 and ok.stdout.strip()=='audit-ready' and not ok.stderr
    denied=subprocess.run([sys.executable,'-c','import subprocess;subprocess.run(["tesseract","--version"])'],capture_output=True,text=True,timeout=10)
    assert denied.returncode!=0 and 'native PDF must not launch' in denied.stderr
    rows=[json.loads(line) for line in log.read_text().splitlines()]
    assert len(rows)==1 and rows[0]['executable']=='tesseract'
    log.unlink();return log


def assert_bbox(actual,expected):
    assert len(actual)==len(expected)==4
    assert all(0<=x<=1 for x in actual)
    assert all(abs(a-b)<=0.002 for a,b in zip(actual,expected)),(actual,expected)



def assert_native_order(text,truth):
    assert all(text.count(word)==1 for word in truth['order'])
    positions=[text.index(word) for word in truth['order']]
    assert positions==sorted(positions), (truth['order'],positions)

def test_native_pdf_all_pages_grids_without_ocr(tmp_path,monkeypatch):
    # TC-008-pdf-native
    log=prepare_audit(tmp_path,monkeypatch)
    f=Fixture(tmp_path/'archive');project=f.project('008 PDF');items={}
    for key in ('nativealpha','nativebeta'):
        raw,truth=native_pdf(key);path=f.file(key+'.pdf',raw=raw)
        items[path.name]={'raw':raw,'path':path,'truth':truth,'before':fingerprint(path)}
    source=f.add(f.root/'docs',projects=[project]);refreshed=f.refresh(source)
    assert refreshed['sources'][0]['counts']['ready']==2,'both native PDFs must work with OCR forbidden'
    hits=f.search('nativealpha nativebeta',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==2 and {Path(h['path']).name for h in hits}==set(items)
    for hit in hits:
        item=items[Path(hit['path']).name];truth=item['truth']
        assert hit['format']=='pdf' and hit['original_available'] is True
        result=f.read(hit,start=0,end=hit['text_length'])
        assert_native_order(result['text'],truth)
        assert len(result['tables'])==len({t['table_id'] for t in result['tables']})==sum(len(p['tables']) for p in truth['pages'])==3
        by_page={p:[t for t in result['tables'] if t['location']['page']==p] for p in (1,2)}
        assert {t['location']['page'] for t in result['tables']}=={1,2}
        units=result['coverage']['units'];assert {u['page'] for u in units}=={1,2}
        assert all(u['method']=='native' and u['status']=='ready' for u in units)
        views=[]
        for page in truth['pages']:
            for paragraph in page['paragraphs']:
                anchor=paragraph['text'];assert result['text'].count(anchor)==1
                found=f.search(anchor,scope='project',project_id=project,local=True,limit=50)['results']
                selected=[h for h in found if h['id']==hit['id']];assert len(selected)==1
                locs=[loc for loc in result['locations'] if result['text'][loc['start']:loc['end']]==anchor]
                assert len(locs)==1 and locs[0]['page']==page['page'] and locs[0]['method']=='native'
                assert locs[0]['page_width']==page['width'] and locs[0]['page_height']==page['height']
                x0,y0,x1,y1=locs[0]['bbox'];assert 0<=x0<x1<=1 and 0<=y0<y1<=1
                assert abs(x0-72/page['width'])<0.002
                assert paragraph['top_min']/page['height']<y0<y1<paragraph['top_max']/page['height']
                assert y1-y0<0.04 and x1-x0<0.75
                assert any(loc['page']==page['page'] and loc['start']==locs[0]['start'] and loc['end']==locs[0]['end'] and loc['bbox']==locs[0]['bbox'] for loc in selected[0]['locations'])
            assert len(by_page[page['page']])==len(page['tables'])
            for expected_table in page['tables']:
                candidates=[t for t in by_page[page['page']] if all(abs(a-b)<0.002 for a,b in zip(t['location']['bbox'],expected_table['bbox']))]
                assert len(candidates)==1;table=candidates[0]
                assert_bbox(table['location']['bbox'],expected_table['bbox'])
                view=f.read(hit,view='table',table_id=table['table_id']);views.append(view)
                assert view['table_id']==table['table_id'] and view['rows']==expected_table['rows'] and view['columns']==expected_table['columns']
                cells={(cell['row'],cell['column']):cell for cell in view['cells']}
                assert len(cells)==len(view['cells'])==6 and set(cells)=={(r,c) for r in range(1,4) for c in range(1,3)}
                for expected in expected_table['cells']:
                    cell=cells[(expected['row'],expected['column'])]
                    assert cell['text']==expected['text'] and result['text'].count(expected['text'])==1
                    assert cell['location']['page']==page['page']
                    assert (cell['row_span'],cell['column_span'])==(1,1)
                    assert_bbox(cell['location']['bbox'],expected['bbox'])
                    matched=f.search(expected['text'],scope='project',project_id=project,local=True,limit=50)['results']
                    same=[value for value in matched if value['id']==hit['id']];assert len(same)==1
                    anchored=[loc for loc in same[0]['locations'] if loc['page']==page['page'] and result['text'][loc['start']:loc['end']]==expected['text']]
                    assert len(anchored)==1;assert_bbox(anchored[0]['bbox'],expected['bbox'])
                assert view['header_context']['role']=='first_content_row'
                assert {(c['row'],c['column'],c['text']) for c in view['header_context']['cells']}=={(e['row'],e['column'],e['text']) for e in expected_table['cells'] if e['row']==1}
        download=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert download.status_code==200 and download.content==item['raw']
        assert hashlib.sha256(download.content).hexdigest()==hit['sha256']
        assert fingerprint(item['path'])==item['before']
        observe('pdf-native-'+truth['key'],{'hit':hit,'read':result,'tables':views,'original':item['before']})
    assert not log.exists() or log.read_text()=='','native PDF launched forbidden subprocess'


def test_native_pdf_fixture_has_independent_pages_and_cells():
    for key in ('nativealpha','nativebeta'):
        raw,truth=native_pdf(key)
        with pdfplumber.open(BytesIO(raw)) as pdf:
            assert len(pdf.pages)==len(truth['pages'])==2
            for page,expected in zip(pdf.pages,truth['pages']):
                assert page.width==expected['width'] and page.height==expected['height']
                assert page.rotation==expected['rotation']
                for paragraph in expected['paragraphs']:assert paragraph['text'] in page.extract_text()
                extracted=page.extract_tables()
                assert len(extracted)==len(expected['tables'])
                assert extracted==[[[e['text'] for e in table['cells'] if e['row']==r] for r in range(1,4)] for table in expected['tables']]


def test_native_pdf_audit_is_active(tmp_path,monkeypatch):
    log=prepare_audit(tmp_path,monkeypatch)
    assert not log.exists()


def test_native_order_observer_rejects_both_wrong():
    for key in ('nativealpha','nativebeta'):
        _,truth=native_pdf(key)
        assert_native_order('\n'.join(truth['order']),truth)
        wrong_page_order=[word for page in reversed(truth['pages']) for word in [*[p['text'] for p in page['paragraphs']],*[cell['text'] for cell in page['cells']]]]
        with pytest.raises(AssertionError):assert_native_order('\n'.join(wrong_page_order),truth)
        wrong_cell_order=list(truth['order']);wrong_cell_order[-2],wrong_cell_order[-1]=wrong_cell_order[-1],wrong_cell_order[-2]
        with pytest.raises(AssertionError):assert_native_order('\n'.join(wrong_cell_order),truth)


def test_native_pdf_rotation_truth_rejects_raw_coordinates():
    angles=set()
    for key in ('nativealpha','nativebeta'):
        _,truth=native_pdf(key)
        for page in truth['pages']:
            angles.add(page['rotation']);correct=page['bbox'];assert_bbox(correct,correct)
            if page['rotation'] in (90,270):
                # Ignoring /Rotate uses the raw media box dimensions and axes.
                raw=([correct[1],1-correct[2],correct[3],1-correct[0]] if page['rotation']==90 else [1-correct[3],correct[0],1-correct[1],correct[2]])
                with pytest.raises(AssertionError):assert_bbox(raw,correct)
            elif page['rotation']==180:
                raw=[1-correct[2],1-correct[3],1-correct[0],1-correct[1]]
                with pytest.raises(AssertionError):assert_bbox(raw,correct)
    assert angles=={0,90,180,270}

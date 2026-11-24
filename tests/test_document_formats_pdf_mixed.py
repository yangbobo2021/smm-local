"""Mixed-page OCR complements native content; all source truth is independent."""
import csv,hashlib,io,json,re,subprocess,sys
from pathlib import Path
import pytest
from document_helpers import Fixture,fingerprint,observe,deny_source_reads
from document_formats_mixed_fixture import mixed_pdf
from document_formats_mixed_observer import install,records
from test_document_formats_retry import ENGINE,DATA,FONT,keep,cli
from test_document_formats_pdf_ocr import normal,distance,assert_box

pytestmark=pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real local OCR materials')


@pytest.fixture(autouse=True)
def preserve_observer_even_when_assertion_fails(tmp_path,request):
    yield
    folder=tmp_path/'mixed-observer'
    if folder.exists():
        label='selfcheck' if 'known_controls' in request.node.name else 'business'
        for path in folder.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:keep('observer/'+label+'/'+path.relative_to(folder).as_posix(),path.read_bytes())


def assert_dimensions(value,truth):
    pages={page['page']:page for page in truth['pages']}
    locations=[*value.get('locations',[]),*[table['location'] for table in value.get('tables',[])],*[cell['location'] for cell in value.get('cells',[])]]
    if 'location' in value:locations.append(value['location'])
    assert locations
    for loc in locations:
        wanted=pages[loc['page']]
        assert loc['page_width']==wanted['width'] and loc['page_height']==wanted['height']


def test_dimensions_guard_rejects_later_page_and_consistent_wrong_views():
    import copy
    truth={'pages':[{'page':p,'width':240,'height':216} for p in (1,2,3)]}
    good={'locations':[{'page':p,'page_width':240,'page_height':216} for p in (1,2,3)]}
    assert_dimensions(good,truth)
    for field in ('page_width','page_height'):
        wrong=copy.deepcopy(good);wrong['locations'][1][field]=1
        for view in (wrong,copy.deepcopy(wrong)):
            with pytest.raises(AssertionError):assert_dimensions(view,truth)


def assert_region(read,start,end,page,method,region):
    expected={i for i in range(start,end) if not read['text'][i].isspace()};covered=set()
    locs=[loc for loc in read['locations'] if loc['start']<end and loc['end']>start]
    assert locs
    for loc in locs:
        assert loc['page']==page and loc['method']==method
        bbox=loc['bbox'];assert len(bbox)==4 and region[0]-.01<=bbox[0]<bbox[2]<=region[2]+.01 and region[1]-.01<=bbox[1]<bbox[3]<=region[3]+.01
        covered.update(range(max(start,loc['start']),min(end,loc['end'])))
    assert expected.issubset(covered)
    return locs


def test_two_mixed_pdfs_preserve_native_and_ocr_regions(tmp_path,monkeypatch):
    # TC-008-pdf-mixed: both documents, later pages and later tables are checked.
    f=Fixture(tmp_path);project=f.project('008 mixed PDFs');items={}
    for key in ('mixedalpha','mixedbeta'):
        raw,truth=mixed_pdf(key,FONT);path=f.file(key+'.pdf',raw=raw)
        items[path.name]={'path':path,'raw':raw,'truth':truth,'before':fingerprint(path)}
        keep('inputs/'+path.name,raw);keep('truth/'+path.stem+'.json',json.dumps(truth,ensure_ascii=False).encode())
    config=cli(f,'processing-status');cli(f,'processing-configure','--expected-revision',config['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    log,observed_files=install(tmp_path,monkeypatch)
    source=f.add(f.root/'docs',projects=[project]);f.refresh(source)
    files=f.files(source);assert len(files)==2 and {Path(value['path']).name for value in files}==set(items)
    assert all(value['published_snapshot']['status']=='ready' for value in files),files
    for item in items.values():assert fingerprint(item['path'])==item['before']
    before_events=records(log);attempts=deny_source_reads(monkeypatch,*[v['path'] for v in items.values()])
    observed_ids=set()
    for name,item in items.items():
        truth=item['truth'];hits=f.search(truth['pages'][0]['heading'],scope='project',project_id=project,local=True,limit=50)['results']
        own=[value for value in hits if Path(value['path']).name==name];assert len(own)==1;hit=own[0];observed_ids.add(hit['id'])
        read=f.read(hit,start=0,end=hit['text_length']);assert_dimensions(read,truth);assert_dimensions(hit,truth);expected=normal(truth['text']);actual=normal(read['text'])
        cer=distance(expected,actual)/len(expected);assert cer<=.01,(name,cer,expected,actual)
        assert read['coverage']['errors']==[] and len(read['tables'])==len({t['table_id'] for t in read['tables']})==3
        for page in truth['pages']:
            heading=page['heading'];assert read['text'].count(heading)==1
            start=read['text'].index(heading);end=start+len(heading)
            locs=assert_region(read,start,end,page['page'],'native',page['heading_bbox'])
            matched=f.search(heading,scope='project',project_id=project,local=True,limit=50)['results']
            selected=[value for value in matched if value['id']==hit['id']];assert len(selected)==1
            assert_dimensions(selected[0],truth);assert any(loc in selected[0]['locations'] for loc in locs)
            if page['page']<3:
                next_heading=truth['pages'][page['page']]['heading'];section_end=read['text'].index(next_heading)
                indices=[i for i in range(end,section_end) if not read['text'][i].isspace()]
                section=''.join(read['text'][i] for i in indices)
                for field in ('title','paragraph'):
                    value=normal(page[field]);offset=section.index(value)
                    assert section.count(value)==1
                    assert_region(read,indices[offset],indices[offset+len(value)-1]+1,page['page'],'ocr',[.09,140/900,.95,310/900])
            rect=locs[0]['bbox'];bounds=page['heading_bbox'];assert bounds[0]<=rect[0]<rect[2]<=bounds[2] and bounds[1]<=rect[1]<rect[3]<=bounds[3]
            tables=[table for table in read['tables'] if table['location']['page']==page['page']];assert len(tables)==len(page['tables'])
            for wanted in page['tables']:
                matching=[t for t in tables if all(abs(a-b)<.01 for a,b in zip(t['location']['bbox'],wanted['bbox']))];assert len(matching)==1
                table=matching[0];assert table['rows']==wanted['rows'] and table['columns']==wanted['columns']
                view=f.read(hit,view='table',table_id=table['table_id']);assert_dimensions(view,truth)
                assert view['table_id']==table['table_id'] and view['location']['page']==page['page']
                assert_box(view['location']['bbox'],wanted['bbox'])
                assert view['rows']==wanted['rows'] and view['columns']==wanted['columns'] and view['location']['method']=='ocr'
                cells={(c['row'],c['column']):c for c in view['cells']};assert len(cells)==len(view['cells'])==len(wanted['cells'])
                for expected_cell in wanted['cells']:
                    cell=cells[(expected_cell['row'],expected_cell['column'])]
                    assert cell['text']==expected_cell['text'] and cell['row_span']==cell['column_span']==1
                    assert cell['location']['page']==page['page'] and cell['location']['method']=='ocr';assert_box(cell['location']['bbox'],expected_cell['bbox'])
                    found=f.search(expected_cell['text'],scope='project',project_id=project,local=True,limit=50)['results']
                    own_hit=[value for value in found if value['id']==hit['id']];assert len(own_hit)==1;assert_dimensions(own_hit[0],truth)
                    located=[loc for loc in own_hit[0]['locations'] if loc['page']==page['page'] and read['text'][loc['start']:loc['end']]==expected_cell['text'] and all(abs(a-b)<.01 for a,b in zip(loc['bbox'],expected_cell['bbox']))]
                    assert len(located)==1 and located[0]['method']=='ocr'
                assert view['header_context']['role']=='first_content_row'
                assert sorted(view['header_context']['cells'],key=lambda c:c['column'])==[cells[(1,c)] for c in range(1,wanted['columns']+1)]
        response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert response.status_code==200 and response.content==item['raw'];keep('downloads/'+name,response.content)
        assert hit['sha256']==hashlib.sha256(response.content).hexdigest()
        observe('mixed-'+name,{'hit':hit,'read':read,'cer':cer,'original':item['before']})
    assert len(observed_ids)==2 and attempts==[] and records(log)==before_events
    completed=[event for event in before_events if event['kind']=='ocr-result'];assert completed
    for item in items.values():
        source_sha=item['before']['sha256'];own=[event for event in completed if event['source_sha256']==source_sha]
        assert own and {int(re.fullmatch(r'ocr-page-(\d+)-region-\d+\.png',event['input_name']).group(1)) for event in own}=={1,2}
        for event in own:
            assert event['exit_code']==0
            output=Path(event['stdout_file']).read_bytes();assert hashlib.sha256(output).hexdigest()==event['stdout_sha256']
            words=''.join(word.get('text','') for word in csv.DictReader(io.StringIO(output.decode('utf-8')),delimiter='\t'))
            assert 'NATIVEHEADER' not in words.upper()
    assert {event['source_sha256'] for event in completed}=={item['before']['sha256'] for item in items.values()}
    keep('observer/events.json',json.dumps(before_events,ensure_ascii=False).encode())
    for path in observed_files.iterdir():keep('observer/files/'+path.name,path.read_bytes())


def test_mixed_ocr_observer_known_controls(tmp_path,monkeypatch):
    raw,truth=mixed_pdf('mixedalpha',FONT);source=tmp_path/'source.pdf';source.write_bytes(raw)
    image=tmp_path/'unregistered.png'
    from PIL import Image
    Image.new('RGB',(10,10),'white').save(image)
    log,files=install(tmp_path,monkeypatch)
    code='''import hashlib,json,subprocess,sys
from pathlib import Path
from smm_local.document_formats.pdf_guard import intermediate
import pypdfium2
root=Path(sys.argv[1]);engine,data=sys.argv[2:4]
try:subprocess.run([engine,str(root/'unregistered.png'),'stdout'],capture_output=True)
except AssertionError:pass
else:raise AssertionError('observer allowed OCR without a validated PDF')
intermediate((root/'source.pdf').read_bytes(),root/'validated.pdf')
with pypdfium2.PdfDocument(root/'validated.pdf') as document:
 page=document[2];bitmap=page.render(scale=300/72)
 bitmap.to_pil().save(root/'ocr-page-3-region-0.png');bitmap.close();page.close()
result=subprocess.run([engine,str(root/'ocr-page-3-region-0.png'),'stdout','--tessdata-dir',data,'-l','chi_sim+eng','--psm','11','-c','tessedit_create_tsv=1'],capture_output=True)
assert result.returncode==0
print(json.dumps({'stdout_sha256':hashlib.sha256(result.stdout).hexdigest()}))
'''
    result=subprocess.run([sys.executable,'-c',code,str(tmp_path),ENGINE,DATA],capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stderr
    events=records(log);rejected=[e for e in events if e['kind']=='ocr-rejected'];completed=[e for e in events if e['kind']=='ocr-result']
    assert len(rejected)==len(completed)==1
    event=completed[0];assert event['source_sha256']==hashlib.sha256(raw).hexdigest() and event['exit_code']==0
    observed=Path(event['stdout_file']).read_bytes();assert hashlib.sha256(observed).hexdigest()==json.loads(result.stdout)['stdout_sha256']
    assert 'NATIVEHEADER3' in ''.join(row.get('text','') for row in csv.DictReader(io.StringIO(observed.decode('utf-8')),delimiter='\t')).upper()
    keep('observer/selfcheck.json',json.dumps(events,ensure_ascii=False).encode())
    for path in files.iterdir():keep('observer/selfcheck/'+path.name,path.read_bytes())

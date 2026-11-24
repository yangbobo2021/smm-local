"""Public raster compatibility and bounded private PDF admission."""
from io import BytesIO
import hashlib,json,zlib
from pathlib import Path
import pytest
from PIL import Image,features
from document_helpers import Fixture,fingerprint,observe
from document_formats_pdf_security_fixture import raster,image_pdf
from test_document_formats_retry import ENGINE,DATA,FONT,keep,cli
from test_document_formats_pdf_ocr import normal
from document_formats_pdf_observer import install as install_reader_observer,records as reader_records


@pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real OCR assets')
@pytest.mark.parametrize('codec',['DCTDecode','JPXDecode','CCITTFaxDecode','FlateDecode'])
def test_supported_raster_codecs_and_inline_pdf(tmp_path,codec,monkeypatch):
    # TC-008-budgets: accepted raster types must pass through the guard.
    f=Fixture(tmp_path);project=f.project('008 safe raster');expected={}
    for key in ('alpha','beta'):
        raw,truth=raster(FONT,codec.lower()+key,codec);path=f.file(key+'.pdf',raw=raw)
        expected[path.name]={'raw':raw,'truth':truth,'before':fingerprint(path),'path':path};keep('inputs/'+codec+'-'+key+'.pdf',raw)
    status=cli(f,'processing-status');cli(f,'processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    observer=install_reader_observer(tmp_path,monkeypatch)
    source=f.add(f.root/'docs',projects=[project]);f.refresh(source)
    files=f.files(source);assert len(files)==2 and {Path(e['path']).name for e in files}==set(expected)
    assert all(entry['status']=='ready' for entry in files),files
    hits=f.search(codec.lower()+'alpha '+codec.lower()+'beta',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==len({h['id'] for h in hits})==2 and {Path(h['path']).name for h in hits}==set(expected)
    for hit in hits:
        item=expected[Path(hit['path']).name];read=f.read(hit,start=0,end=hit['text_length'])
        assert normal(read['text'])==normal(item['truth']['text'])
        assert read['coverage']['errors']==[] and read['locations']
        required={i for i,char in enumerate(read['text']) if not char.isspace()};covered=set()
        for loc in read['locations']:
            assert type(loc['start']) is int and type(loc['end']) is int and 0<=loc['start']<loc['end']<=len(read['text'])
            assert loc['method']=='ocr' and loc['page']==1 and 0<=loc['confidence']<=100
            bbox=loc['bbox'];assert len(bbox)==4 and all(0<=value<=1 for value in bbox) and bbox[0]<bbox[2] and bbox[1]<bbox[3]
            covered.update(range(loc['start'],loc['end']))
        assert required.issubset(covered)
        for line in item['truth']['lines']:
            found=f.search(line,scope='project',project_id=project,local=True,limit=50)['results']
            own=[value for value in found if value['id']==hit['id']];assert len(own)==1 and own[0]['locations']
            assert all(loc in read['locations'] for loc in own[0]['locations'])
        response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert response.status_code==200 and response.content==item['raw'];keep('downloads/'+codec+'-'+item['path'].name,response.content)
        assert fingerprint(item['path'])==item['before']
        observe('safe-raster-'+codec+'-'+item['path'].stem,{'hit':hit,'read':read,'original':item['before']})

    events=reader_records(observer);keep('observer/'+codec+'.json',json.dumps(events,ensure_ascii=False).encode())
    assert not any(event['kind']=='rejected' for event in events),events
    expected_shas={value['before']['sha256'] for value in expected.values()}
    for reader in ('pdfplumber','pdfium'):
        actual=[event for event in events if event['kind']=='reader' and event['reader']==reader]
        assert len(actual)==2 and {event['source_sha256'] for event in actual}==expected_shas
        assert all(event['guard_completed'] and event['sha256'] and Path(event['path']).is_relative_to(tmp_path) for event in actual)


def test_image_declared_pixels_and_hidden_jpeg_dimensions_are_guarded(tmp_path):
    from smm_local.document_formats.pdf_guard import intermediate
    image=Image.new('RGB',(100,80),'white');out=BytesIO();image.save(out,format='JPEG');jpeg=out.getvalue()
    boundary=Image.new('1',(4000,4000),1)
    accepted=image_pdf(zlib.compress(boundary.tobytes()),4000,4000,'FlateDecode',bits=1,color='DeviceGray')
    keep('inputs/pixels-exactly-16m.pdf',accepted)
    admitted=intermediate(accepted,tmp_path/'pixels-exactly-16m.pdf')
    assert admitted['pages']==1 and 2000000<=admitted['decoded_bytes']<2001000
    observe('pixels-exactly-16m',admitted)
    cases={'declared':image_pdf(jpeg,16000001,1,'DCTDecode')}
    changed=bytearray(jpeg)
    # Independent JPEG marker walk changes the actual SOF dimensions; PDF still
    # declares a harmless 100x80 image. No oversized bitmap is constructed.
    i=2
    while i<len(changed):
        assert changed[i]==255
        marker=changed[i+1];length=int.from_bytes(changed[i+2:i+4],'big')
        if marker in (0xc0,0xc1,0xc2):changed[i+5:i+9]=b'\xff\xff\xff\xff';break
        i+=2+length
    else:raise AssertionError('fixture JPEG has no SOF')
    cases['hidden']=image_pdf(bytes(changed),100,80,'DCTDecode')
    for key,raw in cases.items():
        keep('hostile/'+key+'.pdf',raw)
        with pytest.raises(ValueError,match='像素|尺寸|1600'):intermediate(raw,tmp_path/(key+'.pdf'))


def test_inline_decoded_payload_is_checked_before_render(tmp_path):
    from smm_local.document_formats.pdf_guard import intermediate
    # A 1x1 Gray image cannot legally have 33MiB of decoded pixel payload.
    # Only the compressed <40KiB bytes are put in the source PDF.
    raw=image_pdf(zlib.compress(b'\0'*(33*1024*1024)),1,1,'FlateDecode',bits=8,color='DeviceGray',inline=True)
    keep('hostile/inline-payload.pdf',raw)
    with pytest.raises(ValueError,match='图像|像素|长度|预算|解压'):intermediate(raw,tmp_path/'inline.pdf')


def test_codec_fixture_has_real_distinct_headers():
    assert features.check('jpg') and features.check('jpg_2000') and features.check('libtiff')
    if not FONT:pytest.skip('font preparation is required for raster fixture')
    hashes=[]
    for codec in ('DCTDecode','JPXDecode','CCITTFaxDecode','FlateDecode'):
        for key in ('alpha','beta'):
            raw,truth=raster(FONT,codec.lower()+key,codec)
            assert raw.startswith(b'%PDF-') and ('/Filter /'+codec).encode() in raw and len(truth['lines'])==2
            hashes.append(hashlib.sha256(raw).hexdigest())
    assert len(hashes)==len(set(hashes))==8


def test_inline_filter_cannot_bypass_actual_decoded_budget(tmp_path):
    from smm_local.document_formats.pdf_guard import intermediate
    raw=image_pdf(zlib.compress(b'\0'*(128*1024*1024+1)),1,1,'FlateDecode',inline=True)
    keep('inputs/inline-expansion.pdf',raw)
    with pytest.raises(ValueError):intermediate(raw,tmp_path/'inline.pdf')


def test_pdf_actual_page_and_shared_global_boundaries(tmp_path):
    from smm_local.document_formats.pdf_guard import intermediate
    from document_formats_pdf_security_fixture import content_pdf
    mib=1024*1024;one=b'%'+b'a'*(32*mib-1)
    # One complete page can contain exactly 32MiB, including split streams;
    # the same object shared by several pages is charged once globally.
    cases=[('single',[one],[[0]],32*mib,{1:32*mib}),('split',[one[:16*mib],one[16*mib:]],[[0,1]],32*mib,{1:32*mib}),('shared',[one],[[0],[0],[0]],32*mib,{1:32*mib,2:32*mib,3:32*mib}),('global',[one]*4,[[0],[1],[2],[3]],128*mib,{i:32*mib for i in range(1,5)})]
    for name,streams,pages,total,page_bytes in cases:
        raw=content_pdf(streams,pages);keep('inputs/boundary-'+name+'.pdf',raw)
        result=intermediate(raw,tmp_path/(name+'.pdf'))
        assert result['decoded_bytes']==total and result['page_content_bytes']==page_bytes
        observe('actual-budget-'+name,result)
    for name,streams,pages in [('page-plus-one',[one+b'a'],[[0]]),('split-plus-one',[one,b'a'],[[0,1]]),('shared-second-page-plus-one',[one,b'a'],[[0],[0,1]]),('global-plus-one',[one]*4+[b'a'],[[0],[1],[2],[3],[4]])]:
        raw=content_pdf(streams,pages);keep('inputs/boundary-'+name+'.pdf',raw)
        with pytest.raises(ValueError,match='32MiB|128MiB'):intermediate(raw,tmp_path/(name+'.pdf'))
        observe('budget-rejected-'+name,{'raw_sha256':hashlib.sha256(raw).hexdigest(),'expected':'reject before oversized decoded allocation'})


def test_actual_reader_observer_has_known_positive_and_negative_controls(tmp_path,monkeypatch):
    import subprocess,sys
    from document_formats_pdf_security_fixture import content_pdf
    log=install_reader_observer(tmp_path,monkeypatch);source=tmp_path/'source.pdf';source.write_bytes(content_pdf([b''],[[0]]))
    output=tmp_path/'private.pdf'
    code='''from pathlib import Path
import sys,json,hashlib
from smm_local.document_formats.pdf_guard import intermediate
import pypdfium2,pdfplumber
source,output=map(Path,sys.argv[1:])
intermediate(source.read_bytes(),output)
with pypdfium2.PdfDocument(output) as document:assert len(document)==1
with pdfplumber.open(output) as document:assert len(document.pages)==1
print(json.dumps({'guard_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
for value in (source,source.read_bytes()):
 for open_document in (pypdfium2.PdfDocument,pdfplumber.open):
  try:open_document(value)
  except AssertionError:pass
  else:raise AssertionError('unsafe input accepted by observer')
output.write_bytes(source.read_bytes())
try:pypdfium2.PdfDocument(output)
except AssertionError:pass
else:raise AssertionError('mutated intermediate accepted')
'''
    completed=subprocess.run([sys.executable,'-c',code,str(source),str(output)],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert completed.returncode==0,(completed.stdout,completed.stderr)
    observed=reader_records(log);readers=[v for v in observed if v['kind']=='reader'];rejected=[v for v in observed if v['kind']=='rejected']
    assert len(readers)==2 and {v['reader'] for v in readers}=={'pdfplumber','pdfium'}
    assert len(rejected)==5 and {v['reader'] for v in rejected}=={'pdfplumber','pdfium'}
    expected_sha=json.loads(completed.stdout)['guard_sha256'];source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    guards=[v for v in observed if v['kind']=='guard'];assert len(guards)==1
    assert all(v['sha256']==expected_sha and v['source_sha256']==source_sha and v['guard_completed'] is True and Path(v['path'])==output.resolve() for v in guards+readers)
    keep('observer/selfcheck.json',json.dumps(observed,ensure_ascii=False).encode())

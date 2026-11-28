"""Real bounded intermediate readers preserve source pixels/forms/objects."""
from io import BytesIO
import hashlib

import pdfplumber
import pypdfium2
import pytest

from document_helpers import Fixture, observe
from document_formats_pdf_safety_cases import predictor_image, nested_forms, compressed_font_object, filtered_text
from test_document_formats_retry import keep


@pytest.mark.parametrize('predictor',[2,10,11,12,13,14,15])
def test_real_predictor_intermediate_preserves_every_source_pixel(tmp_path,predictor):
    from smm_local.document_formats.pdf_guard import intermediate
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdftypes import resolve1
    for variant in (0,1):
        raw,expected=predictor_image(predictor,variant);before=hashlib.sha256(raw).hexdigest()
        keep('pdf-safety/predictor-'+str(predictor)+'-'+str(variant)+'.pdf',raw)
        # Validate the independent input before exercising SMM's guard.
        with pypdfium2.PdfDocument(raw) as pdf:
            assert len(pdf)==1
            page=pdf[0];bitmap=page.render(scale=1);pixels=bitmap.to_pil().convert('RGB')
            source_pixels=[pixels.getpixel((x,y)) for y in (30,90) for x in (40,120,200)]
            assert source_pixels==[(v,v,v) for v in expected]
            bitmap.close();page.close()
        output=tmp_path/(str(predictor)+'-'+str(variant)+'.pdf');report=intermediate(raw,output)
        document=PDFDocument(PDFParser(BytesIO(output.read_bytes())));pages=list(PDFPage.create_pages(document));assert len(pages)==1
        images=resolve1(pages[0].resources['XObject']);assert len(images)==1
        image=resolve1(next(iter(images.values())))
        assert image.get_data()==expected and not image.attrs.get('Filter') and image.attrs['Width']==3 and image.attrs['Height']==2
        with pypdfium2.PdfDocument(output) as pdf:
            page=pdf[0];bitmap=page.render(scale=1);pixels=bitmap.to_pil().convert('RGB')
            actual=[pixels.getpixel((x,y)) for y in (30,90) for x in (40,120,200)]
            assert actual==[(v,v,v) for v in expected]
            bitmap.close();page.close()
        assert hashlib.sha256(raw).hexdigest()==before and report['pages']==1
        keep('pdf-safety/private-predictor-'+str(predictor)+'-'+str(variant)+'.pdf',output.read_bytes())
        observe('guard-predictor-pixels',{'predictor':predictor,'variant':variant,'expected_pixels':list(expected),'source_pixels':source_pixels,'rendered_pixels':actual,'source_sha256':before,'private_sha256':hashlib.sha256(output.read_bytes()).hexdigest()})


@pytest.mark.parametrize('factory',[nested_forms,compressed_font_object],ids=['nested-forms','compressed-object-stream'])
def test_real_form_and_object_stream_sources_are_searchable_and_exact(tmp_path,factory,monkeypatch):
    f=Fixture(tmp_path);project=f.project('real safe objects');expected={}
    for key in ('SAFETYALPHA','SAFETYBETA'):
        raw,words=factory(key)
        # Validate each independently generated source with both native readers
        # before SMM sees it; expected words come from the fixture source.
        with pypdfium2.PdfDocument(raw) as document:
            page=document[0];text=page.get_textpage();body=text.get_text_range();text.close();page.close()
            assert all(body.count(word)==1 for word in words)
        with pdfplumber.open(BytesIO(raw)) as document:
            body=document.pages[0].extract_text();assert all(body.count(word)==1 for word in words)
        path=f.file(key+'.pdf',raw=raw);expected[path.name]={'raw':raw,'words':words,'mtime':path.stat().st_mtime_ns}
        keep('pdf-safety/'+factory.__name__+'-'+key+'.pdf',raw)
    from document_formats_pdf_observer import install,records
    observer=install(tmp_path,monkeypatch)
    source=f.add(f.root/'docs',projects=[project]);f.refresh(source)
    rows=f.files(source);assert len(rows)==2 and all(row['latest_attempt']['status']=='ready' for row in rows)
    query=' '.join(truth['words'][0] for truth in expected.values())
    hits=f.search(query,scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==len({h['id'] for h in hits})==2
    from pathlib import Path
    assert {Path(h['path']).name for h in hits}==set(expected)
    for hit in hits:
        path=Path(hit['path']);truth=expected[path.name];value=f.read(hit,start=0,end=hit['text_length'])
        assert all(value['text'].count(word)==1 for word in truth['words'])
        assert [value['text'].index(word) for word in truth['words']]==sorted(value['text'].index(word) for word in truth['words'])
        assert value['tables']==[] and value['coverage']['errors']==[]
        response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert response.status_code==200 and response.content==truth['raw']
        assert path.read_bytes()==truth['raw'] and path.stat().st_mtime_ns==truth['mtime']
        observe('safe-form-object-read',{'factory':factory.__name__,'reference':hit['reference'],'words':truth['words'],'text':value['text'],'sha256':hashlib.sha256(response.content).hexdigest()})
    events=records(observer);assert not any(e['kind']=='rejected' for e in events)
    expected_shas={hashlib.sha256(v['raw']).hexdigest() for v in expected.values()}
    # Native text is extracted without rasterization. PDFium is separately
    # exercised against the private intermediate in the filter/pixel cases.
    for reader in ('pdfplumber',):
        calls=[e for e in events if e['kind']=='reader' and e['reader']==reader]
        assert len(calls)==2 and {e['source_sha256'] for e in calls}==expected_shas
        assert all(e['guard_completed'] and Path(e['path']).is_relative_to(tmp_path) for e in calls)
    assert not any(e['kind']=='reader' and e['reader']=='pdfium' for e in events)
    keep('pdf-safety/'+factory.__name__+'-reader-events.json',__import__('json').dumps(events,ensure_ascii=False).encode())


@pytest.mark.parametrize('kind',['ASCIIHexDecode','ASCII85Decode','RunLengthDecode','LZWDecode','FlateDecode','ASCII85-LZW','ASCIIHex-Flate'])
def test_real_filter_pipelines_are_preserved_by_both_private_readers(tmp_path,kind):
    from smm_local.document_formats.pdf_guard import intermediate
    for key in ('PIPELINEALPHA','PIPELINEBETA'):
        raw,words=filtered_text(key,kind);keep('pdf-safety/'+kind+'-'+key+'.pdf',raw)
        # Independent source reader first checks this is an actual valid PDF,
        # not only a byte sequence our private decoder happens to accept.
        with pypdfium2.PdfDocument(raw) as document:
            page=document[0];text=page.get_textpage();assert text.get_text_range().strip()==key;text.close();page.close()
        output=tmp_path/(key+'.pdf');report=intermediate(raw,output)
        with pdfplumber.open(output) as document:assert document.pages[0].extract_text()==key
        with pypdfium2.PdfDocument(output) as document:
            page=document[0];text=page.get_textpage();assert text.get_text_range().strip()==key;text.close();page.close()
        keep('pdf-safety/private-'+kind+'-'+key+'.pdf',output.read_bytes())
        assert report['pages']==1
        observe('real-filter-pipeline',{'kind':kind,'source_words':words,'raw_sha256':hashlib.sha256(raw).hexdigest(),
            'private_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'decoded_bytes':report['decoded_bytes']})

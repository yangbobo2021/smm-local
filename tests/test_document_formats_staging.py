"""Actual 256MiB retained-capture capacity; no constant or backend stubs."""
import gzip,hashlib,json,os
from io import BytesIO
from pathlib import Path
import pytest
from document_helpers import Fixture,observe,fingerprint
from document_formats_fixtures import docx_fixture
from document_formats_staging_fixture import image_pdf
from document_formats_staging_observer import observe_capacity_writes

MIB=1024*1024
CAPACITY=256*MIB


def keep(name,raw):
    if directory:=os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        path=Path(directory)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def assert_missing_ocr_failure(error):
    assert isinstance(error,str) and 'ocr' in error.lower()
    assert '暂存超过256MiB' not in error and 'staging capacity' not in error.lower()



def save_input(name,raw):
    compressed=gzip.compress(raw,mtime=0);assert gzip.decompress(compressed)==raw
    keep('inputs/'+name+'.gz',compressed)
    meta={'name':name,'bytes':len(raw),'sha256':sha(raw),'gzip_bytes':len(compressed),'gzip_sha256':sha(compressed)}
    keep('inputs/'+name+'.manifest.json',json.dumps(meta).encode());return meta


def storage(f,published):
    root=f.db.db_path.parent/'.document-snapshots';value={}
    for kind in ('raw','results'):
        directory=root/kind
        for path in sorted(directory.iterdir()) if directory.exists() else []:
            assert path.is_file() and not path.is_symlink()
            if (kind,path.name) in published:continue
            raw=path.read_bytes();assert sha(raw)==path.name
            value[kind+'/'+path.name]={'bytes':len(raw),'sha256':sha(raw)}
    return value


def capacity_bytes(snapshot):return sum(row['bytes'] for row in snapshot.values())


def prepare(tmp_path):
    f=Fixture(tmp_path);project=f.project('capacity');raw=docx_fixture('stagingcontrol')[0]
    path=f.root/'published-control.docx';path.write_bytes(raw);source=f.add(path,[project]);f.refresh(source)
    files=f.files(source);assert len(files)==1 and files[0]['status']=='ready';entry=files[0]
    hits=f.search('stagingcontrol',scope='project',project_id=project,local=True)['results'];assert len(hits)==1 and hits[0]['id']==entry['id']
    hit=hits[0];read=f.read(hit);response=f.client.post('/api/documents/original',json={'reference':hit['reference']});assert response.status_code==200 and response.content==raw
    published={('raw',sha(raw)),('results',entry['published_snapshot']['result_sha256'])}
    assert storage(f,published)=={}
    return f,project,published,{'hit':hit,'text':read['text'],'raw':raw}


def assert_control(f,control):
    read=f.read(control['hit']);assert read['id']==control['hit']['id'] and read['text']==control['text']
    assert read['version']==control['hit']['version']==1 and read['processing_version']==control['hit']['processing_version']==1
    response=f.client.post('/api/documents/original',json={'reference':control['hit']['reference']})
    assert response.status_code==200 and response.content==control['raw']


def add_failure(f,project,key,size,*,raw=None):
    raw=image_pdf(key,size) if raw is None else raw;assert len(raw)==size
    meta=save_input(key+'.pdf',raw);path=f.file(key+'.pdf',raw=raw);before=fingerprint(path)
    source=f.add(path,[project]);refresh=f.refresh(source);files=f.files(source);assert len(files)==1
    entry=files[0];assert fingerprint(path)==before
    assert entry['status']=='failed' and entry['published_snapshot'] is None and entry['version']==entry['processing_version']==0
    target=entry['retry_target'];assert target and target['sha256']==meta['sha256']
    assert target['expected_version']==target['expected_processing_version']==0
    assert isinstance(target['capture_id'],str) and target['capture_id'] and isinstance(target['expected_attempt_id'],str) and target['expected_attempt_id']
    assert entry['latest_attempt']['capture_id']==target['capture_id'] and entry['latest_attempt']['attempt_id']==target['expected_attempt_id']
    error=entry['latest_attempt']['error'];assert_missing_ocr_failure(error)
    path.unlink();observe('retained-'+key,{'input':meta,'source':source,'refresh':refresh,'entry':entry,'source_deleted':True})
    return {'meta':meta,'source':source,'entry':entry,'path':path}


def assert_retained(f,items,published,expected_bytes):
    assert len({item['entry']['id'] for item in items})==len(items)
    assert len({item['entry']['retry_target']['capture_id'] for item in items})==len(items)
    assert len({item['entry']['retry_target']['expected_attempt_id'] for item in items})==len(items)
    expected={item['meta']['sha256']:item['meta']['bytes'] for item in items}
    actual=storage(f,published)
    assert set(actual)=={'raw/'+digest for digest in expected}
    assert capacity_bytes(actual)==expected_bytes
    for digest,length in expected.items():assert actual['raw/'+digest]=={'bytes':length,'sha256':digest}
    for item in items:
        files=f.files(item['source']);assert len(files)==1;entry=files[0];old=item['entry']
        assert entry['id']==old['id'] and entry['version']==entry['processing_version']==0 and entry['published_snapshot'] is None
        assert entry['retry_target']==old['retry_target'] and entry['latest_attempt']==old['latest_attempt']
    return actual


def fill(f,project,tail,prefix):
    return [add_failure(f,project,prefix+str(index),20*MIB if index<12 else tail) for index in range(13)]


def test_actual_staging_capacity_deduplicates_same_saved_bytes(tmp_path):
    # TC-008-staging-dedup: equality and a new identity with existing bytes.
    f,project,published,control=prepare(tmp_path);items=fill(f,project,16*MIB,'dedup')
    before=assert_retained(f,items,published,CAPACITY);assert_control(f,control)
    duplicate=image_pdf('dedup0',20*MIB)
    assert sha(duplicate)==items[0]['meta']['sha256']
    added=add_failure(f,project,'new-identity',20*MIB,raw=duplicate)
    assert added['entry']['id'] not in {item['entry']['id'] for item in items}
    for field in ('capture_id','expected_attempt_id'):
        assert added['entry']['retry_target'][field] not in {item['entry']['retry_target'][field] for item in items}
    after=assert_retained(f,[*items,added],published,CAPACITY);assert after==before;assert_control(f,control)
    observe('capacity-exact-and-dedup',{'bytes':CAPACITY,'before':before,'after':after,'candidate_count':14,'independent_raw_count':13})


def test_actual_staging_plus_one_rejects_before_writing_new_bytes(tmp_path,monkeypatch):
    # TC-008-staging-plus-one: a legal last PDF would make exactly +1 byte.
    f,project,published,control=prepare(tmp_path);new=image_pdf('overcapacity');tail=16*MIB-len(new)+1
    items=fill(f,project,tail,'plusone');expected=CAPACITY-len(new)+1
    assert sum(item['meta']['bytes'] for item in items)==expected and expected+len(new)==CAPACITY+1
    before=assert_retained(f,items,published,expected);assert_control(f,control)
    meta=save_input('last-plus-one.pdf',new);path=f.file('last-plus-one.pdf',raw=new);input_before=fingerprint(path)
    with f.db.connect() as con:
        captures_before=[dict(row) for row in con.execute('SELECT * FROM document_captures ORDER BY id')]
        attempts_before=[dict(row) for row in con.execute('SELECT * FROM document_processing_attempts ORDER BY id')]
    source=f.add(path,[project])
    with monkeypatch.context() as patch:
        events=observe_capacity_writes(patch,f.db.db_path.parent/'.document-snapshots')
        response=f.client.post('/api/documents/refresh',json={'source_id':source['id']})
    observe('capacity-rejection-writes',{'events':events})
    assert response.status_code in (200,400,409,413,422),response.text
    refresh=response.json();entries=f.files(source)
    observe('capacity-rejection-response',{'status':response.status_code,'response':refresh})
    assert fingerprint(path)==input_before and entries
    message=json.dumps({'refresh':refresh,'files':entries},ensure_ascii=False)
    assert '256' in message and ('暂存' in message or 'staging' in message.lower())
    assert all(entry.get('published_snapshot') is None and entry.get('retry_target') is None for entry in entries)
    with f.db.connect() as con:
        assert [dict(row) for row in con.execute('SELECT * FROM document_captures ORDER BY id')]==captures_before
        assert [dict(row) for row in con.execute('SELECT * FROM document_processing_attempts ORDER BY id')]==attempts_before
    after=storage(f,published);observe('capacity-plus-one-storage',{'input':meta,'before':before,'after':after,'bytes_before':expected,'bytes_after':capacity_bytes(after),'refresh':refresh,'files':entries,'write_events':events})
    assert events==[],events
    assert after==before and capacity_bytes(after)==expected
    assert_retained(f,items,published,expected);assert_control(f,control)


def test_exact_large_pdf_is_legal_and_below_other_budgets():
    import pdfplumber,pypdfium2
    for key,total in (('small',None),('twenty',20*MIB)):
        raw=image_pdf(key,total)
        if total is not None:assert len(raw)==total
        assert raw==image_pdf(key,total)
        with pdfplumber.open(BytesIO(raw)) as pdf:
            assert len(pdf.pages)==1;page=pdf.pages[0]
            assert page.width==640 and page.height==160 and page.extract_text()==''
            assert len(page.images)==1 and page.images[0]['srcsize']==(640,160)
            content=b''.join(stream.get_data() for stream in page.page_obj.contents)
            assert len(content)<32*MIB and len(content)+640*160*3<128*MIB
        pdf=pypdfium2.PdfDocument(raw);page=pdf[0];bitmap=page.render(scale=1);image=bitmap.to_pil().copy()
        assert image.size==(640,160) and image.convert('L').getextrema()[0]<100
        bitmap.close();page.close();pdf.close();out=BytesIO();image.save(out,format='PNG');keep('fixture-controls/'+key+'.png',out.getvalue())
        observe('legal-size-'+key,{'bytes':len(raw),'sha256':sha(raw),'pages':1,'image_pixels':640*160,'page_content_bytes':len(content),'decoded_upper_bound':len(content)+640*160*3})


def test_physical_storage_observer_detects_unreferenced_or_corrupt_bytes(tmp_path):
    from types import SimpleNamespace
    f=SimpleNamespace(db=SimpleNamespace(db_path=tmp_path/'archive.sqlite3'))
    raw_dir=tmp_path/'.document-snapshots/raw';result_dir=tmp_path/'.document-snapshots/results';raw_dir.mkdir(parents=True);result_dir.mkdir()
    published=b'published';pending=b'pending';result=b'pending result'
    (raw_dir/sha(published)).write_bytes(published);(raw_dir/sha(pending)).write_bytes(pending);(result_dir/sha(result)).write_bytes(result)
    permanent={('raw',sha(published))};value=storage(f,permanent)
    assert value=={'raw/'+sha(pending):{'bytes':len(pending),'sha256':sha(pending)},'results/'+sha(result):{'bytes':len(result),'sha256':sha(result)}}
    assert capacity_bytes(value)==len(pending)+len(result)
    orphan=b'orphan';path=raw_dir/sha(orphan);path.write_bytes(orphan)
    extra=storage(f,permanent);assert extra!=value and capacity_bytes(extra)==capacity_bytes(value)+len(orphan)
    path.write_bytes(b'corrupt')
    with pytest.raises(AssertionError):storage(f,permanent)
    path.unlink();temporary=raw_dir/'.pending-interrupted';temporary.write_bytes(b'pending physical bytes')
    with pytest.raises(AssertionError):storage(f,permanent)
    observe('storage-observer-controls',{'published_excluded':True,'raw_and_result_counted':True,'orphan_counted':True,'corrupt_and_pending_rejected':True})


def test_missing_ocr_diagnostic_control_allows_sha256_in_trace():
    assert_missing_ocr_failure("parse(raw, request['raw_sha256']); {'method': 'ocr', 'reason': 'missing component probe'}")
    for error in ('未发布暂存超过256MiB','OCR管线：未发布暂存超过256MiB','OCR staging capacity exceeded','unrelated parser failure'):
        with pytest.raises(AssertionError):assert_missing_ocr_failure(error)
    observe('staging-error-observer-controls',{'sha256_trace_accepted':True,'wrong_causes_rejected':4})


def test_before_accept_write_observer_has_real_positive_and_negative_controls(tmp_path,monkeypatch):
    import subprocess,sys
    root=tmp_path/'snapshots';raw=root/'raw';raw.mkdir(parents=True)
    existing=raw/'existing';existing.write_bytes(b'existing');outside=tmp_path/'outside';outside.write_bytes(b'renamed')
    with monkeypatch.context() as patch:
        events=observe_capacity_writes(patch,root)
        assert existing.read_bytes()==b'existing' and events==[]
        (raw/'.pending-zero').write_bytes(b'');assert events==[]
        (raw/'stream').write_bytes(b'first')
        fd=os.open(raw/'.pending-fd',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(fd,b'fd');os.close(fd)
        fd=os.open(raw/'.pending-stream',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(b'stream')
        os.replace(outside,raw/'moved');size=len(events)
        (tmp_path/'metadata').write_bytes(b'metadata')
        fd=os.open(tmp_path/'other-metadata',os.O_WRONLY|os.O_CREAT,0o600);os.write(fd,b'metadata');os.close(fd)
        assert len(events)==size
        child=subprocess.run([sys.executable,'-I','-c','pass'],capture_output=True,timeout=10);assert child.returncode==0
        assert [event['kind'] for event in events]==['stream.write','os.write','stream.write','move','worker-launch']
        assert [event['bytes'] for event in events[:-1]]==[5,2,6,7]
    observe('capacity-write-observer-controls',{'events':events,'existing_read_excluded':True,'zero_byte_file_excluded':True,'metadata_outside_body_store_excluded':True})

"""Empty success still has a usable saved original; failed is a separate state."""
import hashlib,json
from pathlib import Path
import pytest
from document_helpers import Fixture,observe,fingerprint,deny_source_reads
from document_formats_fixtures import docx_fixture
from document_formats_empty_fixture import empty_office,empty_pdf,image_only_pdf
from document_formats_sync_observer import install as install_no_processing
from test_document_formats_sync import test_sync_observer_known_positive_and_negative_controls as test_query_observer_controls
from test_document_formats_retry import keep


def business_state(f):
    with f.db.connect() as con:
        names=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'document_%'")]
        return {name:sorted([dict(row) for row in con.execute('SELECT * FROM "'+name+'"')],key=lambda row:json.dumps(row,sort_keys=True,default=str)) for name in names}


def test_empty_source_files_have_exact_originals_without_text_hits(tmp_path,monkeypatch):
    # TC-008-empty-original: Local path/files/API sub-path, not E/H completion.
    f=Fixture(tmp_path);project=f.project('empty documents');control_project=f.project('nonempty control');items={}
    for format in ('docx','xlsx','pdf'):
        for index,key in enumerate(('alpha','beta'),1):
            marker='empty'+format+key
            raw,truth=empty_pdf(marker) if format=='pdf' else empty_office(format,marker,sheets=index if format=='xlsx' else 1)
            path=f.file(marker+'.'+format,raw=raw)
            items[path.name]={'path':path,'raw':raw,'truth':truth,'before':fingerprint(path)}
            keep('inputs/'+path.name,raw);keep('truth/'+path.stem+'.json',json.dumps(truth).encode())
    failures={'broken.docx':b'PK\x03\x04truncated invalid archive','image-only.pdf':image_only_pdf()}
    negative={name:f.file(name,raw=raw) for name,raw in failures.items()}
    for name,raw in failures.items():keep('inputs/'+name,raw)
    control_root=f.root/'control';control_root.mkdir();control_raw=docx_fixture('nonemptycontrol81723')[0]
    control_path=control_root/'control.docx';control_path.write_bytes(control_raw)
    legacy_path=control_root/'legacy.txt';legacy_raw=b'legacynotcaptured81723\r\nline2';legacy_path.write_bytes(legacy_raw)
    keep('inputs/control.docx',control_raw);keep('inputs/legacy.txt',legacy_raw)
    source=f.add(f.root/'docs',[project]);control_source=f.add(control_root,[control_project]);f.refresh(source);f.refresh(control_source)
    baseline=f.files(source);assert len(baseline)==8 and {Path(row['path']).name for row in baseline}=={*items,*failures}
    indexed={Path(row['path']).name:row for row in baseline}
    for name,item in items.items():
        entry=indexed[name];assert entry['status']=='ready' and entry['published_snapshot']['status']=='empty-success',entry
        assert entry['version']==entry['processing_version']==1 and entry['text_length']==0
        assert entry['sha256']==item['before']['sha256'] and fingerprint(item['path'])==item['before']
        published=entry['published_snapshot'];result_path=f.db.db_path.parent/'.document-snapshots/results'/published['result_sha256'];raw_result=result_path.read_bytes()
        assert hashlib.sha256(raw_result).hexdigest()==published['result_sha256'];value=json.loads(raw_result)
        assert value['text']=='' and value['text_length']==0 and value['status']=='empty-success' and value['format']==item['truth']['format']
        assert value['coverage']['errors']==[] and value['coverage']['units']
        units=value['coverage']['units'];truth=item['truth']
        assert all(unit['method']=='native' and unit['status'] in ('ready','empty','empty-success') for unit in units)
        if truth['format']=='pdf':
            assert len(units)==2 and {unit['page'] for unit in units}==set(truth['pages'])
            assert all(unit['page_width']==truth['width'] and unit['page_height']==truth['height'] for unit in units)
        else:assert len(units)==len(truth['parts']) and {unit['part'] for unit in units}==set(truth['parts'])
        keep('results/'+name+'.json',raw_result)
    for name in failures:
        entry=indexed[name]
        assert entry['status']=='failed' and entry['published_snapshot'] is None and entry['latest_attempt']['status']=='failed'
        assert entry['version']==entry['processing_version']==0 and entry.get('original_reference') is None
    control_hits=f.search('nonemptycontrol81723',scope='project',project_id=control_project,local=True)['results'];assert len(control_hits)==1;control=control_hits[0]
    legacy_hits=f.search('legacynotcaptured81723',scope='project',project_id=control_project,local=True)['results'];assert len(legacy_hits)==1;legacy=legacy_hits[0]
    all_paths=[item['path'] for item in items.values()]+list(negative.values())+[control_path,legacy_path]
    for path in all_paths:path.unlink()
    with f.db.connect() as con:archive_id=json.loads(con.execute("SELECT value FROM settings WHERE key='archive:identity'").fetchone()[0])
    references={};query_before=business_state(f)
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*all_paths)
        files=f.files(source);assert len(files)==8 and {row['id'] for row in files}=={row['id'] for row in baseline}
        by_name={Path(row['path']).name:row for row in files}
        assert len({by_name[name]['id'] for name in items})==6
        for name in failures:
            entry=by_name[name]
            assert entry['status']=='failed' and entry['published_snapshot'] is None and entry['latest_attempt']['status']=='failed'
            assert entry['version']==entry['processing_version']==0 and entry.get('original_reference') is None
        for name,item in items.items():
            entry=by_name[name];assert entry['id']==indexed[name]['id'] and entry['version']==entry['processing_version']==1
            assert entry['status']=='ready' and entry['published_snapshot']['status']=='empty-success'
            reference=entry['original_reference'];assert isinstance(reference,str) and reference;references[name]=reference
            assert f.search(item['truth']['key'],scope='project',project_id=project,local=True)['results']==[]
            info=f.read(reference,view='original-info')
            assert info['id']==entry['id'] and info['version']==entry['version'] and info['processing_version']==entry['processing_version']
            assert info['format']==item['truth']['format'] and info['available'] is True and info['sha256']==item['before']['sha256'] and info['bytes']==len(item['raw'])
            assert info['source_ids']==[source['id']] and info['archive_scope']=='local' and info['origin']=={'device_id':archive_id,'archive_id':archive_id,'document_id':entry['id']}
            response=f.client.post('/api/documents/original',json={'reference':reference})
            assert response.status_code==200 and response.content==item['raw'] and hashlib.sha256(response.content).hexdigest()==entry['sha256']
            assert 'attachment' in response.headers['content-disposition'];keep('downloads/'+name,response.content)
        assert len(set(references.values()))==6
        assert {hit['id'] for hit in f.search('nonemptycontrol81723',scope='project',project_id=control_project,local=True)['results']}=={control['id']}
        legacy_info=f.read(legacy,view='original-info')
        assert legacy_info['available'] is False and 'not_captured' in legacy_info['reason']
        rejected=f.bad('POST','/api/documents/original',{'reference':legacy['reference']});assert b'legacynotcaptured81723' not in rejected.content
        assert f.read(legacy,start=0,end=legacy['text_length'])['text']==legacy_raw.decode().replace('\r\n','\n')
        assert attempts==[] and reads==[] and business_state(f)==query_before;observe('empty-queries-no-processing',{'attempts':attempts,'source_reads':reads,'references':references})
    f.remove(source);after_removal=business_state(f)
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*all_paths)
        for name,reference in references.items():
            f.bad('POST','/api/documents/read',{'reference':reference,'view':'original-info'})
            response=f.bad('POST','/api/documents/original',{'reference':reference});assert response.content!=items[name]['raw']
        current=f.search('nonemptycontrol81723',scope='project',project_id=control_project,local=True)['results'];assert len(current)==1 and current[0]['id']==control['id']
        assert (current[0]['version'],current[0]['processing_version'],current[0]['sha256'])==(control['version'],control['processing_version'],control['sha256'])
        old=f.read(control,view='original-info');assert old['id']==control['id'] and old['version']==control['version'] and old['processing_version']==control['processing_version']
        assert old['origin']=={'device_id':archive_id,'archive_id':archive_id,'document_id':control['id']} and old['source_ids']==[control_source['id']]
        assert old['format']=='docx' and old['available'] is True and old['sha256']==hashlib.sha256(control_raw).hexdigest() and old['bytes']==len(control_raw)
        response=f.client.post('/api/documents/original',json={'reference':control['reference']});assert response.status_code==200 and response.content==control_raw
        remaining=f.files(control_source);assert {entry['id'] for entry in remaining}=={control['id'],legacy['id']} and len(remaining)==2
        legacy_after=f.search('legacynotcaptured81723',scope='project',project_id=control_project,local=True)['results'];assert len(legacy_after)==1 and legacy_after[0]['id']==legacy['id']
        assert f.read(legacy,start=0,end=legacy['text_length'])['text']==legacy_raw.decode().replace('\r\n','\n')
        legacy_after_info=f.read(legacy,view='original-info');assert legacy_after_info['available'] is False and 'not_captured' in legacy_after_info['reason']
        assert attempts==[] and reads==[] and business_state(f)==after_removal;observe('after-empty-source-removal',{'control':current[0],'old_info':old,'attempts':attempts,'source_reads':reads})


def test_empty_source_read_guard_known_control(tmp_path,monkeypatch):
    source=tmp_path/'source.docx';source.write_bytes(b'should not open')
    attempts=deny_source_reads(monkeypatch,source)
    with pytest.raises(AssertionError):source.read_bytes()
    assert attempts==[str(source)]
    observe('empty-source-read-guard',{'attempts':attempts})

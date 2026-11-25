"""Only unsupported objects are not blank; genuine empty Office files still work."""
import copy,hashlib,json,os,sqlite3,zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest
from PIL import Image
from document_helpers import ROOT,observe
from test_document_formats_restore_set import invoke
from test_document_formats_retry import keep
from smm_local.core import Archive
from smm_local.document_results import validate

FIXTURES=ROOT/'tests'/'fixtures'/'document-format-objects'


def inputs():
    manifest=json.loads((FIXTURES/'manifest.json').read_text(encoding='utf-8'))
    expected={(p,f,k) for p in ('ordinary','global') for f,kinds in [('docx',('body','header','footer','blank','text')),('xlsx',('object','blank','text'))] for k in kinds}
    assert {(i['project'],i['format'],i['kind']) for i in manifest['items']}==expected
    assert len(manifest['items'])==len({i['sha256'] for i in manifest['items']})==16
    assert manifest['generator_sha256']==hashlib.sha256((ROOT/'scripts'/'acceptance'/'008_generate_object_fixtures.py').read_bytes()).hexdigest()
    values=[]
    for item in manifest['items']:
        key=item['project']+item['kind']+item['format'];assert item['file']==key+'.'+item['format']
        raw=(FIXTURES/item['file']).read_bytes()
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        expected_text=key+' supported value' if item['kind']=='text' else ''
        assert item['text']==expected_text
        assert item['expected_status']==('empty-success' if item['kind']=='blank' else 'ready' if item['kind']=='text' else 'failed')
        with zipfile.ZipFile(BytesIO(raw)) as z:
            assert z.testzip() is None
            drawing=[];texts=[];pictures=[]
            for name in z.namelist():
                if name.endswith('.png'):
                    picture=z.read(name)
                    with Image.open(BytesIO(picture)) as image:
                        image.load();assert image.format=='PNG' and image.size==(24,24)
                        assert len(set(image.convert('RGB').getdata()))>1
                    pictures.append({'part':name,'sha256':hashlib.sha256(picture).hexdigest()})
                if name.endswith('.xml'):
                    root=ET.fromstring(z.read(name))
                    if any(n.tag.endswith('}drawing') for n in root.iter()):drawing.append(name)
                    texts.extend(n.text for n in root.iter() if n.tag.endswith('}t') and n.text)
            part='word/header1.xml' if item['kind']=='header' else 'word/footer1.xml' if item['kind']=='footer' else 'word/document.xml' if item['format']=='docx' else 'xl/worksheets/sheet1.xml'
            assert sorted(drawing)==sorted(item['drawing_parts'])==([] if item['kind']=='blank' else [part])
            assert texts==item['supported_text_nodes']==([expected_text] if expected_text else [])
            assert sorted(pictures,key=lambda p:p['part'])==item['images']
            assert len(pictures)==int(item['kind']!='blank')
        values.append((item,raw))
    return values


def test_frozen_sdk_office_inputs_are_complete_and_independently_checked():
    values=inputs()
    observe('object-empty-frozen-inputs',{'items':[i for i,r in values],'count':len(values),'SDK_environment_not_required_by_test':True})


@pytest.mark.parametrize('owner',['local','hub'])
def test_real_creator_does_not_publish_object_only_files_as_empty_success(tmp_path,owner):
    # TC-008-unsupported-object-empty
    root=tmp_path/owner;root.mkdir();db=root/('smm-hub.sqlite3' if owner=='hub' else 'archive.sqlite3')
    archive=Archive(db);empty=root/'empty-agents';empty.mkdir();archive.set_settings(codex_root=str(empty),claude_root=str(empty))
    if owner=='hub':
        from smm_hub.hub import create_hub
        create_hub(archive,'synthetic-object-empty-'+'b'*32)
    projects=[invoke(root,db,owner,'project','create','Object ordinary'),invoke(root,db,owner,'project','ensure-global')]
    items=[];bad=[];control_count=0;failed_count=0
    for project_name,project in zip(('ordinary','global'),projects):
        folder=root/'sources'/project_name;folder.mkdir(parents=True)
        group=[]
        for original,raw in inputs():
            if original['project']!=project_name:continue
            item={**original,'raw':raw,'project_id':project['id'],'path':folder/original['file']};item['path'].write_bytes(raw);item['mtime']=item['path'].stat().st_mtime_ns
            keep('inputs/'+owner+'-'+item['file'],raw);group.append(item);items.append(item)
        source=invoke(root,db,owner,'documents','add',folder,'--project-id',project['id'])
        for item in group:item['source_id']=source['id']
        invoke(root,db,owner,'documents','refresh','--source-id',source['id'])
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as c:
            assert c.execute('SELECT project_id FROM document_source_projects WHERE source_id=?',(source['id'],)).fetchall()==[(project['id'],)]
    files=invoke(root,db,owner,'documents','files');assert len(files)==len({r['id'] for r in files})==16
    bypath={Path(r['path']).resolve():r for r in files};assert set(bypath)=={i['path'].resolve() for i in items}
    for item in items:
        entry=bypath[item['path'].resolve()];assert entry['source_id']==item['source_id'];latest=entry['latest_attempt']
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as c:
            actual=c.execute('SELECT d.id,x.raw_sha256,x.raw_bytes,a.capture_id,s.current_capture FROM documents d JOIN document_captures x ON x.document_pk=d.pk JOIN document_snapshot_state s ON s.document_pk=d.pk JOIN document_processing_attempts a ON a.id=s.latest_attempt WHERE d.path_key=?',(os.path.normcase(str(item['path'].resolve())),)).fetchall()
        assert len(actual)==1 and actual[0]==(entry['id'],item['sha256'],len(item['raw']),latest['capture_id'],latest['capture_id'])
        assert (root/'.document-snapshots'/'raw'/item['sha256']).read_bytes()==item['raw']
        if item['expected_status']=='failed':
            target=entry.get('retry_target')
            valid=latest['status']=='failed' and bool(latest['error']) and entry['published_snapshot'] is None and entry['version']==entry['processing_version']==0 and target is not None and target['capture_id']==latest['capture_id'] and not entry.get('original_reference')
            if not valid:bad.append({'file':item['file'],'document_id':entry['id'],'expected':'failed_unpublished_legal_capture','entry':entry})
            failed_count+=int(valid)
        else:
            assert latest['status']==entry['published_snapshot']['status']==item['expected_status'] and entry['version']==entry['processing_version']==1
            ref=entry['original_reference'];assert isinstance(ref,str) and ref
            query=Path(item['file']).stem
            found=invoke(root,db,owner,'documents','search',query,'--scope','project','--project-id',item['project_id'],*(['--local'] if owner=='local' else []))['results']
            if item['kind']=='blank':assert found==[] and entry['text_length']==0
            else:
                assert len(found)==1 and found[0]['id']==entry['id'] and found[0]['sha256']==item['sha256']
                value=invoke(root,db,owner,'documents','read','--reference',ref,'--start',0,'--end',entry['text_length'])
                assert value['text']==item['text'] and 'drawing' in value['coverage']['excluded']
            info=invoke(root,db,owner,'documents','read','--reference',ref,'--view','original-info')
            output=root/(entry['id']+'.original');invoke(root,db,owner,'documents','read','--reference',ref,'--original-output',output)
            assert info['sha256']==item['sha256'] and info['bytes']==len(item['raw']) and output.read_bytes()==item['raw']
            keep('downloads/'+owner+'-'+item['sha256'],output.read_bytes());control_count+=1
        assert item['path'].read_bytes()==item['raw'] and item['path'].stat().st_mtime_ns==item['mtime']
        observe('object-empty-target',{'owner':owner,'input':{k:v for k,v in item.items() if k not in {'raw'}},'entry':entry,'captured_original_exact':True})
    assert control_count==8
    observe('object-empty-creator-complete',{'owner':owner,'actual_correct_failed_objects':failed_count,'expected_failed_objects':8,'positive_blank_and_text_controls':control_count,'wrong_object_states':bad})
    assert not bad,{'object_only_not_failed':bad}


@pytest.mark.parametrize('format',['docx','xlsx'])
def test_pure_result_validation_rejects_declared_unsupported_empty_content(format):
    # TC-008-unsupported-object-empty; Hub validates results without parsing raw.
    from importlib import import_module
    parser=import_module('smm_local.document_formats.'+('word' if format=='docx' else 'spreadsheet')).parse
    accepted=[]
    for item,raw in inputs():
        if item['format']!=format or item['kind']!='blank':continue
        value=parser(raw,item['sha256'],{'format':format,'rendering':'smm-document-text-v1','config_revision':0});assert value['status']=='empty-success' and value['text']=='' and value['coverage']['excluded']==[]
        assert validate(value)==value
        bad=copy.deepcopy(value);bad['coverage']['excluded']=['drawing']
        try:validate(bad)
        except ValueError as error:observe('object-empty-result-rejected',{'file':item['file'],'error':str(error)})
        else:accepted.append(item['file'])
    assert not accepted,{'self_declared_unsupported_empty_results_accepted':accepted}

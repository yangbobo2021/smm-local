"""Actual creator pages must expose each persisted processing failure diagnostic."""
import hashlib,json,os,time,sqlite3
from io import BytesIO
from pathlib import Path
import pytest
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pdfencrypt import StandardEncryption
from document_helpers import observe
from test_document_formats_retry import FONT,scan_pdf,keep
from test_document_formats_restore_set import invoke
from test_document_formats_upload_restart import Server
from document_formats_web_helpers import Browser

BROWSER=pytest.mark.skipif(not (os.environ.get('PLAYWRIGHT_BROWSERS_PATH') and FONT),reason='requires prepared real browser/font; skipped does not prove Web/platform acceptance')


def encrypted_pdf(label):
    out=BytesIO();password='synthetic-'+label
    pdf=canvas.Canvas(out,invariant=1,encrypt=StandardEncryption(password,strength=128))
    pdf.drawString(72,700,label+' valid encrypted original');pdf.showPage();pdf.save()
    raw=out.getvalue()
    with pdfplumber.open(BytesIO(raw),password=password) as opened:
        assert len(opened.pages)==1 and label+' valid encrypted original' in opened.pages[0].extract_text()
    with pytest.raises(Exception):
        with pdfplumber.open(BytesIO(raw)) as opened:opened.pages[0].extract_text()
    return raw


def expected_visible(value,latest):
    assert latest['status']=='failed' and isinstance(latest['error'],str) and latest['error'].strip()
    for field in ('capture_id','attempt_id','status','config_revision','error'):
        assert field in value and type(value[field]) is type(latest[field]) and value[field]==latest[field],field


def test_failure_diagnostic_oracle_rejects_wrong_target_status_and_reason():
    latest={'capture_id':'capture-a','attempt_id':'attempt-a','status':'failed','config_revision':4,'error':'OCR data unavailable'}
    expected_visible(dict(latest),latest);rejected=[]
    for field in latest:
        for value in (None,'wrong target'):
            bad={**latest,field:value}
            with pytest.raises(AssertionError):expected_visible(bad,latest)
            rejected.append(field)
        missing=dict(latest);missing.pop(field)
        with pytest.raises(AssertionError):expected_visible(missing,latest)
    with pytest.raises(AssertionError):expected_visible({**latest,'error':''},latest)
    observe('web-diagnostic-known-controls',{'wrong_fields_rejected':rejected,'missing_fields_rejected':list(latest),'empty_reason_rejected':True})


@BROWSER
@pytest.mark.parametrize('owner',['local','hub'])
def test_real_web_details_show_each_saved_failure_reason(tmp_path,owner):
    # TC-008-web-failure-diagnostic; no initial-upload or ready-management repair.
    from playwright.sync_api import expect
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/acceptance'))
    from document_formats_lifecycle_visual import capture as capture_details
    server=Server(tmp_path/owner,owner)
    if owner=='hub':server.db=server.root/'smm-hub.sqlite3'
    evidence=Path(os.environ.get('ACCEPTANCE_EVIDENCE_DIR',str(tmp_path/'browser-evidence')));evidence.mkdir(exist_ok=True)
    items=[];failures=[];snapshots=[]
    try:
        server.start()
        projects=[invoke(server.root,server.db,owner,'project','create','diagnostic ordinary'),invoke(server.root,server.db,owner,'project','ensure-global')]
        for number,project in enumerate(projects):
            directory=tmp_path/'materials'/str(number);directory.mkdir(parents=True)
            for kind in ('ocr','encrypted'):
                label=owner+str(number)+kind;raw=scan_pdf(label) if kind=='ocr' else encrypted_pdf(label)
                path=directory/(label+'.pdf');path.write_bytes(raw)
                keep('inputs/'+label+'.pdf',raw)
                items.append({'label':label,'path':path,'raw':raw,'mtime':path.stat().st_mtime_ns,'kind':kind,'project':project})
            for item in [i for i in items if i['project']['id']==project['id']]:
                raw=item['raw'];body={**server.context,'project_id':project['id'],'project_key':project['stable_key'] if owner=='local' else project['source_key'],'submission_id':item['label'],'name':item['path'].name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                begin=server.call('POST','/documents/uploads',body).json();uid=begin['upload_id']
                for index,offset in enumerate(range(0,len(raw),begin['block_bytes'])):
                    chunk=raw[offset:offset+begin['block_bytes']];server.call('PUT','/documents/uploads/'+uid+'/parts/'+str(index),raw=chunk,headers={'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
                receipt=server.call('POST','/documents/uploads/'+uid+'/commit',server.context).json();item['id']=receipt['document_id'];item['receipt']=receipt
                deadline=time.monotonic()+35
                while True:
                    current={r['id']:r for r in server.call('GET','/documents/library').json()}.get(item['id'])
                    if current and current['latest_attempt']['status'] in {'ready','partial','failed','empty-success'}:break
                    assert time.monotonic()<deadline,current
                    time.sleep(.03)
                assert current['latest_attempt']['status']=='failed',current
        rows=server.call('GET','/documents/library').json();assert len(rows)==len({r['id'] for r in rows})==4
        byid={r['id']:r for r in rows};assert set(byid)=={i['id'] for i in items}
        for item in items:
            row=byid[item['id']];item['entry']=row;latest=row['latest_attempt']
            assert latest['capture_id']==item['receipt']['capture_id'] and latest['attempt_id']==item['receipt']['attempt_id']
            with sqlite3.connect('file:'+str(server.db)+'?mode=ro',uri=True) as c:
                capture=c.execute('SELECT x.raw_sha256,d.id FROM document_captures x JOIN documents d ON d.pk=x.document_pk WHERE x.id=?',(latest['capture_id'],)).fetchone()
            assert capture==(hashlib.sha256(item['raw']).hexdigest(),item['id'])
            assert (server.root/'.document-snapshots'/'raw'/capture[0]).read_bytes()==item['raw']
            assert row['published_snapshot'] is None and row['version']==row['processing_version']==0 and row['retry_target'] is not None and row['retry_target']['capture_id']==latest['capture_id']
            assert latest['status']=='failed' and latest['error']
            assert ('ocr' in latest['error'].casefold()) if item['kind']=='ocr' else any(s in latest['error'].casefold() for s in ('加密','密码','encrypt','password'))
            snapshots.append({'id':row['id'],'project':item['project']['id'],'input_sha256':hashlib.sha256(item['raw']).hexdigest(),'latest_attempt':latest})
        observe('web-diagnostic-independent-targets',{'owner':owner,'items':snapshots})
        with Browser(server,evidence) as browser:
            for project in projects:
                browser.project(project,library=True)
                box=browser.page.locator('#doc-library-list' if owner=='local' else '#hub-library-list')
                for item in [i for i in items if i['project']['id']==project['id']]:
                    row=box.locator('.result').filter(has_text='文档 '+item['id']);expect(row).to_have_count(1);expect(row).to_be_visible()
                    screenshot=evidence/(owner+'-'+item['label']+'-failed-detail.png')
                    proof=capture_details(browser.page,owner,item['entry'],'pdf',screenshot)
                    visible=json.loads(proof['after']['fields']['latest_attempt'])
                    try:expected_visible(visible,item['entry']['latest_attempt']);valid=True
                    except AssertionError as exc:valid=False;failures.append({'id':item['id'],'field':str(exc),'expected':item['entry']['latest_attempt'],'visible':visible})
                    observe('web-diagnostic-visible',{'owner':owner,'document_id':item['id'],'project_id':project['id'],'screenshot':screenshot.name,'capture':proof,'visible':visible,'exact_target_reason_visible':valid})
            assert all(i['path'].read_bytes()==i['raw'] and i['path'].stat().st_mtime_ns==i['mtime'] for i in items)
            assert not failures,{'missing_or_wrong_saved_failure_diagnostics':failures}
    finally:server.stop()

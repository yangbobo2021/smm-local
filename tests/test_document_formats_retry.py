"""Real local OCR retry from saved captures; enabled only with prepared assets."""
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from document_helpers import Fixture,deny_source_reads,observe
from document_formats_fixtures import docx_fixture

ENGINE=os.environ.get('SMM_008_OCR_EXECUTABLE')
DATA=os.environ.get('SMM_008_OCR_DATA')
FONT=os.environ.get('SMM_008_FONT')
pytestmark=pytest.mark.skipif(not all((ENGINE,DATA,FONT)),reason='requires explicitly prepared real OCR assets; not E/H evidence when skipped')


def keep(name,raw):
    if folder:=os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        path=Path(folder)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def scan_pdf(anchor):
    image=Image.new('RGB',(2000,600),'white');draw=ImageDraw.Draw(image);font=ImageFont.truetype(FONT,64)
    draw.text((100,130),anchor+' RETRY 73428',fill='black',font=font)
    draw.text((100,300),'CAPTURED ORIGINAL 12345.67',fill='black',font=font)
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(600,180),invariant=1,pageCompression=1)
    pdf.drawImage(ImageReader(image),0,0,width=600,height=180);pdf.showPage();pdf.save()
    return output.getvalue()


def child_source_guard(root,paths,monkeypatch):
    folder=root/'source-audit';folder.mkdir();log=folder/'attempts.jsonl'
    code=r'''import json,os,sys
protected={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_PROTECTED_SOURCES'])}
def audit(event,args):
    values=([args[0]] if event=='open' else list(args[1]) if event=='subprocess.Popen' and isinstance(args[1],(list,tuple)) else [])
    for value in values:
        if isinstance(value,(str,bytes)) and os.path.normcase(os.path.abspath(os.fsdecode(value))) in protected:
            with open(os.environ['SMM_008_SOURCE_AUDIT'],'a',encoding='utf-8') as out:out.write(json.dumps({'pid':os.getpid(),'event':event,'path':os.fsdecode(value)})+'\n')
            raise AssertionError('forbidden original source read')
sys.addaudithook(audit)
'''
    (folder/'sitecustomize.py').write_text(code,encoding='utf-8')
    monkeypatch.setenv('SMM_008_PROTECTED_SOURCES',json.dumps(list(map(str,paths))))
    monkeypatch.setenv('SMM_008_SOURCE_AUDIT',str(log))
    monkeypatch.setenv('PYTHONPATH',str(folder)+os.pathsep+os.environ.get('PYTHONPATH',''))
    return log


def cli(f,*args,code=0):
    argv=[sys.executable,'-B','-m','smm_local.cli','--db',str(f.db.db_path),'documents',*map(str,args)]
    result=subprocess.run(argv,cwd=f.root,capture_output=True,text=True,encoding='utf-8',timeout=90)
    observe('real-cli-'+str(len(args)),{'argv':argv,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'expected':code})
    if code is None:assert result.returncode!=0,result.stdout
    else:assert result.returncode==code,result.stderr
    return json.loads(result.stdout) if code==0 else result


def retry_args(entry,target,*,version=None,processing_version=None):
    return ['reprocess','--document-id',entry['id'],'--capture-id',target['capture_id'],'--expected-attempt-id',target['expected_attempt_id'],'--expected-version',target['expected_version'] if version is None else version,'--expected-processing-version',target['expected_processing_version'] if processing_version is None else processing_version]


def test_first_ocr_failure_retries_each_saved_capture(tmp_path,monkeypatch):
    # TC-008-first-failure: two failed targets plus an already-published control.
    f=Fixture(tmp_path);project=f.project('008 capture retry')
    wordraw=docx_fixture('controlword')[0];wordpath=f.file('control.docx',raw=wordraw);keep('inputs/control.docx',wordraw)
    source=f.add(f.root/'docs',projects=[project]);f.refresh(source)
    prior=f.search('controlword',scope='project',project_id=project,local=True)['results'];assert len(prior)==1
    control=prior[0];control_text=f.read(control,start=0,end=control['text_length'])['text']
    expected={}
    for name,anchor in [('alpha.pdf','ALPHA'),('beta.pdf','BETA')]:
        raw=scan_pdf(anchor);path=f.file(name,raw=raw)
        expected[name]={'raw':raw,'path':path,'anchor':anchor,'sha256':hashlib.sha256(raw).hexdigest()};keep('inputs/'+name,raw)
    f.refresh(source)
    entries={Path(e['path']).name:e for e in f.files(source)}
    assert len(entries)==3 and set(entries)=={'control.docx',*expected}
    assert f.read(control,start=0,end=control['text_length'])['text']==control_text
    targets={}
    for name,item in expected.items():
        entry=entries[name]
        assert 'published_snapshot' in entry and entry['published_snapshot'] is None
        assert entry['version']==entry['processing_version']==0
        assert entry['latest_attempt']['status']=='failed'
        target=entry['retry_target'];assert target is not None
        assert target['sha256']==item['sha256']
        assert target['expected_version']==target['expected_processing_version']==0
        assert target['expected_attempt_id']==entry['latest_attempt']['attempt_id']
        assert target['capture_id']==entry['latest_attempt']['capture_id']
        targets[name]=target
    assert len({t['capture_id'] for t in targets.values()})==len({t['expected_attempt_id'] for t in targets.values()})==2
    source_reads=deny_source_reads(monkeypatch,wordpath,*[v['path'] for v in expected.values()])
    log=child_source_guard(f.root,[wordpath,*[v['path'] for v in expected.values()]],monkeypatch)
    before=f.files(source);status=cli(f,'processing-status')
    cli(f,'processing-configure','--expected-revision',status['config']['revision'],'--ocr-executable',ENGINE,'--ocr-data-dir',DATA,'--languages','chi_sim+eng')
    after=f.files(source)
    assert {e['id']:e['latest_attempt'] for e in after}=={e['id']:e['latest_attempt'] for e in before}
    for item in expected.values():item['path'].unlink()
    # A legal capture from another document cannot be used as this target.
    wrong={**targets['alpha.pdf'],'capture_id':targets['beta.pdf']['capture_id']}
    cli(f,*retry_args(entries['alpha.pdf'],wrong),code=None)
    assert f.files(source)==after
    completed=set()
    for name,item in expected.items():
        target=targets[name];entry=entries[name]
        cli(f,*retry_args(entry,target));completed.add(name)
        current={Path(e['path']).name:e for e in f.files(source)}
        assert set(current)==set(entries)
        published=current[name]['published_snapshot']
        assert published['version']==published['processing_version']==1
        assert published['capture_id']==target['capture_id']
        assert current[name]['latest_attempt']['attempt_id']!=target['expected_attempt_id']
        hits=f.search('ALPHA BETA',scope='project',project_id=project,local=True,limit=50)['results']
        assert len(hits)==len(completed) and {Path(h['path']).name for h in hits}==completed
        for hit in hits:
            wanted=expected[Path(hit['path']).name]
            assert wanted['anchor'] in f.read(hit,start=0,end=hit['text_length'])['text']
            response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
            assert response.status_code==200 and response.content==wanted['raw'];keep('downloads/'+Path(hit['path']).name,response.content)
            assert hit['sha256']==wanted['sha256']
        assert f.read(control,start=0,end=control['text_length'])['text']==control_text
        control_raw=f.client.post('/api/documents/original',json={'reference':control['reference']})
        assert control_raw.status_code==200 and control_raw.content==wordraw;keep('downloads/control.docx',control_raw.content)
        assert current['control.docx']['version']==entries['control.docx']['version']
        assert current['control.docx']['processing_version']==entries['control.docx']['processing_version']
        frozen=f.files(source)
        cli(f,*retry_args(entry,target,version=1,processing_version=1),code=None)
        assert f.files(source)==frozen
    assert source_reads==[] and (not log.exists() or log.read_text()=='')


def test_prepared_ocr_assets_can_start():
    for path in (ENGINE,DATA,FONT):assert Path(path).exists(),path
    result=subprocess.run([ENGINE,'--version'],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert result.returncode==0 and 'tesseract 5.' in result.stdout+result.stderr
    langs=subprocess.run([ENGINE,'--tessdata-dir',DATA,'--list-langs'],capture_output=True,text=True,encoding='utf-8',timeout=20)
    assert langs.returncode==0 and {'eng','chi_sim'}.issubset(set((langs.stdout+langs.stderr).splitlines()))
    observe('actual-ocr-assets',{'engine':ENGINE,'version':result.stdout+result.stderr,'languages':langs.stdout+langs.stderr,'font_sha256':hashlib.sha256(Path(FONT).read_bytes()).hexdigest(),'data_sha256':{n:hashlib.sha256((Path(DATA)/(n+'.traineddata')).read_bytes()).hexdigest() for n in ('eng','chi_sim')}})


def test_source_guard_is_active(tmp_path,monkeypatch):
    source=tmp_path/'source.txt';source.write_text('forbidden body',encoding='utf-8')
    log=child_source_guard(tmp_path,[source],monkeypatch)
    allowed=subprocess.run([sys.executable,'-c','print("guard-ready")'],capture_output=True,text=True,timeout=10)
    assert allowed.returncode==0 and allowed.stdout.strip()=='guard-ready'
    denied=subprocess.run([sys.executable,'-c','from pathlib import Path;import sys;Path(sys.argv[1]).read_bytes()',str(source)],capture_output=True,text=True,timeout=10)
    assert denied.returncode!=0 and 'forbidden original source read' in denied.stderr
    observed=[json.loads(line) for line in log.read_text().splitlines()]
    assert len(observed)==1 and observed[0]['path']==str(source)

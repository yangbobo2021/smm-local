"""Real browser/download custody probe; not SMM platform acceptance."""
import argparse,json,os,socket,threading,traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from reportlab.pdfgen import canvas
from playwright.sync_api import sync_playwright
from document_formats_evidence import save,sha


def listening(port):
    with socket.socket() as probe:probe.settimeout(1);return probe.connect_ex(('127.0.0.1',port))==0


def probe(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    originals=output/'originals';originals.mkdir()
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
    from document_formats_fixtures import docx_fixture
    (originals/'alpha.docx').write_bytes(docx_fixture('custodyalpha')[0])
    pdf=canvas.Canvas(str(originals/'beta.pdf'),pagesize=(300,200),invariant=1)
    for page in (1,2):pdf.drawString(30,100,'CUSTODY BETA ORIGINAL PAGE '+str(page));pdf.showPage()
    pdf.save()
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>008 evidence custody probe</title><h1>008 EVIDENCE CUSTODY</h1><a download href="originals/alpha.docx">Download alpha</a><a download href="originals/beta.pdf">Download beta</a>',encoding='utf-8')
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(output)));port=server.server_address[1]
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();before={'port':port,'listening':listening(port),'thread_alive':thread.is_alive()};browser=None
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch();context=browser.new_context(accept_downloads=True)
            context.tracing.start(screenshots=True,snapshots=True,sources=True)
            try:
                page=context.new_page();response=page.goto('http://127.0.0.1:'+str(port))
                assert response.status==200 and page.get_by_role('heading').inner_text()=='008 EVIDENCE CUSTODY'
                page.screenshot(path=str(output/'visible-probe.png'),full_page=True)
                downloads=output/'downloads';downloads.mkdir()
                for name,label in [('alpha.docx','Download alpha'),('beta.pdf','Download beta')]:
                    with page.expect_download() as pending:page.get_by_role('link',name=label).click()
                    pending.value.save_as(downloads/name)
                    assert (downloads/name).read_bytes()==(originals/name).read_bytes()
                save(output/'observations.json',{'kind':'real browser custody small sample, not product acceptance','originals':{p.name:sha(p) for p in originals.iterdir()},'downloads':{p.name:sha(p) for p in downloads.iterdir()},'title':page.title()})
            finally:
                context.tracing.stop(path=str(output/'trace.zip'));context.close();browser.close();browser=None
    except Exception as error:
        save(output/'probe-error.json',{'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()});raise
    finally:
        if browser is not None:browser.close()
        server.shutdown();server.server_close();thread.join(5)
        after={'port':port,'listening':listening(port),'thread_alive':thread.is_alive()}
        passed=before['listening'] and before['thread_alive'] and not after['listening'] and not after['thread_alive']
        save(output/'cleanup.json',{'scope':'small-sample HTTP server only; no SMM service registration','status':'verified' if passed else 'failed','checks':[{'name':'task HTTP listener and serving thread','before':before,'after':after,'passed':passed}]})
        if not passed:raise RuntimeError('probe listener cleanup not verified')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--context-output',type=Path,required=True);a=p.parse_args()
    context={'run_id':os.environ['GITHUB_RUN_ID'],'job_key':'evidence-custody-probe','commit':os.environ['GITHUB_SHA'],'artifact_name':'008-evidence-custody-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']}
    save(a.context_output,context);probe(a.output)
if __name__=='__main__':main()

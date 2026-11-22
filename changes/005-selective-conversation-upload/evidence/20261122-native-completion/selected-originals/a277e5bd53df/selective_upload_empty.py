"""Actual E1 CLI/MCP/Web successful empty searches in fresh installed archives."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import socket
import tempfile
import uuid

from selective_upload_platform import Run, now


class Empty(Run):
    def execute_empty(self):
        self.installed(); self.setup()
        positive=self.cli(self.db,'search','selective','--scope','project','--project-id',str(self.projects['A']))
        assert {h['source_session_id'] for h in positive['results']}=={'local-A','remote-B','vibe-V'}
        self.save('positive-control',positive)
        # Playwright's synchronous context owns an event loop. Complete actual
        # stdio MCP calls before entering it; do not nest asyncio.run there.
        prepared={}
        for scope in ['all','project']:
            cli=self.cli(self.db,'search','uniquelyabsentquery','--scope',scope,*(['--project-id',str(self.projects['A'])] if scope=='project' else []))
            mcp=asyncio.run(self.mcp('search_conversations',{'query':'uniquelyabsentquery','scope':scope,**({'project_id':self.projects['A']} if scope=='project' else {})}))
            for result in [cli,mcp]:
                assert result['results']==[] and result['coverage']=={'local':'complete','hub':'complete'} and not result.get('fallback_reason')
            prepared[scope]={'cli':cli,'mcp':mcp}
        self.save('successful-empty-cli-mcp',prepared)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,**({'executable_path':self.t['browser']} if self.t.get('browser') else {}))
            context=browser.new_context(viewport={'width':1440,'height':1000}); context.tracing.start(screenshots=True,snapshots=True,sources=True)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            observed={}
            try:
                page.goto(self.web);page.locator('nav button[data-tab=search]').click()
                for scope in ['all','project']:
                    cli,mcp=prepared[scope]['cli'],prepared[scope]['mcp']
                    page.locator('#query').fill('uniquelyabsentquery');page.locator('#scope').select_option(scope)
                    if scope=='project':page.locator('#search-project').select_option(str(self.projects['A']))
                    with page.expect_response(lambda r:r.url.endswith('/api/search')) as answer:page.locator('#search-form button').click()
                    web=answer.value.json()
                    for result in [cli,mcp,web]:
                        assert result['results']==[] and result['coverage']=={'local':'complete','hub':'complete'}
                        assert not result.get('fallback_reason')
                    page.locator('#results').get_by_text('没有匹配结果',exact=False).wait_for()
                    page.wait_for_function("all => {const t=document.getElementById('effective').textContent;return t.includes('本机已检索') && t.includes('Hub已检索') && t.includes('所有项目')===all}",arg=scope=='all')
                    page.screenshot(path=str(self.output/('successful-empty-'+scope+'.png')),full_page=True)
                    observed[scope]={'cli':cli,'mcp':mcp,'web':web,'visible':page.locator('body').inner_text()}
                assert errors==[]
                self.save('successful-empty',{'by_scope':observed,'browser_version':browser.version,'page_errors':errors})
            finally:context.tracing.stop(path=str(self.output/'successful-empty-trace.zip'));browser.close()

    def run_empty(self):
        error=None
        try:self.execute_empty()
        except BaseException as exc:error=f'{type(exc).__name__}: {exc}';raise
        finally:
            try:self.cleanup()
            except BaseException as exc:
                if error is None:error=f'cleanup: {exc}';raise
            finally:self.save('result',{'status':'failed' if error else 'passed','failure':error,'started_at':self.started,'finished_at':now(),'scope':'E1 actual successful empty query, both all/project and CLI/stdio MCP/browser; no rerun claim for unrelated behavior'})


def main():
    p=argparse.ArgumentParser();p.add_argument('--target-config',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
    config=json.loads(a.target_config.read_text(encoding='utf-8-sig'));assert os.sys.platform==config['expected_platform']
    config['work']=str(Path(config['work']).parent/('smm-005-empty-'+uuid.uuid4().hex))
    with socket.socket() as s:s.bind(('127.0.0.1',0));config['port']=s.getsockname()[1]
    config['address']='https://localhost:'+str(config['port'])
    output=a.output or Path(os.environ['ACCEPTANCE_EVIDENCE_DIR'])/'probe'
    with tempfile.TemporaryDirectory(prefix='smm-005-empty-config-') as d:
        target=Path(d)/'target.json';target.write_text(json.dumps(config));Empty(argparse.Namespace(target_config=target,output=output,mode='client')).run_empty()


if __name__=='__main__':main()

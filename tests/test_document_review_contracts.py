"""Independent regressions for SPEC B6/B7 found in the green review."""
import asyncio
import json
from copy import deepcopy

from test_hub_documents_contracts import w
from document_helpers import deny_source_reads, observe
from hub_document_helpers import assert_text
from smm_local import federation
from smm_local.mcp_server import create_mcp


# @case-id: TC-007-listing-coverage
def test_listing_coverage(w, monkeypatch):
    p=w.project('Listing Local')
    path,source=w.source('listing.txt','listingnonce local original',[p])
    hp=w.hub_project('Listing Hub')
    native=w.upload(hp,'remote.txt','listingnonce remote original',hub=True)
    server=create_mcp(w.pair.local)
    async def call(name,body):
        answer=await server.call_tool(name,body)
        observe('listing-mcp',{'name':name,'request':body,'response':str(answer)})
        return json.loads(answer[0][0].text)
    def tool(name,body):return asyncio.run(call(name,body))
    def local_state():
        with w.pair.local.connect() as c:
            names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if r[0]=='settings' or r[0].startswith(('local_upload','upload_message','local_document','document'))]
            return {name:[dict(r) for r in c.execute('SELECT * FROM "'+name+'" ORDER BY 1')] for name in names}
    before_local=local_state();before_hub=w.snapshot();all_calls_start=len(w.calls)
    with monkeypatch.context() as scan_guard:
        attempts=deny_source_reads(scan_guard,path)
        assert {s['id'] for s in tool('list_document_sources',{})}=={source['id']}
        assert isinstance(tool('list_projects',{}),list)
        for name in ['list_document_sources','list_projects']:
            result=tool(name,{'include_hub':True})
            assert result['coverage']=={'local':'complete','hub':'complete'}
            assert not result.get('fallback_reason')
            if name=='list_document_sources':
                assert {s['id'] for s in result['local']}=={source['id']}
                assert native['source_id'] in {s['id'] for s in result['hub']}
                assert {s['origin']['kind'] for s in result['hub']}=={'hub'}
            else:
                assert p in {s['id'] for s in result['local']}
                assert hp['id'] in {s['id'] for s in result['hub']}
        result=w.local.request('GET','/api/projects?include_hub=true')
        assert result['coverage']=={'local':'complete','hub':'complete'}
        expected_sources=tool('list_document_sources',{})
        expected_projects=tool('list_projects',{})
        expected_api_projects=w.local.request('GET','/api/projects')
        before=w.snapshot()
        marker=len(w.calls)
        original=federation._request
        def offline(*a,**kw):raise federation.HubUnavailable('listing offline witness')
        monkeypatch.setattr(federation,'_request',offline)
        for name in ['list_document_sources','list_projects']:
            result=tool(name,{'include_hub':True})
            assert result['coverage']=={'local':'complete','hub':'unavailable'}
            assert result['hub']==[] and 'listing offline witness' in result['fallback_reason']
            assert result['local']==(expected_sources if name=='list_document_sources' else expected_projects)
        result=w.local.request('GET','/api/projects?include_hub=true')
        assert result['coverage']=={'local':'complete','hub':'unavailable'}
        assert result['local']==expected_api_projects and result['hub']==[] and result['fallback_reason']
        assert w.snapshot()==before
        assert not w.calls[marker:],'No request succeeds when offline'
        monkeypatch.setattr(federation,'_request',original)
        marker=len(w.calls)
        for name in ['list_document_sources','list_projects']:tool(name,{'include_hub':True})
        w.local.request('GET','/api/projects?include_hub=true')
        assert {route for route,_ in w.calls[marker:]}<={'/info','/projects','/documents/sources'}
        assert w.snapshot()==before
    assert not attempts
    assert local_state()==before_local and w.snapshot()==before_hub
    assert {route for route,_ in w.calls[all_calls_start:]}<={'/info','/projects','/documents/sources'}
    observe('listing-side-effects',{'local_upload_document_settings_unchanged':True,'hub_document_projects_unchanged':True,'routes':[route for route,_ in w.calls[all_calls_start:]],'source_open_attempts':attempts})
    assert path.read_text()=='listingnonce local original'


# @case-id: TC-007-snippet-conflict
def test_snippet_conflict(w, monkeypatch):
    p=w.project('Snippet Original')
    original_text='conflictnonce actual local original'
    _,source=w.source('conflict.txt',original_text,[p]);w.policy(p);w.sync()
    local=w.local.search('conflictnonce',local=True)['results'][0]
    request=federation._request
    for kind in ['equal-window','partial-overlap']:
        def conflict(config,route,payload=None):
            result=request(config,route,payload)
            if route=='/documents/search':
                result=deepcopy(result);hit=result['results'][0]
                if kind=='partial-overlap':hit['start']=5
                hit['text']='x'*(hit['end']-hit['start'])
            return result
        monkeypatch.setattr(federation,'_request',conflict)
        result=w.local.search('conflictnonce',limit=50)
        observe('snippet-conflict',{'kind':kind,'result':result})
        assert len(result['results'])==1
        hit=result['results'][0]
        assert hit['text']==local['text'] and hit['archive_scope']=='local'
        assert result['coverage']['hub']=='partial' and result['candidate_failures']
        assert len(hit['origin_references'])==1
        assert_text(w.local.read(hit),original_text)
    monkeypatch.setattr(federation,'_request',request)
    valid=w.local.search('conflictnonce')['results'][0]
    assert valid['archive_scope']=='combined' and len(valid['origin_references'])==2
    assert_text(w.local.read(valid),original_text)

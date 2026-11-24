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
    path2,source2=w.source('listing-other.txt','listingnonce local other',[p])
    hp=w.hub_project('Listing Hub')
    native=w.upload(hp,'remote.txt','listingnonce remote original',hub=True)
    native2=w.upload(hp,'remote-other.txt','listingnonce remote other',hub=True)
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
    # Baselines come from the setup archives, not a queried list response.
    with w.pair.local.connect() as c:
        wanted_local={r['id']:dict(r) for r in c.execute('SELECT id,name,kind FROM projects')}
    with w.pair.remote.connect() as c:
        wanted_hub={r['id']:dict(r) for r in c.execute('SELECT p.id,p.name,h.kind AS source,h.owner,h.source_key FROM projects p JOIN hub_projects h ON h.id=p.id')}
    def complete_projects(rows,wanted):
        assert len(rows)==len(wanted) and {r['id'] for r in rows}==set(wanted)
        for row in rows:
            assert all(row[key]==value for key,value in wanted[row['id']].items())
    wanted_local_sources={source['id'],source2['id']}
    wanted_hub_sources={native['source_id'],native2['source_id']}
    def complete_sources(rows,wanted):
        assert len(rows)==len(wanted) and {row['id'] for row in rows}==wanted
    before_local=local_state();before_hub=w.snapshot();all_calls_start=len(w.calls)
    with monkeypatch.context() as scan_guard:
        attempts=deny_source_reads(scan_guard,path,path2)
        complete_sources(tool('list_document_sources',{}),wanted_local_sources)
        complete_projects(tool('list_projects',{}),wanted_local)
        for name in ['list_document_sources','list_projects']:
            result=tool(name,{'include_hub':True})
            assert result['coverage']=={'local':'complete','hub':'complete'}
            assert not result.get('fallback_reason')
            if name=='list_document_sources':
                complete_sources(result['local'],wanted_local_sources)
                complete_sources(result['hub'],wanted_hub_sources)
                assert {s['origin']['kind'] for s in result['hub']}=={'hub'}
            else:
                complete_projects(result['local'],wanted_local)
                complete_projects(result['hub'],wanted_hub)
        result=w.local.request('GET','/api/projects?include_hub=true')
        assert result['coverage']=={'local':'complete','hub':'complete'}
        complete_projects(result['local'],wanted_local)
        complete_projects(result['hub'],wanted_hub)
        expected_sources=tool('list_document_sources',{})
        complete_sources(expected_sources,wanted_local_sources)
        expected_projects=tool('list_projects',{})
        expected_api_projects=w.local.request('GET','/api/projects')
        complete_projects(expected_projects,wanted_local)
        complete_projects(expected_api_projects,wanted_local)
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
            if name=='list_projects':complete_projects(result['local'],wanted_local)
            else:complete_sources(result['local'],wanted_local_sources)
        result=w.local.request('GET','/api/projects?include_hub=true')
        assert result['coverage']=={'local':'complete','hub':'unavailable'}
        assert result['local']==expected_api_projects and result['hub']==[] and result['fallback_reason']
        complete_projects(result['local'],wanted_local)
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
    assert path2.read_text()=='listingnonce local other'


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

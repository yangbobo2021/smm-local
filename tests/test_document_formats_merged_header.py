"""Saved-result views retain left-anchored merged headings and exact budgets."""
import hashlib,json,socket,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from document_formats_merged_header_fixture import merged_header
from document_formats_sync_observer import install as no_processing
from document_helpers import observe,deny_source_reads,fingerprint
from test_document_formats_management import Creator
from test_document_formats_retry import keep
from test_document_formats_table_context import state
from test_hub_documents_contracts import w


def source_cell(actual, expected):
    for key,value in expected.items():assert actual[key]==value,key
    if actual.get('merged_into'):assert actual['text'] is None


def expected_headers(truth, window):
    selected=set(range(window['column_start'],window['column_end']))
    # Frozen source says A:N share one heading. This does not call SMM's
    # window/intersection implementation or infer headings from returned data.
    coords=({1} if selected & set(range(1,15)) else set()) | ({15,16} & selected)
    return [c for c in truth['headers'] if c['column'] in coords]


def header_cells(actual, expected, *, summary=False):
    assert len(actual)==len({(c['row'],c['column']) for c in actual})==len(expected)
    indexed={(c['row'],c['column']):c for c in actual}
    assert set(indexed)=={(c['row'],c['column']) for c in expected}
    for wanted in expected:
        cell=indexed[(wanted['row'],wanted['column'])]
        if summary:
            for key,value in wanted.items():
                if key!='text':assert cell[key]==value,key
            assert cell['text']==wanted['text'][:len(cell['text'])]
            if len(cell['text'])<len(wanted['text']):assert cell['text_truncated'] is True and cell['text_length']==len(wanted['text'])
        else:source_cell(cell,wanted)


def source_window(value, truth, expected_window=None):
    assert (value['rows'],value['columns'])==(250,16) and value['location']==truth['location']
    win=value['window']
    if expected_window is not None:assert win==expected_window
    r,re,c,ce=(win[k] for k in ('row_start','row_end','column_start','column_end'))
    wanted=[v for v in truth['cells'] if r<=v['row']<re and c<=v['column']<ce]
    actual=value['cells'];assert len(actual)==len({(v['row'],v['column']) for v in actual})==len(wanted)
    indexed={(v['row'],v['column']):v for v in actual};assert set(indexed)=={(v['row'],v['column']) for v in wanted}
    for v in wanted:source_cell(indexed[(v['row'],v['column'])],v)
    headers=value['header_context'];assert headers['role']==truth['header_role']
    header_cells(headers['cells'],expected_headers(truth,win))
    unique={(v['row'],v['column']):v for v in actual+headers['cells']}
    assert len(unique)<=1000 and sum(len(v.get('text') or '') for v in unique.values())<=16000


@pytest.mark.parametrize('owner',['local','hub'])
def test_merged_headings_follow_selected_columns_and_exact_unicode_budget(w,owner,monkeypatch):
    # TC-008-merged-column-header. Actual FastAPI HTTP, not TCP/TLS/service.
    c=Creator(w,owner);items=[]
    for group,project in enumerate(c.projects):
        for format in ('docx','xlsx'):
            for length in (64,2001,16000):
                for index in (1,2):
                    key=owner+str(group)+format+str(length)+str(index)
                    raw,truth=merged_header(format,key,length);item={'project':project,'name':key+'.'+format,'raw':raw,'truth':truth}
                    keep('merged/inputs/'+item['name'],raw);keep('merged/truth/'+item['name']+'.json',json.dumps(truth,ensure_ascii=False).encode())
                    uid,receipt,entry=c.upload(item,raw)
                    assert entry['latest_attempt']['status']=='ready' and not entry['publication_pending']
                    assert entry['version']==entry['processing_version']==1 and entry['sha256']==hashlib.sha256(raw).hexdigest()
                    item.update(id=receipt['document_id'],path=Path(entry['path']),entry=entry)
                    item['before']=fingerprint(item['path']);assert item['before']['sha256']==hashlib.sha256(raw).hexdigest()
                    digest=entry['published_snapshot']['result_sha256'];saved=(c.db.db_path.parent/'.document-snapshots/results'/digest).read_bytes()
                    assert hashlib.sha256(saved).hexdigest()==digest
                    result=json.loads(saved);assert result['text']==truth['text'] and result['raw_sha256']==entry['sha256'] and len(result['tables'])==1
                    table=result['tables'][0];assert (table['rows'],table['columns'],table['location'])==(250,16,truth['location'])
                    actual={(cell['row'],cell['column']):cell for cell in table['cells']}
                    assert len(actual)==len(table['cells'])==len(truth['cells']) and set(actual)=={(v['row'],v['column']) for v in truth['cells']}
                    for cell in truth['cells']:source_cell(actual[(cell['row'],cell['column'])],cell)
                    item.update(result_sha256=digest,profile=result['profile'],table_id=table['table_id'])
                    keep('merged/results/'+item['name']+'.json',saved)
                    items.append(item)
    assert len(items)==len({i['id'] for i in items})==24
    for item in items:
        assert fingerprint(item['path'])==item['before'];item['path'].unlink()
    before=state(SimpleNamespace(db=c.db))
    def read(item,body,rejected=False):
        response=c.request('POST','/documents/read',body,reject=rejected)
        if rejected:return response
        value=response.json()
        assert value['id']==item['id'] and value['version']==value['processing_version']==1
        assert value['sha256']==item['entry']['sha256'] and value['result_sha256']==item['result_sha256'] and value['profile']==item['profile']
        if body.get('view')=='table':assert value['table_id']==item['table_id']
        return value
    with monkeypatch.context() as m:
        attempts=no_processing(m);reads=deny_source_reads(m,*(i['path'] for i in items))
        # Calibrate the actual guards, including a real allowed socketpair and
        # saved blob open. Keep control records; queries may add no event.
        from smm_local.document_snapshots import Snapshots
        for action in (lambda:Snapshots.process(None,None,'docx'),lambda:subprocess.Popen([sys.executable,'-c','raise SystemExit(0)']),lambda:socket.create_connection(('192.0.2.1',9)),lambda:__import__('pdfplumber')):
            with pytest.raises(AssertionError):action()
        for item in items:
            with pytest.raises(AssertionError):item['path'].read_bytes()
        a,b=socket.socketpair()
        try:a.sendall(b'H');assert b.recv(1)==b'H'
        finally:a.close();b.close()
        assert (c.db.db_path.parent/'.document-snapshots/raw'/items[0]['entry']['sha256']).read_bytes()==items[0]['raw']
        baseline=list(attempts);read_baseline=list(reads);assert len(baseline)==4 and len(read_baseline)==24
        for item in items:
            t=item['truth'];result=c.request('POST','/documents/search',{**c.context,'query':t['query'],'scope':'project','project_id':item['project']['id'],'limit':50,**({'local':True} if owner=='local' else {})}).json()
            assert len(result['results'])==1 and result['results'][0]['id']==item['id']
            hit=result['results'][0];ref=hit['reference'];body={**c.context,'reference':ref}
            assert hit['version']==hit['processing_version']==1 and hit['sha256']==hashlib.sha256(item['raw']).hexdigest()
            assert hit['text']==t['text'][hit['start']:hit['end']] and t['query'] in hit['text']
            assert hit['start_line']==1+t['text'].count('\n',0,hit['start']) and hit['end_line']==1+t['text'].count('\n',0,hit['end']-1)
            default=read(item,body)
            assert default['text']==t['text'][hit['start']:hit['end']] and len(default['tables'])==1
            table=default['tables'][0];context=hit['table_context'];assert context['table_id']==table['table_id'] and table['location']==t['location']
            assert table['table_id']==item['table_id'] and hit['result_sha256']==item['result_sha256'] and hit['profile']==item['profile']
            anchor=context['matched_cells'];assert len(anchor)==1 and (anchor[0]['row'],anchor[0]['column'],anchor[0]['row_span'],anchor[0]['column_span'])==(243,13,1,1)
            assert anchor[0]['location']==next(v for v in t['cells'] if (v['row'],v['column'])==(243,13))['location']
            assert context['header_context']['role']==t['header_role']
            assert len(hit['text'])+sum(len(v.get('text') or '') for v in context['header_context']['cells'])<=2000
            view_body={**body,'view':'table','table_id':table['table_id']}
            if t['header_length']<16000:
                win=context['suggested_window'];assert win is not None
                assert win['row_start']<=243<win['row_end'] and win['column_start']<=13<win['column_end']
                assert win['row_end']-win['row_start']<=20 and win['column_end']-win['column_start']<=10
                assert win['column_start']>1
                header_cells(context['header_context']['cells'],expected_headers(t,win),summary=True)
                view=read(item,view_body);source_window(view,t,win)
                assert view['window_origin']=='search_hit'
                if t['header_length']==2001:assert context['needs_expansion'] is True
            else:
                assert context['suggested_window'] is None and context['needs_expansion'] is True
                assert '16000' in context['reason'] and '原件' in context['reason']
                header_cells(context['header_context']['cells'],[t['headers'][0]],summary=True)
                refused=read(item,view_body,rejected=True);assert '16000' in refused.text and '原件' in refused.text
            # Nonintersecting O/P columns must not borrow A:N's heading.
            bounds={'row_start':243,'row_end':244,'column_start':15,'column_end':17}
            source_window(read(item,{**view_body,**bounds}),t,bounds)
            if t['header_length']==16000:
                # Header appears in both cells/context: count exactly once.
                bounds={'row_start':1,'row_end':2,'column_start':1,'column_end':15}
                source_window(read(item,{**view_body,**bounds}),t,bounds)
                refused=read(item,{**view_body,'row_start':243,'row_end':244,'column_start':13,'column_end':14},rejected=True)
                assert '16000' in refused.text and '原件' in refused.text
            full=[]
            for start in range(0,len(t['text']),16000):
                end=min(len(t['text']),start+16000);value=read(item,{**body,'start':start,'end':end})
                assert value['text']==t['text'][start:end] and value['start']==start and value['end']==end
                full.append(value['text'])
            assert ''.join(full)==t['text']
            original=c.request('POST','/documents/original',body).content;assert original==item['raw'];keep('merged/downloads/'+item['entry']['sha256']+'.'+t['format'],original)
            assert attempts==baseline and reads==read_baseline
            observe('merged-target-complete',{'owner':owner,'id':item['id'],'name':item['name'],'header_length':t['header_length'],'raw_sha256':item['entry']['sha256']})
        assert state(SimpleNamespace(db=c.db))==before and attempts==baseline and reads==read_baseline
        observe('merged-query-controls',{'owner':owner,'processing_spawn_import_network_controls':baseline,'source_open_controls':read_baseline,'extra_events':False,'documents':len(items)})

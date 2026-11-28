"""Search excerpt plus true source-header summaries share a codepoint budget."""
import copy,json
import pytest
from document_helpers import Fixture,observe,deny_source_reads
from document_formats_table_fixture import workbook
from document_formats_sync_observer import install as install_no_processing
from test_document_formats_table_context import capture,state,assert_location,assert_text_window,assert_window


def preview_source(key,header_length):
    query=key+'Target';header=('甲😀H'*6000)[:header_length]
    cells=[{'row':1,'column':11,'text':header,'row_span':1,'column_span':1},{'row':243,'column':11,'text':query,'row_span':1,'column_span':1}]
    raw,text=workbook([{'name':'Overview','cells':[{'row':1,'column':1,'text':key+'Overview'}]},{'name':'Details','state':'hidden','cells':cells,'hidden_rows':[243],'hidden_columns':[11]}])
    return raw,{'format':'xlsx','query':query,'text':text,'rows':243,'columns':11,'target':[243,11],'cells':cells,'header_role':'first_content_row','location':{'part':'xl/worksheets/sheet2.xml','sheet':'Details','sheet_index':2},'sheet_state':'hidden'}


def context_texts(value):
    if isinstance(value,dict):return [text for key,item in value.items() for text in ([item] if key=='text' and isinstance(item,str) else context_texts(item))]
    if isinstance(value,list):return [text for item in value for text in context_texts(item)]
    return []


def assert_summary(hit,truth,table_id):
    assert_text_window(hit,truth);assert truth['query'] in hit['text']
    context=hit['table_context'];assert context['table_id']==table_id
    matched=context['matched_cells'];assert len(matched)==1
    cell=matched[0];assert (cell['row'],cell['column'],cell['row_span'],cell['column_span'])==(243,11,1,1)
    start=truth['text'].index(truth['query'])
    assert_location(cell['location'],{**truth['location'],'coordinate':'K243','start':start,'end':start+len(truth['query'])})
    headers=context['header_context'];assert headers['role']=='first_content_row'
    assert len(headers['cells'])==1;header=headers['cells'][0];original=truth['cells'][0]['text']
    assert (header['row'],header['column'],header['row_span'],header['column_span'])==(1,11,1,1)
    first=truth['text'].index(original)
    assert_location(header['location'],{**truth['location'],'coordinate':'K1','start':first,'end':first+len(original)})
    shown=header['text'];assert isinstance(shown,str) and shown and original.startswith(shown)
    if shown!=original:assert context['needs_expansion'] is True
    assert len(hit['text'])+sum(map(len,context_texts(context)))<=2000
    return context


def test_search_table_header_summaries_have_exact_shared_budget(tmp_path,monkeypatch):
    # TC-008-table-preview: the shared Local API summary path only.
    f=Fixture(tmp_path);project=f.project('table summaries');items={}
    for key in ('alpha','beta'):
        for suffix,length in (('short',40),('long',2001),('oversized',16001)):
            raw,truth=preview_source(key+suffix,length);items[key+suffix+'.xlsx']={'raw':raw,'truth':truth,'header_length':length}
    source=capture(f,project,items);before=state(f)
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*(item['path'] for item in items.values()))
        for name,item in items.items():
            truth=item['truth'];hits=f.search(truth['query'],scope='project',project_id=project,local=True)['results']
            assert len(hits)==1 and hits[0]['id']==item['entry']['id'];hit=hits[0]
            read=f.read(hit);assert_text_window(read,truth)
            assert (read['start'],read['end'],read['text'])==(hit['start'],hit['end'],hit['text'])
            assert read['id']==hit['id']==item['entry']['id'] and read['sha256']==hit['sha256']==item['entry']['sha256']
            assert read['version']==hit['version']==read['processing_version']==hit['processing_version']==1
            tables=[table for table in read['tables'] if table['location'].get('sheet_index')==2]
            assert len(tables)==1;ident=tables[0]['table_id'];assert_location(tables[0]['location'],truth['location'])
            context=assert_summary(hit,truth,ident)
            if item['header_length']<16000:
                view=f.read(hit,view='table',table_id=ident)
                assert_window(view,truth,target=truth['target'],window=context['suggested_window'])
                if item['header_length']==40:assert context['header_context']==view['header_context']
            else:
                assert context['suggested_window'] is None and context['needs_expansion'] is True
                message=context['reason'];assert '16000' in message and '原件' in message
                rejected=f.bad('POST','/api/documents/read',{'reference':hit['reference'],'view':'table','table_id':ident})
                message=json.dumps(rejected.json(),ensure_ascii=False);assert '16000' in message and '原件' in message
            observe('summary-'+name,{'hit':hit,'text_read':read,'summary_codepoints':len(hit['text'])+sum(map(len,context_texts(context)))})
        assert attempts==[] and reads==[] and state(f)==before
        observe('summary-queries-readonly',{'attempts':attempts,'source_reads':reads,'before':before,'after':state(f)})


def test_preview_oracle_rejects_omission_fabrication_and_bad_budget():
    _,truth=preview_source('oracle',2001);header=truth['cells'][0]['text'];start=truth['text'].index(truth['query']);first=truth['text'].index(header)
    loc={**truth['location'],'coordinate':'K243','start':start,'end':start+len(truth['query'])}
    head={'row':1,'column':11,'row_span':1,'column_span':1,'text':header[:1600],'location':{**truth['location'],'coordinate':'K1','start':first,'end':first+len(header)}}
    context={'table_id':'table','matched_cells':[{'row':243,'column':11,'row_span':1,'column_span':1,'location':loc}],'header_context':{'role':'first_content_row','cells':[head]},'needs_expansion':True}
    hit={'start':start,'end':len(truth['text']),'text':truth['query'],'start_line':3,'end_line':3,'table_context':context}
    assert_summary(hit,truth,'table')
    for mutate in (lambda v:v['table_context']['header_context']['cells'][0].update(text=''),lambda v:v['table_context'].pop('header_context'),lambda v:v['table_context']['header_context'].update(cells=[]),lambda v:v['table_context']['header_context'].update(role='explicit_header'),lambda v:v['table_context']['header_context']['cells'][0].update(text='fabricated'),lambda v:v['table_context']['header_context']['cells'][0]['location'].update(coordinate='L1'),lambda v:v['table_context']['matched_cells'][0].update(row=1),lambda v:v['table_context'].update(needs_expansion=False),lambda v:v['table_context']['header_context']['cells'][0].update(text=header),lambda v:v.update(start=start-1)):
        bad=copy.deepcopy(hit);mutate(bad)
        with pytest.raises((AssertionError,KeyError)):assert_summary(bad,truth,'table')
    assert len(header.encode('utf-8'))>len(header) and len(header.encode('utf-16-le'))//2>len(header)
    observe('summary-oracle-controls',{'rejected_variants':10,'codepoint_budget':2000,'non_bmp':True})

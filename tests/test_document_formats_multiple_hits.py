"""A suggested table window is a truthful local range, not all distant hits."""
import copy,json
import pytest
from document_helpers import Fixture,observe,deny_source_reads
from document_formats_multi_fixture import multiple_source,nested_source
from document_formats_sync_observer import install as install_no_processing
from test_document_formats_table_context import capture,state,assert_text_window,assert_location,assert_cell


def same_location(actual,expected):
    try:assert_location(actual,expected)
    except (AssertionError,KeyError,TypeError):return False
    return True


def source_cell(actual,wanted,table):
    if table['format']!='pdf':return assert_cell(actual,wanted,table)
    for field in ('row','column','text','row_span','column_span'):assert actual[field]==wanted[field]
    assert actual['type']=='string'
    loc=actual['location'];start=table['text'].index(wanted['text'])
    assert_location(loc,{'page':table['location']['page'],'bbox':wanted['bbox'],'page_width':table['page_width'],'page_height':table['page_height'],'method':'native','start':start,'end':start+len(wanted['text'])})


def assert_view(view,truth,expected_window=None,anchor=False):
    assert (view['rows'],view['columns'])==(truth['rows'],truth['columns']);assert_location(view['location'],truth['location'])
    window=view['window'];r,re,c,ce=[window[k] for k in ('row_start','row_end','column_start','column_end')]
    assert 1<=r<re<=truth['rows']+1 and 1<=c<ce<=truth['columns']+1 and re-r<=20 and ce-c<=10
    if expected_window is not None:assert window==expected_window
    assert view['window_origin']==('search_hit' if anchor else 'table_start')
    expected={(x['row'],x['column']):x for x in truth['cells'] if r<=x['row']<re and c<=x['column']<ce}
    actual={(x['row'],x['column']):x for x in view['cells']};assert len(actual)==len(view['cells'])==len(expected) and set(actual)==set(expected)
    for rc,wanted in expected.items():source_cell(actual[rc],wanted,truth)
    headers=view['header_context'];assert headers['role']==truth['header_role']
    wanted={(x['row'],x['column']):x for x in truth['cells'] if x['row']==1 and c<=x['column']<ce}
    actual={(x['row'],x['column']):x for x in headers['cells']};assert len(actual)==len(headers['cells'])==len(wanted) and set(actual)==set(wanted)
    for rc,expected in wanted.items():source_cell(actual[rc],expected,truth)


def assert_selected_matches(context,table,queries):
    expected={(cell['row'],cell['column']):cell for cell in table['cells'] if cell['text'] in queries}
    matched=context['matched_cells'];assert matched
    coordinates={(cell['row'],cell['column']) for cell in matched};assert len(coordinates)==len(matched) and coordinates<=set(expected)
    for cell in matched:
        source=expected[(cell['row'],cell['column'])]
        assert (cell['row_span'],cell['column_span'])==(source['row_span'],source['column_span'])
        loc=cell['location'];r,c=cell['row'],cell['column']
        if table['format']=='docx':assert loc=={**table['location'],'path':table['location']['path']+'/row['+str(r)+']/cell['+str(c)+']'}
        else:
            start=table['text'].index(source['text']);wanted={'start':start,'end':start+len(source['text'])}
            if table['format']=='xlsx':
                from document_formats_table_fixture import letters
                wanted.update(**table['location'],coordinate=letters(c)+str(r))
            else:wanted.update(page=table['location']['page'],bbox=source['bbox'],method='native',page_width=table['page_width'],page_height=table['page_height'])
            assert_location(loc,wanted)
    return coordinates



def assert_unanchored_window(view,truth):
    assert view['window_origin']=='table_start'
    assert view['window']=={'row_start':1,'row_end':min(21,truth['rows']+1),'column_start':1,'column_end':min(11,truth['columns']+1)}

def exercise(f,source,project,items,monkeypatch):
    before=state(f);seen=[]
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*(item['path'] for item in items.values()))
        for name,item in items.items():
            truth=item['truth'];seen.append(item['entry']['id'])
            for queries in truth['queries']:
                hits=f.search(' '.join(queries),scope='project',project_id=project,local=True)['results']
                assert len(hits)==1 and hits[0]['id']==item['entry']['id'];hit=hits[0]
                assert_text_window(hit,truth);read=f.read(hit);assert_text_window(read,truth)
                assert (read['start'],read['end'],read['text'])==(hit['start'],hit['end'],hit['text'])
                assert read['id']==hit['id']==item['entry']['id'] and read['sha256']==hit['sha256']==item['entry']['sha256']
                assert read['version']==hit['version']==read['processing_version']==hit['processing_version']==1
                assert read['source_ids']==hit['source_ids']==[source['id']]
                context=hit['table_context'];summary=[t for t in read['tables'] if t['table_id']==context['table_id']];assert len(summary)==1
                selected=[t for t in truth['tables'] if same_location(summary[0]['location'],t['location'])];assert len(selected)==1;table=selected[0]
                coordinates=assert_selected_matches(context,table,queries)
                view=f.read(hit,view='table',table_id=context['table_id']);assert view['table_id']==context['table_id']
                assert_view(view,table,expected_window=context['suggested_window'],anchor=True)
                cells={(c['row'],c['column']) for c in view['cells']};assert cells&coordinates
                all_targets=[(t,c) for t in truth['tables'] for c in t['cells'] if c['text'] in queries]
                covered=[(t,c) for t,c in all_targets if t is table and (c['row'],c['column']) in cells]
                if len(covered)!=len(all_targets):assert not context.get('all_matches_covered',False) and not view.get('all_matches_covered',False)
                others=[t for t in truth['tables'] if t is not table]
                for other in others:
                    summaries=[t for t in read['tables'] if same_location(t['location'],other['location'])];assert len(summaries)==1
                    other_view=f.read(hit,view='table',table_id=summaries[0]['table_id'])
                    assert other_view['table_id']==summaries[0]['table_id'];assert_view(other_view,other)
                    assert_unanchored_window(other_view,other)
                observe('multiple-hits-'+name,{'queries':queries,'hit':hit,'text_read':read,'selected_view':view,'independent_matching_cells':len(all_targets),'actually_covered_cells':len(covered)})
        assert len(seen)==len(set(seen))==2 and state(f)==before and attempts==[] and reads==[]
        observe('multiple-hits-readonly',{'before':before,'after':state(f),'processing_attempts':attempts,'source_reads':reads})


@pytest.mark.parametrize('format',['docx','xlsx','pdf'])
def test_multiple_matches_keep_one_truthful_default_window(tmp_path,monkeypatch,format):
    # TC-008-table-multiple-hits; three format subpaths fail independently.
    f=Fixture(tmp_path);project=f.project('multiple matches');items={}
    for key in ('alpha','beta'):
        raw,truth=multiple_source(format,key);items[key+'.'+format]={'raw':raw,'truth':truth}
    source=capture(f,project,items);exercise(f,source,project,items,monkeypatch)


def test_nested_table_hit_does_not_borrow_parent_coordinates(tmp_path,monkeypatch):
    # Same TC, distinct Word structural-container condition.
    f=Fixture(tmp_path);project=f.project('nested tables');items={}
    for key in ('alpha','beta'):
        raw,truth=nested_source(key);items['nested-'+key+'.docx']={'raw':raw,'truth':truth}
    source=capture(f,project,items);exercise(f,source,project,items,monkeypatch)


def test_nested_match_oracle_rejects_parent_and_other_coordinates():
    raw,truth=nested_source('oracle');table=truth['tables'][1];source=table['cells'][0];loc={**table['location'],'path':table['location']['path']+'/row[1]/cell[1]'}
    good={'matched_cells':[{'row':1,'column':1,'row_span':1,'column_span':1,'location':loc}]}
    assert assert_selected_matches(good,table,truth['queries'][0])=={(1,1)}
    for alter in (lambda c:c['matched_cells'][0]['location'].update(path='body/table[1]/row[1]/cell[1]'),lambda c:c['matched_cells'][0].update(column=2),lambda c:c['matched_cells'][0].update(column_span=2),lambda c:c.update(matched_cells=[])):
        bad=copy.deepcopy(good);alter(bad)
        with pytest.raises(AssertionError):assert_selected_matches(bad,table,truth['queries'][0])
    with pytest.raises(AssertionError):assert_selected_matches(good,truth['tables'][0],truth['queries'][0])
    observe('nested-oracle-controls',{'parent_and_wrong_matches_rejected':5})


def test_multiple_source_fixtures_have_independent_targets():
    from io import BytesIO
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    for key in ('alpha','beta'):
        raw,truth=nested_source(key)
        with ZipFile(BytesIO(raw)) as z:
            root=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            assert '\n'.join(t.text for t in root.findall('.//w:t',ns))==truth['text']
            assert len(root.findall('.//w:tbl',ns))==2
            nested=root.find('./w:body/w:tbl/w:tr/w:tc/w:tbl',ns);assert nested is not None
            assert [t.text for t in nested.findall('.//w:t',ns)]==[key+'NestedA',key+'NestedB']
        for format in ('docx','xlsx','pdf'):
            raw,truth=multiple_source(format,key)
            for queries in truth['queries']:
                assert len(queries)==2 and len(set(queries))==2
                assert all(truth['text'].count(q)==1 for q in queries)
                matched=[(t,c) for t in truth['tables'] for c in t['cells'] if c['text'] in queries];assert len(matched)==2
                assert matched[0][0] is not matched[1][0] or abs(matched[0][1]['row']-matched[1][1]['row'])>200
    observe('multiple-fixture-controls',{'formats':3,'documents_each':2,'query_pairs_each':2,'nested_documents':2})


def test_unanchored_window_oracle_rejects_truncated_default_ranges():
    for truth,window in [({'rows':243,'columns':15},{'row_start':1,'row_end':21,'column_start':1,'column_end':11}),({'rows':1,'columns':2},{'row_start':1,'row_end':2,'column_start':1,'column_end':3})]:
        good={'window_origin':'table_start','window':window};assert_unanchored_window(good,truth)
        for key,value in [('row_start',2),('column_start',2),('row_end',window['row_end']+1),('column_end',2)]:
            wrong=copy.deepcopy(good);wrong['window'][key]=value
            with pytest.raises(AssertionError):assert_unanchored_window(wrong,truth)
        wrong=copy.deepcopy(good);wrong['window_origin']='explicit'
        with pytest.raises(AssertionError):assert_unanchored_window(wrong,truth)
    short={'window_origin':'table_start','window':{'row_start':1,'row_end':2,'column_start':1,'column_end':2}}
    with pytest.raises(AssertionError):assert_unanchored_window(short,{'rows':243,'columns':15})
    observe('unanchored-window-oracle',{'large_front':[20,10],'small_front':[1,2],'one_cell_default_rejected':True})

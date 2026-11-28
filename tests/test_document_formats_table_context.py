"""Public saved-result table windows: deep hit anchoring and exact combined quotas."""
import copy,hashlib,json,os
from pathlib import Path
import pytest
from document_helpers import Fixture,observe,deny_source_reads
from document_formats_table_fixture import deep_word,deep_xlsx,deep_pdf,quota_grid,quota_text,letters
from document_formats_sync_observer import install as install_no_processing


def keep(name,raw):
    if folder:=os.environ.get('ACCEPTANCE_EVIDENCE_DIR'):
        path=Path(folder)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def state(f):
    with f.db.connect() as con:
        tables=[row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'document_%'")]
        return {name:sorted([dict(row) for row in con.execute('SELECT * FROM "'+name+'"')],key=lambda row:json.dumps(row,sort_keys=True,default=str)) for name in tables}


def assert_box(actual,expected):
    assert len(actual)==len(expected)==4 and all(type(x) in (int,float) and 0<=x<=1 for x in actual)
    assert all(abs(a-b)<0.002 for a,b in zip(actual,expected)),(actual,expected)


def assert_location(actual,expected):
    for key,value in expected.items():
        if key=='bbox':assert_box(actual[key],value)
        else:assert actual[key]==value,key


def assert_cell(cell,expected,truth):
    for key in ('row','column','text','row_span','column_span'):assert cell[key]==expected[key],key
    loc=cell['location'];format=truth['format'];r,c=expected['row'],expected['column']
    if format=='docx':assert loc=={**truth['location'],'path':truth['location']['path']+'/row['+str(r)+']/cell['+str(c)+']'}
    elif format=='xlsx':
        assert_location(loc,{**truth['location'],'coordinate':letters(c)+str(r)})
        assert cell['sheet_state']==truth['sheet_state']
        assert cell['row_hidden']==(truth['sheet_state']=='hidden' and r==243)
        assert cell['column_hidden']==(truth['sheet_state']=='hidden' and c==11)
    else:
        assert_location(loc,{'page':2,'bbox':expected['bbox'],'page_width':truth['page_width'],'page_height':truth['page_height'],'method':'native'})
    if format!='docx':
        assert type(loc['start']) is int and type(loc['end']) is int
        assert truth['text'][loc['start']:loc['end']]==expected['text']
    assert cell['type']=='string'


def assert_window(view,truth,*,target=None,window=None):
    assert (view['rows'],view['columns'])==(truth['rows'],truth['columns'])
    assert_location(view['location'],truth['location'])
    bounds=view['window'];r,re,c,ce=[bounds[k] for k in ('row_start','row_end','column_start','column_end')]
    assert 1<=r<re<=truth['rows']+1 and 1<=c<ce<=truth['columns']+1
    if target is not None:
        assert re-r<=20 and ce-c<=10 and r<=target[0]<re and c<=target[1]<ce
        assert view['window_origin']=='search_hit'
    if window is not None:assert bounds==window
    wanted={(x['row'],x['column']):x for x in truth['cells'] if r<=x['row']<re and c<=x['column']<ce}
    actual={(x['row'],x['column']):x for x in view['cells']}
    assert len(actual)==len(view['cells'])==len(wanted) and set(actual)==set(wanted)
    for rc,expected in wanted.items():assert_cell(actual[rc],expected,truth)
    headers=view['header_context'];assert headers['role']==truth['header_role']
    wanted_headers={(x['row'],x['column']):x for x in truth['cells'] if x['row']==1 and c<=x['column']<ce}
    actual_headers={(x['row'],x['column']):x for x in headers['cells']}
    assert len(actual_headers)==len(headers['cells'])==len(wanted_headers) and set(actual_headers)==set(wanted_headers)
    for rc,expected in wanted_headers.items():assert_cell(actual_headers[rc],expected,truth)


def assert_text_window(value,truth):
    start,end=value['start'],value['end'];text=truth['text']
    assert type(start) is int and type(end) is int and 0<=start<end<=len(text)
    assert value['text']==text[start:end]
    assert value['start_line']==text.count('\n',0,start)+1
    assert value['end_line']==text.count('\n',0,max(start,end-1))+1


def capture(f,project,items):
    for name,item in items.items():
        item['path']=f.file(name,raw=item['raw']);keep('inputs/'+name,item['raw']);keep('truth/'+name+'.json',json.dumps(item['truth'],ensure_ascii=False).encode())
    source=f.add(f.root/'docs',[project]);f.refresh(source)
    files=f.files(source);assert len(files)==len(items) and {Path(row['path']).name for row in files}==set(items)
    for row in files:
        item=items[Path(row['path']).name];item['entry']=row
        assert row['status']=='ready' and row['version']==row['processing_version']==1
        assert row['sha256']==hashlib.sha256(item['raw']).hexdigest()
        result=(f.db.db_path.parent/'.document-snapshots/results'/row['published_snapshot']['result_sha256']).read_bytes()
        assert hashlib.sha256(result).hexdigest()==row['published_snapshot']['result_sha256']
        assert json.loads(result)['text']==item['truth']['text']
        keep('results/'+Path(row['path']).name+'.json',result);item['path'].unlink()
    return source


@pytest.mark.parametrize('format,maker',[('docx',deep_word),('xlsx',deep_xlsx),('pdf',deep_pdf)])
def test_deep_table_hit_context_and_default_window(tmp_path,monkeypatch,format,maker):
    # TC-008-table-context: each format executes independently, two documents.
    f=Fixture(tmp_path);project=f.project('deep tables');items={}
    for key in ('alpha','beta'):
        raw,truth=maker(key);items[key+'.'+format]={'raw':raw,'truth':truth}
    source=capture(f,project,items);before=state(f);seen=[]
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*(item['path'] for item in items.values()))
        targets=[]
        for name,item in items.items():
            truth=item['truth'];hits=f.search(truth['query'],scope='project',project_id=project,local=True)['results']
            assert len(hits)==1 and hits[0]['id']==item['entry']['id'];hit=hits[0]
            assert_text_window(hit,truth);read=f.read(hit);assert_text_window(read,truth)
            assert (read['start'],read['end'])==(hit['start'],hit['end'])
            assert read['id']==hit['id']==item['entry']['id'] and read['sha256']==hit['sha256']==item['entry']['sha256']
            assert read['version']==hit['version']==1 and read['processing_version']==hit['processing_version']==1
            candidates=[table for table in read['tables'] if all(key in table['location'] and (all(abs(a-b)<0.002 for a,b in zip(table['location'][key],value)) if key=='bbox' and len(table['location'][key])==4 else table['location'][key]==value) for key,value in truth['location'].items())]
            assert len(candidates)==1;table=candidates[0];assert_location(table['location'],truth['location'])
            context=hit['table_context'];assert context['table_id']==table['table_id']
            expected=next(c for c in truth['cells'] if [c['row'],c['column']]==truth['target'])
            matched=context['matched_cells'];assert any(all(cell[k]==expected[k] for k in ('row','column','row_span','column_span')) for cell in matched)
            view=f.read(hit,view='table',table_id=table['table_id'])
            assert view['table_id']==table['table_id'];assert_window(view,truth,target=truth['target'],window=context['suggested_window'])
            context_headers={'header_context':context['header_context']}
            assert context_headers['header_context']==view['header_context']
            targets.append((hit,table['table_id']));seen.append(hit['id']);observe('deep-'+name,{'hit':hit,'read':read,'table':view})
        assert len(set(seen))==2
        for index,(hit,table_id) in enumerate(targets):
            other=targets[1-index][1];assert other!=table_id
            f.bad('POST','/api/documents/read',{'reference':hit['reference'],'view':'table','table_id':other})
            view=f.read(hit,view='table',table_id=table_id);assert view['table_id']==table_id
        assert attempts==[] and reads==[] and state(f)==before
        observe('deep-queries-readonly',{'attempts':attempts,'source_reads':reads,'before':before,'after':state(f)})


def table_id(f,hit,truth):
    read=f.read(hit);assert_text_window(read,truth)
    assert len(read['tables'])==1
    table=read['tables'][0];assert_location(table['location'],truth['location'])
    return table['table_id']


def window(row_start,row_end,column_start,column_end):
    return dict(row_start=row_start,row_end=row_end,column_start=column_start,column_end=column_end)


def test_combined_window_header_cell_and_unicode_quotas(tmp_path,monkeypatch):
    # TC-008-table-context-bounds: actual parser/results, no lowered limits.
    f=Fixture(tmp_path);project=f.project('table quota');items={}
    for key in ('alpha','beta'):
        raw,truth=quota_grid(key);items[key+'-grid.xlsx']={'raw':raw,'truth':truth}
        for extra in (0,1):
            raw,truth=quota_text(key,extra);items[key+'-text-'+str(extra)+'.xlsx']={'raw':raw,'truth':truth,'extra':extra}
    source=capture(f,project,items);before=state(f)
    with monkeypatch.context() as guard:
        attempts=install_no_processing(guard);reads=deny_source_reads(guard,*(item['path'] for item in items.values()))
        for name,item in items.items():
            truth=item['truth'];hits=f.search(truth['query'],scope='project',project_id=project,local=True,limit=50)['results']
            same=[hit for hit in hits if hit['id']==item['entry']['id']];assert len(same)==1;hit=same[0]
            ident=table_id(f,hit,truth)
            if '-grid' in name:
                accepted=[window(1,41,1,26),window(2,41,1,26)];refused=[window(2,42,1,26)]
            else:
                cases=[window(1,3,1,2),window(2,3,1,2)];accepted=cases if item['extra']==0 else [];refused=cases if item['extra']==1 else []
                assert sum(len(c['text']) for c in truth['cells'])==16000+item['extra']
            for bounds in accepted:
                view=f.read(hit,view='table',table_id=ident,**bounds);assert_window(view,truth,window=bounds)
                observe('quota-accepted-'+name,{'window':bounds,'table':view})
            for bounds in refused:
                response=f.bad('POST','/api/documents/read',{'reference':hit['reference'],'view':'table','table_id':ident,**bounds})
                message=json.dumps(response.json(),ensure_ascii=False)
                assert ('1000' in message or '16000' in message) and '原件' in message
                observe('quota-rejected-'+name,{'window':bounds,'response':response.json()})
        assert attempts==[] and reads==[] and state(f)==before
        observe('quota-queries-readonly',{'attempts':attempts,'source_reads':reads,'before':before,'after':state(f)})


def expected_cell(source,truth):
    cell={**source,'type':'string'};r,c=cell['row'],cell['column']
    location={**truth['location'],'coordinate':letters(c)+str(r)}
    start=truth['text'].index(cell['text']);location.update(start=start,end=start+len(cell['text']))
    cell.update(location=location,sheet_state=truth['sheet_state'],row_hidden=r==243,column_hidden=c==11)
    return cell


def test_table_oracles_reject_wrong_target_header_offsets_and_coordinates(tmp_path,monkeypatch):
    _,truth=deep_xlsx('alpha');bounds=window(224,244,6,16)
    cells=[expected_cell(c,truth) for c in truth['cells']]
    view={'rows':243,'columns':15,'location':truth['location'],'window':bounds,'window_origin':'search_hit','cells':[c for c in cells if c['row']==243],'header_context':{'role':'first_content_row','cells':[c for c in cells if c['row']==1]}}
    assert_window(view,truth,target=truth['target'],window=bounds)
    bads=[]
    for mutate in (lambda v:v.update(window=window(1,21,1,11)),lambda v:v.update(rows=242),lambda v:v['cells'][0].update(text='wrong'),lambda v:v['cells'][0].update(column_span=1),lambda v:v['cells'][0]['location'].update(coordinate='K242'),lambda v:v['cells'][0].update(row_hidden=False),lambda v:v['header_context'].update(role='explicit_header'),lambda v:v['header_context'].update(cells=[]),lambda v:v['header_context']['cells'][0].update(text='wrong')):
        bad=copy.deepcopy(view);mutate(bad)
        with pytest.raises(AssertionError):assert_window(bad,truth,target=truth['target'],window=bounds)
        bads.append(bad)
    text=truth['text'];start=text.index(truth['query']);good={'start':start,'end':len(text),'text':text[start:],'start_line':text.count('\n',0,start)+1,'end_line':text.count('\n',0,len(text)-1)+1};assert_text_window(good,truth)
    for key,value in [('text','wrong'),('start',start-1),('start_line',1),('end_line',1)]:
        with pytest.raises(AssertionError):assert_text_window({**good,key:value},truth)
    path=tmp_path/'deleted-source.xlsx';path.write_bytes(b'source')
    with monkeypatch.context() as guard:
        attempts=deny_source_reads(guard,path)
        with pytest.raises(AssertionError):path.read_bytes()
        assert attempts==[str(path)]
    observe('table-oracles-selfcheck',{'bad_windows_rejected':len(bads),'bad_texts_rejected':4,'source_guard':attempts})


def test_source_defined_deep_and_quota_fixture_controls():
    from io import BytesIO
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    import pdfplumber
    for key in ('alpha','beta'):
        raw,truth=deep_word(key)
        with ZipFile(BytesIO(raw)) as z:
            root=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            values=[node.text for node in root.findall('.//w:t',ns)];assert '\n'.join(values)==truth['text']
            tables=root.findall('./w:body/w:tbl',ns);assert len(tables)==2
            rows=tables[1].findall('./w:tr',ns);assert len(rows)==243 and rows[0].find('./w:trPr/w:tblHeader',ns) is not None
            target=rows[242].findall('./w:tc',ns)[10];assert target.find('./w:tcPr/w:gridSpan',ns).attrib['{'+ns['w']+'}val']=='2'
            assert target.find('.//w:t',ns).text==truth['query']
        raw,truth=deep_xlsx(key)
        with ZipFile(BytesIO(raw)) as z:
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('./s:sheets/s:sheet',ns);assert len(sheets)==2 and sheets[1].attrib['state']=='hidden'
            root=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
            assert root.find('./s:mergeCells/s:mergeCell',ns).attrib['ref']=='K243:L243'
            assert root.find('./s:sheetData/s:row[@r="243"]',ns).attrib['hidden']=='1'
            assert root.find('./s:sheetData/s:row/s:c[@r="K243"]/s:is/s:t',ns).text==truth['query']
        raw,truth=deep_pdf(key)
        with pdfplumber.open(BytesIO(raw)) as pdf:
            assert len(pdf.pages)==2 and len(pdf.pages[1].extract_tables())==2
            assert pdf.pages[1].extract_tables()[1][-1][-1]==truth['query']
        raw,truth=quota_grid(key)
        assert len(truth['cells'])==1025 and len({(c['row'],c['column']) for c in truth['cells']})==1025
        for extra in (0,1):
            raw,truth=quota_text(key,extra);header=truth['cells'][0]['text']
            assert sum(len(c['text']) for c in truth['cells'])==16000+extra
            assert len(header.encode('utf-8'))>len(header) and len(header.encode('utf-16-le'))//2>len(header)
    observe('table-fixture-controls',{'formats':['docx','xlsx','pdf'],'documents_each':2,'cell_counts':[1000,1025],'unicode_counts':[16000,16001]})

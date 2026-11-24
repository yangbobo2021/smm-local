"""008 SpreadsheetML public-entry checks with independent complete coordinate truth."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from xml.etree import ElementTree as ET
import hashlib
import copy
import pytest
import re
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer


@pytest.fixture
def formula_trap():
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path);self.send_response(200);self.end_headers();self.wfile.write(b"MUST_NOT_FETCH")
        def log_message(self,*args):pass
    server=HTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield "http://127.0.0.1:"+str(server.server_port)+"/formula",calls
    finally:server.shutdown();server.server_close();thread.join(2)
from document_helpers import Fixture,fingerprint,observe
from document_formats_xlsx_fixture import xlsx_fixture,S


def verify_xlsx(f,hit,truth):
    result=f.read(hit,start=0,end=hit['text_length'])
    assert hit['format']=='xlsx' and hit['original_available'] is True
    locators=result['tables']; assert len(locators)==len({t['table_id'] for t in locators})==3
    by_sheet={t['location']['sheet']:t for t in locators}
    assert set(by_sheet)==set(truth['sheets'])
    views=[]
    for sheet,expected in truth['sheets'].items():
        view=f.read(hit,view='table',table_id=by_sheet[sheet]['table_id'])
        assert view['location']['sheet']==sheet
        assert view['sheet_state']==truth['sheet_states'][sheet]
        cells={c['location']['coordinate']:c for c in view['cells'] if not c.get('merged_into')}
        assert len(cells)==len([c for c in view['cells'] if not c.get('merged_into')])
        assert set(cells)==set(expected), (sheet,cells,expected)
        for coordinate,value in expected.items():
            cell=cells[coordinate]
            assert cell['location']['sheet']==sheet
            assert cell['location']['sheet_index']==list(truth['sheets']).index(sheet)+1
            letters,row=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',coordinate).groups()
            column=0
            for letter in letters:column=column*26+ord(letter)-64
            assert (cell['row'],cell['column'])==(int(row),column)
            assert value['text'] in result['text']
            assert cell['text']==value['text'] and cell['type']==value['type'], (sheet,coordinate,cell,value)
            assert cell['row_hidden']==(sheet=='Main' and coordinate.endswith('2'))
            assert cell['column_hidden']==(sheet=='Main' and coordinate.startswith('B'))
            assert cell['sheet_state']==truth['sheet_states'][sheet]
            if value['type']=='formula':
                assert cell['formula']==value['formula']
                assert cell['cache']['status']==value['cache']['status']
                assert cell['cache'].get('value')==value['cache']['value']
                if value['cache']['status']=='present':
                    assert cell['cache']['freshness']=='unknown'
                    assert cell['cache']['type']==value['cache']['type']
            if value['type']=='date':
                assert cell['date']=={'serial':value['serial'],'iso':value['iso'],'number_format':value['number_format'],'date_system':'1904' if truth['date1904'] else '1900'}
            if coordinate=='G2' and sheet=='Main':
                assert (cell['row_span'],cell['column_span'])==(1,2)
            else:
                assert (cell['row_span'],cell['column_span'])==(1,1)
        for continuation in [c for c in view['cells'] if c.get('merged_into')]:
            assert sheet=='Main' and continuation['location']['coordinate']=='H2'
            assert continuation['text'] in ('',None)
            assert continuation['merged_into']=={'row':2,'column':7}
        views.append(view)
        for coordinate,query in truth['queries'][sheet].items():
            found=f.search(query,scope='project',project_id=truth['project'],local=True,limit=50)['results']
            targets=[h for h in found if h['id']==hit['id']]
            assert len(targets)==1
            assert any(loc['sheet']==sheet and loc['coordinate']==coordinate for loc in targets[0]['locations'])
    observe('xlsx-'+truth['key'],{'hit':hit,'read':result,'tables':views})
    return result


def test_xlsx_complete_cells_formulas_dates_and_update(tmp_path,formula_trap):
    # TC-008-xlsx: separate files/three sheets, before and after actual replacement.
    f=Fixture(tmp_path);project=f.project('008 Excel');items={};url,calls=formula_trap
    for key,calendar in [('sheetalpha',False),('sheetbeta',True)]:
        raw,truth=xlsx_fixture(key,date1904=calendar,formula_url=url);truth['project']=project
        path=f.file(key+'.xlsx',raw=raw)
        items[path.name]={'path':path,'raw':raw,'truth':truth,'before':fingerprint(path)}
    source=f.add(tmp_path/'docs',projects=[project])
    refreshed=f.refresh(source)
    assert refreshed['sources'][0]['counts']['ready']==2, 'both supported XLSX files must become searchable'
    assert calls==[], calls
    hits=f.search('sheetalphaTitle sheetbetaTitle',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==2 and {Path(h['path']).name for h in hits}==set(items)
    old={}
    for hit in hits:
        item=items[Path(hit['path']).name];verify_xlsx(f,hit,item['truth']);old[Path(hit['path']).name]=hit
        response=f.client.post('/api/documents/original',json={'reference':hit['reference']})
        assert response.status_code==200 and response.content==item['raw']
        assert fingerprint(item['path'])==item['before']
    raw,new_truth=xlsx_fixture('sheetalpha',updated=True,formula_url=url);new_truth['project']=project
    items['sheetalpha.xlsx']['path'].write_bytes(raw)
    new_before=fingerprint(items['sheetalpha.xlsx']['path'])
    refreshed=f.refresh(source);assert refreshed['sources'][0]['counts']['ready']==2
    hits=f.search('sheetalphaUpdated sheetbetaTitle',scope='project',project_id=project,local=True,limit=50)['results']
    assert len(hits)==2 and {Path(h['path']).name for h in hits}==set(items)
    for hit in hits:
        name=Path(hit['path']).name
        if name=='sheetalpha.xlsx':
            assert hit['version']==old[name]['version']+1
            verify_xlsx(f,hit,new_truth)
            download=f.client.post('/api/documents/original',json={'reference':hit['reference']})
            assert download.status_code==200 and download.content==raw
            assert hit['sha256']==hashlib.sha256(raw).hexdigest()
            assert fingerprint(items['sheetalpha.xlsx']['path'])==new_before
            f.bad('POST','/api/documents/read',{'reference':old[name]['reference']})
        else:
            assert hit['version']==old[name]['version']
            verify_xlsx(f,hit,items[name]['truth'])
            assert f.read(old[name],start=0,end=old[name]['text_length'])['text']==f.read(hit,start=0,end=hit['text_length'])['text']
            response=f.client.post('/api/documents/original',json={'reference':old[name]['reference']})
            assert response.status_code==200 and response.content==items[name]['raw']
            assert fingerprint(items[name]['path'])==items[name]['before']

    assert calls==[], calls


def test_xlsx_independent_fixture_cells():
    for key,calendar,changed in [('sheetalpha',False,False),('sheetbeta',True,False),('sheetalpha',False,True),('sheetbeta',True,True)]:
        raw,truth=xlsx_fixture(key,date1904=calendar,updated=changed)
        with ZipFile(BytesIO(raw)) as z:
            workbook=ET.fromstring(z.read('xl/workbook.xml'))
            ns={'s':S}
            assert workbook.find('s:workbookPr',ns).attrib['date1904']==str(int(calendar))
            for i,(sheet,expected) in enumerate(truth['sheets'].items(),1):
                root=ET.fromstring(z.read('xl/worksheets/sheet'+str(i)+'.xml'))
                cells={c.attrib['r']:c for c in root.findall('.//s:c',ns)}
                assert set(cells)==set(expected)
                shared=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
                for coordinate,cell in cells.items():
                    value=expected[coordinate];v=cell.find('s:v',ns)
                    if value['type']=='string':
                        actual=shared[int(v.text)] if cell.attrib.get('t')=='s' else ''.join(cell.find('s:is',ns).itertext())
                        assert actual==value['text']
                    elif value['type']=='boolean':assert v.text==('1' if value['text']=='TRUE' else '0')
                    elif value['type']=='date':assert v.text==value['serial'] and cell.attrib['s']=='1'
                    elif value['type'] in {'number','error'}:assert v.text==value['text']
                    if expected[coordinate]['type']=='formula':
                        assert cell.find('s:f',ns).text==expected[coordinate]['formula']
                        assert (cell.find('s:v',ns) is not None)==(expected[coordinate]['cache']['status']=='present')
            assert sum(map(len,truth['sheets'].values()))==16


def test_xlsx_observer_self_check():
    _,truth=xlsx_fixture('observer',date1904=True);truth['project']=1
    hit={'id':'fixture-only','reference':'fixture-only','text_length':1000,'format':'xlsx','original_available':True}
    tables={};locators=[]
    for index,(sheet,expected) in enumerate(truth['sheets'].items(),1):
        ident=str(index);locators.append({'table_id':ident,'location':{'sheet':sheet}});cells=[]
        for coord,value in expected.items():
            letters,row=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',coord).groups();column=0
            for letter in letters:column=column*26+ord(letter)-64
            cell={'location':{'coordinate':coord,'sheet':sheet,'sheet_index':index},'row':int(row),'column':column,'text':value['text'],'type':value['type'],'row_hidden':sheet=='Main' and row=='2','column_hidden':sheet=='Main' and letters=='B','sheet_state':truth['sheet_states'][sheet],'row_span':1,'column_span':2 if sheet=='Main' and coord=='G2' else 1}
            if value['type']=='formula':cell.update(formula=value['formula'],cache=value['cache'])
            if value['type']=='date':cell['date']={'serial':value['serial'],'iso':value['iso'],'number_format':value['number_format'],'date_system':'1904'}
            cells.append(cell)
        tables[ident]={'location':{'sheet':sheet},'sheet_state':truth['sheet_states'][sheet],'cells':cells}
    hit['locations']=[copy.deepcopy(cell['location']) for table in tables.values() for cell in table['cells']]
    class Known:
        def __init__(self):self.tables=copy.deepcopy(tables)
        def read(self,hit,**kwargs):
            if kwargs.get('view')=='table':return self.tables[kwargs['table_id']]
            return {'text':'\n'.join(c['text'] for t in tables.values() for c in t['cells']),'tables':locators}
        def search(self,*args,**kwargs):return {'results':[{**hit,'locations':[{'sheet':sheet,'coordinate':coordinate} for sheet,cells in truth['sheets'].items() for coordinate in cells]}]}
    verify_xlsx(Known(),hit,truth)
    for mutate in ('missing_cell','duplicate','wrong_coordinate','wrong_calendar','wrong_cache','wrong_hidden'):
        known=Known();cells=known.tables['1']['cells']
        if mutate=='missing_cell':known.tables['3']['cells'].pop()
        elif mutate=='duplicate':cells.append(copy.deepcopy(cells[0]))
        elif mutate=='wrong_coordinate':cells[-1]['column']=1
        elif mutate=='wrong_calendar':next(c for c in cells if c['type']=='date')['date']['date_system']='1900'
        elif mutate=='wrong_cache':next(c for c in cells if c['location']['coordinate']=='D2')['cache']['value']='999'
        elif mutate=='wrong_hidden':known.tables['3']['sheet_state']='visible'
        with pytest.raises(AssertionError):verify_xlsx(known,hit,truth)

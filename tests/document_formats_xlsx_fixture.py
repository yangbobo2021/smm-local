"""Independent SpreadsheetML inputs and exact cell truth; no product imports."""
from html import escape
from document_formats_fixtures import package
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'


def xlsx_fixture(key, *, date1904=False, updated=False, formula_url="https://example.invalid/"):
    title=key+('Updated' if updated else 'Title')
    values={
        'Main':{'A1':{'text':title,'type':'string'},'B1':{'text':key+'Header','type':'string'},
                'A2':{'text':'42.5','type':'number'},'B2':{'text':'TRUE','type':'boolean'},
                'C2':{'text':'#DIV/0!','type':'error'},
                'D2':{'text':'=SUM(1,2) [cached: 3]','type':'formula','formula':'SUM(1,2)','cache':{'status':'present','value':'3','type':'number','freshness':'unknown'}},
                'E2':{'text':'=AVERAGE(8,4) [cache: missing]','type':'formula','formula':'AVERAGE(8,4)','cache':{'status':'missing','value':None,'freshness':'unknown'}},
                'F2':{'text':'="" [cached: ]','type':'formula','formula':'""','cache':{'status':'present','value':'','type':'string','freshness':'unknown'}},
                'G2':{'text':key+'Merged','type':'string'},
                'A3':{'text':'1904-01-01' if date1904 else '2024-01-01','type':'date','serial':'0' if date1904 else '45292','iso':'1904-01-01' if date1904 else '2024-01-01','number_format':'mm-dd-yy'},
                'B3':{'text':key+'Inline','type':'string'},
                'C3':{'text':'=HYPERLINK("'+formula_url+'", "'+key+'Link") [cache: missing]','type':'formula','formula':'HYPERLINK("'+formula_url+'", "'+key+'Link")','cache':{'status':'missing','value':None,'freshness':'unknown'}}},
        'Hidden':{'A1':{'text':key+'Hidden','type':'string'},'B2':{'text':'FALSE','type':'boolean'}},
        'VeryHidden':{'A1':{'text':key+'VeryHidden','type':'string'},'B2':{'text':'-7135903','type':'number'}}}
    if updated:
        values['Main']['A2']['text']='91.25';values['Main']['B2']['text']='FALSE';values['Main']['C2']['text']='#REF!'
        values['Main']['D2'].update(text='=SUM(6,3) [cached: 9]',formula='SUM(6,3)',cache={'status':'present','value':'9','type':'number','freshness':'unknown'})
        values['Main']['E2'].update(text='=MAX(8,4) [cache: missing]',formula='MAX(8,4)')
        values['Main']['A3'].update(text='1904-01-02' if date1904 else '2024-01-02',serial='1' if date1904 else '45293',iso='1904-01-02' if date1904 else '2024-01-02')
        values['Main']['B3']['text']=key+'InlineUpdated'
        values['Hidden']['A1']['text']=key+'HiddenUpdated';values['Hidden']['B2']['text']='TRUE'
        values['VeryHidden']['A1']['text']=key+'VeryHiddenUpdated';values['VeryHidden']['B2']['text']='-8549216'
    queries={}
    for sheet,cells in values.items():
        queries[sheet]={}
        for coordinate,value in cells.items():
            if value['type']=='formula':
                if value['formula']=='""':continue # no searchable token; exact structure still required
                query=value['formula'].split('(',1)[0]
            else:query=value['text']
            queries[sheet][coordinate]=query
    shared=[value['text'] for sheet,cells in values.items() for coordinate,value in cells.items() if value['type']=='string' and not (sheet=='Main' and coordinate=='B3')]
    files={};states={'Main':'visible','Hidden':'hidden','VeryHidden':'veryHidden'}
    for number,(name,cells) in enumerate(values.items(),1):
        rows={}
        for coordinate,value in cells.items():
            row=int(''.join(c for c in coordinate if c.isdigit()));kind=value['type'];kind_attr='';content=''
            if kind=='string':
                if name=='Main' and coordinate=='B3':kind_attr=' t="inlineStr"';content='<is><t>'+escape(value['text'])+'</t></is>'
                else:kind_attr=' t="s"';content='<v>'+str(shared.index(value['text']))+'</v>'
            elif kind=='formula':
                if value['cache'].get('type')=='string':kind_attr=' t="str"'
                content='<f>'+escape(value['formula'])+'</f>'
                if value['cache']['status']=='present':content+='<v>'+escape(value['cache']['value'])+'</v>'
            else:
                if kind=='boolean':kind_attr=' t="b"';raw_value='1' if value['text']=='TRUE' else '0'
                elif kind=='error':kind_attr=' t="e"';raw_value=value['text']
                elif kind=='date':kind_attr=' s="1"';raw_value=value['serial']
                else:raw_value=value['text']
                content='<v>'+escape(raw_value)+'</v>'
            rows.setdefault(row,[]).append('<c r="'+coordinate+'"'+kind_attr+'>'+content+'</c>')
        data=''.join('<row r="'+str(row)+'"'+(' hidden="1"' if name=='Main' and row==2 else '')+'>'+''.join(items)+'</row>' for row,items in rows.items())
        before='<cols><col min="2" max="2" hidden="1"/></cols>' if name=='Main' else ''
        after='<sheetProtection sheet="1"/><mergeCells count="1"><mergeCell ref="G2:H2"/></mergeCells>' if name=='Main' else ''
        files['xl/worksheets/sheet'+str(number)+'.xml']='<worksheet xmlns="'+S+'">'+before+'<sheetData>'+data+'</sheetData>'+after+'</worksheet>'
    files['xl/workbook.xml']='<workbook xmlns="'+S+'" xmlns:r="'+R+'"><workbookPr date1904="'+('1' if date1904 else '0')+'"/><sheets>'+''.join('<sheet name="'+name+'" sheetId="'+str(i)+'" state="'+states[name]+'" r:id="s'+str(i)+'"/>' for i,name in enumerate(values,1))+'</sheets></workbook>'
    relations=''.join('<Relationship Id="s'+str(i)+'" Type="'+R+'/worksheet" Target="worksheets/sheet'+str(i)+'.xml"/>' for i in range(1,4))
    relations+='<Relationship Id="styles" Type="'+R+'/styles" Target="styles.xml"/><Relationship Id="strings" Type="'+R+'/sharedStrings" Target="sharedStrings.xml"/>'
    files['xl/_rels/workbook.xml.rels']='<Relationships xmlns="'+P+'">'+relations+'</Relationships>'
    files['xl/styles.xml']='<styleSheet xmlns="'+S+'"><fonts count="1"><font/></fonts><fills count="1"><fill/></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>'
    files['xl/sharedStrings.xml']='<sst xmlns="'+S+'" count="'+str(len(shared))+'" uniqueCount="'+str(len(shared))+'">'+''.join('<si><t>'+escape(t)+'</t></si>' for t in shared)+'</sst>'
    files['_rels/.rels']='<Relationships xmlns="'+P+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    types={'/xl/workbook.xml':'sheet.main','/xl/styles.xml':'styles','/xl/sharedStrings.xml':'sharedStrings',**{'/xl/worksheets/sheet'+str(i)+'.xml':'worksheet' for i in range(1,4)}}
    files['[Content_Types].xml']='<Types xmlns="'+C+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+''.join('<Override PartName="'+path+'" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'+kind+'+xml"/>' for path,kind in types.items())+'</Types>'
    return package(files), {'key':key,'title':title,'sheets':values,'sheet_states':states,'date1904':date1904,'queries':queries,'updated':updated}

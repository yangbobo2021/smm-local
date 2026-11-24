"""Source-defined deep table positions and exact quota inputs; no SMM imports."""
from html import escape
from document_formats_fixtures import package,W,R,REL,CT
from document_formats_pdf_fixture import native_pdf

S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def letters(column):
    value=''
    while column:column,rem=divmod(column-1,26);value=chr(65+rem)+value
    return value


def workbook(sheets):
    files={};order=[]
    for index,sheet in enumerate(sheets,1):
        rows={}
        for cell in sorted(sheet['cells'],key=lambda c:(c['row'],c['column'])):
            coordinate=letters(cell['column'])+str(cell['row'])
            xml='<c r="'+coordinate+'" t="inlineStr"><is><t xml:space="preserve">'+escape(cell['text'])+'</t></is></c>'
            rows.setdefault(cell['row'],[]).append(xml);order.append(cell['text'])
        content=''.join('<row r="'+str(row)+'"'+(' hidden="1"' if row in sheet.get('hidden_rows',[]) else '')+'>'+''.join(cells)+'</row>' for row,cells in rows.items())
        cols=''.join('<col min="'+str(col)+'" max="'+str(col)+'" hidden="1"/>' for col in sheet.get('hidden_columns',[]))
        merges=sheet.get('merges',[])
        files['xl/worksheets/sheet'+str(index)+'.xml']='<worksheet xmlns="'+S+'">'+('<cols>'+cols+'</cols>' if cols else '')+'<sheetData>'+content+'</sheetData>'+('<mergeCells>'+''.join('<mergeCell ref="'+ref+'"/>' for ref in merges)+'</mergeCells>' if merges else '')+'</worksheet>'
    files['xl/workbook.xml']='<workbook xmlns="'+S+'" xmlns:r="'+R+'"><sheets>'+''.join('<sheet name="'+sheet['name']+'" sheetId="'+str(i)+'" state="'+sheet.get('state','visible')+'" r:id="s'+str(i)+'"/>' for i,sheet in enumerate(sheets,1))+'</sheets></workbook>'
    files['xl/_rels/workbook.xml.rels']='<Relationships xmlns="'+REL+'">'+''.join('<Relationship Id="s'+str(i)+'" Type="'+R+'/worksheet" Target="worksheets/sheet'+str(i)+'.xml"/>' for i in range(1,len(sheets)+1))+'</Relationships>'
    files['_rels/.rels']='<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="xl/workbook.xml"/></Relationships>'
    types={'/xl/workbook.xml':'sheet.main',**{'/xl/worksheets/sheet'+str(i)+'.xml':'worksheet' for i in range(1,len(sheets)+1)}}
    files['[Content_Types].xml']='<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+''.join('<Override PartName="'+part+'" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'+kind+'+xml"/>' for part,kind in types.items())+'</Types>'
    return package(files),'\n'.join(order)


def deep_word(key):
    heading=key+' Word Ω😀';first=[{'row':1,'column':c,'text':key+'Overview'+str(c),'row_span':1,'column_span':1} for c in (1,2)]
    target=key+'DeepTarget';cells=[]
    for row in range(1,244):
        for col in range(1,16):
            if row==243 and col==12:continue
            text=target if (row,col)==(243,11) else key+'R'+str(row)+'C'+str(col)
            cells.append({'row':row,'column':col,'text':text,'row_span':1,'column_span':2 if (row,col)==(243,11) else 1})
    def table(values,columns,header=False):
        data=[]
        for row in sorted({c['row'] for c in values}):
            line=''.join('<w:tc><w:tcPr>'+('<w:gridSpan w:val="2"/>' if c['column_span']==2 else '')+'</w:tcPr><w:p><w:r><w:t>'+escape(c['text'])+'</w:t></w:r></w:p></w:tc>' for c in values if c['row']==row)
            data.append('<w:tr><w:trPr>'+('<w:tblHeader/>' if header and row==1 else '')+'</w:trPr>'+line+'</w:tr>')
        return '<w:tbl><w:tblPr/><w:tblGrid>'+('<w:gridCol w:w="1000"/>'*columns)+'</w:tblGrid>'+''.join(data)+'</w:tbl>'
    body='<w:p><w:r><w:t>'+escape(heading)+'</w:t></w:r></w:p>'+table(first,2)+table(cells,15,True)
    files={'word/document.xml':'<w:document xmlns:w="'+W+'"><w:body>'+body+'</w:body></w:document>',
           '_rels/.rels':'<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/></Relationships>',
           '[Content_Types].xml':'<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'}
    truth={'format':'docx','query':target,'text':'\n'.join([heading]+[c['text'] for c in first+cells]),'rows':243,'columns':15,'target':[243,11],'header_role':'explicit_header','location':{'part':'word/document.xml','path':'body/table[2]'},'cells':cells}
    return package(files),truth


def deep_xlsx(key):
    cells=[{'row':1,'column':col,'text':key+'Header'+str(col),'row_span':1,'column_span':1} for col in (11,12,15)]
    target=key+'DeepTarget';cells.append({'row':243,'column':11,'text':target,'row_span':1,'column_span':2})
    raw,text=workbook([{'name':'Overview','cells':[{'row':1,'column':1,'text':key+'Overview'}]}, {'name':'Hidden Details','state':'hidden','cells':cells,'hidden_rows':[243],'hidden_columns':[11],'merges':['K243:L243']}])
    return raw,{'format':'xlsx','query':target,'text':text,'rows':243,'columns':15,'target':[243,11],'header_role':'first_content_row','location':{'part':'xl/worksheets/sheet2.xml','sheet':'Hidden Details','sheet_index':2},'cells':cells,'sheet_state':'hidden'}


def deep_pdf(key):
    raw,source=native_pdf('native'+key);page=source['pages'][1];table=page['tables'][1]
    cells=[{**c,'row_span':1,'column_span':1} for c in table['cells']]
    return raw,{'format':'pdf','query':cells[-1]['text'],'text':'\n'.join(source['order']),'rows':3,'columns':2,'target':[3,2],'header_role':'first_content_row','location':{'page':2,'bbox':table['bbox']},'cells':cells,'page_width':page['width'],'page_height':page['height']}


def quota_grid(key):
    cells=[{'row':r,'column':c,'text':key+'R'+str(r)+'C'+str(c),'row_span':1,'column_span':1} for r in range(1,42) for c in range(1,26)]
    raw,text=workbook([{'name':key,'cells':cells}])
    return raw,{'format':'xlsx','query':cells[-1]['text'],'text':text,'rows':41,'columns':25,'cells':cells,'header_role':'first_content_row','location':{'part':'xl/worksheets/sheet1.xml','sheet':key,'sheet_index':1},'sheet_state':'visible'}


def quota_text(key,extra):
    target=key+'Target';pattern='甲😀' if key=='alpha' else '乙😀'
    header=(pattern*8001)[:16000-len(target)+extra]
    cells=[{'row':1,'column':1,'text':header,'row_span':1,'column_span':1},{'row':2,'column':1,'text':target,'row_span':1,'column_span':1}]
    raw,text=workbook([{'name':key,'cells':cells}])
    return raw,{'format':'xlsx','query':target,'text':text,'rows':2,'columns':1,'cells':cells,'header_role':'first_content_row','location':{'part':'xl/worksheets/sheet1.xml','sheet':key,'sheet_index':1},'sheet_state':'visible'}

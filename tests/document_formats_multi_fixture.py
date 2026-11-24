"""Independent distant-table and nested-container truth; no SMM imports."""
from html import escape
from document_formats_fixtures import package,W,R,REL,CT
from document_formats_table_fixture import deep_word,deep_xlsx
from document_formats_pdf_fixture import native_pdf


def cell(row,column,text,**values):return {'row':row,'column':column,'text':text,'row_span':1,'column_span':1,**values}


def multiple_source(format,key):
    if format in {'docx','xlsx'}:
        raw,second=(deep_word if format=='docx' else deep_xlsx)(key)
        first={'format':format,'text':second['text'],'rows':1,'columns':2 if format=='docx' else 1,'header_role':'first_content_row','cells':[cell(1,c,key+'Overview'+(str(c) if format=='docx' else '')) for c in ((1,2) if format=='docx' else (1,))],
               'location':{'part':'word/document.xml','path':'body/table[1]'} if format=='docx' else {'part':'xl/worksheets/sheet1.xml','sheet':'Overview','sheet_index':1}}
        if format=='xlsx':first['sheet_state']='visible'
        queries=[[second['cells'][10 if format=='docx' else 0]['text'],second['query']],[first['cells'][0]['text'],second['query']]]
        return raw,{'format':format,'text':second['text'],'tables':[first,second],'queries':queries}
    raw,source=native_pdf('native'+key);text='\n'.join(source['order']);tables=[]
    for page in source['pages']:
        for table in page['tables']:
            tables.append({'format':'pdf','text':text,'rows':3,'columns':2,'header_role':'first_content_row','location':{'page':page['page'],'bbox':table['bbox']},'cells':[{**c,'row_span':1,'column_span':1} for c in table['cells']],'page_width':page['width'],'page_height':page['height']})
    return raw,{'format':'pdf','text':text,'tables':tables,'queries':[[tables[0]['cells'][0]['text'],tables[2]['cells'][-1]['text']],[tables[1]['cells'][0]['text'],tables[2]['cells'][-1]['text']]]}


def nested_source(key):
    def p(value):return '<w:p><w:r><w:t>'+escape(value)+'</w:t></w:r></w:p>'
    def tc(value,inside=''):return '<w:tc><w:tcPr/>'+p(value)+inside+'</w:tc>'
    def table(cells):return '<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="1800"/><w:gridCol w:w="1800"/></w:tblGrid><w:tr>'+cells+'</w:tr></w:tbl>'
    heading=key+' Heading Ω😀';outer=key+'Outer';a=key+'NestedA';b=key+'NestedB';outside=key+'Outside'
    body=p(heading)+table(tc(outer,table(tc(a)+tc(b)))+tc(outside));text='\n'.join([heading,outer,a,b,outside])
    files={'word/document.xml':'<w:document xmlns:w="'+W+'"><w:body>'+body+'</w:body></w:document>',
        '_rels/.rels':'<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/></Relationships>',
        '[Content_Types].xml':'<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'}
    tables=[]
    for path,values in [('body/table[1]',[outer,outside]),('body/table[1]/row[1]/cell[1]/table[1]',[a,b])]:
        tables.append({'format':'docx','text':text,'rows':1,'columns':2,'header_role':'first_content_row','location':{'part':'word/document.xml','path':path},'cells':[cell(1,c,value) for c,value in enumerate(values,1)]})
    return package(files),{'format':'docx','text':text,'tables':tables,'queries':[[a]]}

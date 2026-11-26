"""Office source tables with a real A1:N1 heading and deep M243 match."""
from html import escape
from document_formats_fixtures import package, W, R, REL, CT
from document_formats_table_fixture import workbook, letters


def merged_header(format, key, length):
    prefix=key+'HeaderΩ😀';header=prefix+('甲😀'*length)[:length-len(prefix)]
    assert len(header)==length
    other=[key+'OtherO',key+'OtherP'];target=key+'DeepTarget';tail=key+'Tail'
    location={'part':'word/document.xml','path':'body/table[1]'} if format=='docx' else {'part':'xl/worksheets/sheet1.xml','sheet':key,'sheet_index':1}
    heads=[{'row':1,'column':c,'text':t,'row_span':1,'column_span':span} for c,t,span in [(1,header,14),(15,other[0],1),(16,other[1],1)]]
    if format=='xlsx':
        cells=heads+[{'row':243,'column':13,'text':target,'row_span':1,'column_span':1},{'row':250,'column':16,'text':tail,'row_span':1,'column_span':1}]
        raw,text=workbook([{'name':key,'cells':cells,'merges':['A1:N1']}])
    else:
        cells=list(heads)
        for row in range(2,251):
            for column in range(1,17):cells.append({'row':row,'column':column,'text':target if (row,column)==(243,13) else tail if (row,column)==(250,16) else '', 'row_span':1,'column_span':1})
        rows=[]
        for row in range(1,251):
            body=''.join('<w:tc><w:tcPr>'+('<w:gridSpan w:val="14"/>' if c['column_span']==14 else '')+'</w:tcPr><w:p><w:r><w:t>'+escape(c['text'])+'</w:t></w:r></w:p></w:tc>' for c in cells if c['row']==row)
            rows.append('<w:tr>'+('<w:trPr><w:tblHeader/></w:trPr>' if row==1 else '')+body+'</w:tr>')
        xml='<w:document xmlns:w="'+W+'"><w:body><w:tbl><w:tblPr/><w:tblGrid>'+('<w:gridCol w:w="1000"/>'*16)+'</w:tblGrid>'+''.join(rows)+'</w:tbl></w:body></w:document>'
        raw=package({'word/document.xml':xml,'_rels/.rels':'<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/></Relationships>','[Content_Types].xml':'<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'})
        text='\n'.join([header,*other,target,tail])
    assert text=='\n'.join([header,*other,target,tail])
    for c in cells:
        c['type']='string'
        if format=='docx':c['location']={**location,'path':location['path']+'/row['+str(c['row'])+']/cell['+str(c['column'])+']'}
        else:
            start=text.index(c['text']);c.update(sheet_state='visible',row_hidden=False,column_hidden=False)
            c['location']={**location,'coordinate':letters(c['column'])+str(c['row']),'start':start,'end':start+len(c['text'])}
    return raw,{'format':format,'text':text,'header_length':length,'query':target,'rows':250,'columns':16,'location':location,'header_role':'explicit_header' if format=='docx' else 'first_content_row','headers':heads,'cells':cells}

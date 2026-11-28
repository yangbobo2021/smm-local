"""Independent OOXML/PDF inputs and source-defined truth; no product imports."""
from __future__ import annotations
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'

def package(files):
    out = BytesIO()
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        for name, value in files.items():
            z.writestr(name, value.encode('utf-8') if isinstance(value, str) else value)
    return out.getvalue()

def docx_fixture(key):
    def p(value):
        return '<w:p><w:r><w:t xml:space="preserve">'+escape(value)+'</w:t></w:r></w:p>'
    def cell(value='', props='', nested=''):
        return '<w:tc><w:tcPr>'+props+'</w:tcPr>'+p(value)+nested+'</w:tc>'
    def row(values, props=''):
        return '<w:tr><w:trPr>'+props+'</w:trPr>'+''.join(values)+'</w:tr>'
    def table(rows, columns):
        return '<w:tbl><w:tblPr/><w:tblGrid>'+''.join('<w:gridCol w:w="1800"/>' for _ in range(columns))+'</w:tblGrid>'+''.join(rows)+'</w:tbl>'
    title = key+' 正文 Chinese 中文证据 Ω😀'
    before, after = key+'Before', key+'After'
    insert, deleted = key+'Inserted', key+'Deleted'
    a = [[key+'HeadA', key+'HeadB'], [key+'MergedWide']]
    nested = table([row([cell(key+'NestedA'), cell(key+'NestedB')])], 2)
    t1 = table([row([cell(a[0][0]), cell(a[0][1])], '<w:tblHeader/>'), row([cell(a[1][0], '<w:gridSpan w:val="2"/>')])], 2)
    t2 = table([row([cell(key+'Tall', '<w:vMerge w:val="restart"/>'), cell(key+'SecondB')]), row([cell('', '<w:vMerge/>'), cell(key+'SecondD', nested=nested)])], 2)
    body = p(title)+p(before)+t1+t2+'<w:p><w:ins w:id="1"><w:r><w:t>'+insert+'</w:t></w:r></w:ins><w:del w:id="2"><w:r><w:delText>'+deleted+'</w:delText></w:r></w:del></w:p>'+p(after)+'<w:p><w:r><w:drawing/></w:r></w:p>'
    sect = '<w:sectPr><w:headerReference w:type="default" r:id="header"/><w:footerReference w:type="default" r:id="footer"/></w:sectPr>'
    names = {'header1':'header', 'footer1':'footer', 'footnotes':'footnotes', 'endnotes':'endnotes'}
    content_types = '<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    relations = '<Relationships xmlns="'+REL+'">'
    for part, kind in names.items():
        content_types += '<Override PartName="/word/'+part+'.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.'+kind+'+xml"/>'
        relations += '<Relationship Id="'+kind+'" Type="'+R+'/'+kind+'" Target="'+part+'.xml"/>'
    files = {'[Content_Types].xml':content_types+'</Types>', '_rels/.rels':'<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/></Relationships>', 'word/_rels/document.xml.rels':relations+'</Relationships>', 'word/document.xml':'<w:document xmlns:w="'+W+'" xmlns:r="'+R+'"><w:body>'+body+sect+'</w:body></w:document>'}
    extra = {'word/header1.xml': key+'Header', 'word/footer1.xml': key+'Footer', 'word/footnotes.xml': key+'Footnote', 'word/endnotes.xml': key+'Endnote'}
    for part, text in extra.items():
        if 'footnotes' in part or 'endnotes' in part:
            kind = 'footnote' if 'footnotes' in part else 'endnote'
            value = '<w:'+kind+'s xmlns:w="'+W+'"><w:'+kind+' w:id="-1" w:type="separator">'+p(key+'SeparatorExcluded')+'</w:'+kind+'><w:'+kind+' w:id="1">'+p(text)+'</w:'+kind+'></w:'+kind+'s>'
        else:
            tag = 'hdr' if 'header' in part else 'ftr'
            value = '<w:'+tag+' xmlns:w="'+W+'">'+p(text)+'</w:'+tag+'>'
        files[part] = value
    words = [title,before,*a[0],a[1][0],key+'Tall',key+'SecondB',key+'SecondD',key+'NestedA',key+'NestedB',insert,after,*extra.values()]
    # Every tuple is a source-defined visible anchor cell: row/column/text/spans.
    tables = [
        [(1,1,a[0][0],1,1),(1,2,a[0][1],1,1),(2,1,a[1][0],1,2)],
        [(1,1,key+'Tall',2,1),(1,2,key+'SecondB',1,1),(2,2,key+'SecondD',1,1)],
        [(1,1,key+'NestedA',1,1),(1,2,key+'NestedB',1,1)],
    ]
    table_paths = ['body/table[1]', 'body/table[2]', 'body/table[2]/row[2]/cell[2]/table[1]']
    body_paths = ['body/paragraph[1]', 'body/paragraph[2]',
                  'body/table[1]/row[1]/cell[1]/paragraph[1]', 'body/table[1]/row[1]/cell[2]/paragraph[1]',
                  'body/table[1]/row[2]/cell[1]/paragraph[1]',
                  'body/table[2]/row[1]/cell[1]/paragraph[1]', 'body/table[2]/row[1]/cell[2]/paragraph[1]',
                  'body/table[2]/row[2]/cell[2]/paragraph[1]',
                  'body/table[2]/row[2]/cell[2]/table[1]/row[1]/cell[1]/paragraph[1]',
                  'body/table[2]/row[2]/cell[2]/table[1]/row[1]/cell[2]/paragraph[1]',
                  'body/paragraph[3]', 'body/paragraph[4]']
    anchors = [{'text':word, 'part':'word/document.xml', 'path':path} for word,path in zip(words[:12],body_paths)]
    for (part,word),path in zip(extra.items(), ['header/paragraph[1]', 'footer/paragraph[1]', 'footnotes/note[1]/paragraph[1]', 'endnotes/note[1]/paragraph[1]']):
        anchors.append({'text':word,'part':part,'path':path})
    return package(files), {'key':key, 'words':words, 'parts':{'word/document.xml',*extra}, 'tables':tables, 'table_paths':table_paths, 'anchors':anchors, 'body_order':words[:12], 'excluded':[deleted,key+'SeparatorExcluded']}

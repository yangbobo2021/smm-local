"""Distinct legitimate blank originals, with no product-generated truth."""
from io import BytesIO
from document_formats_fixtures import package,W,R,REL,CT
from document_formats_table_fixture import workbook
from reportlab.pdfgen import canvas


def blank_original(format,key):
    if format=='docx':
        return package({'word/document.xml':'<w:document xmlns:w="'+W+'"><w:body><!--'+key+'--></w:body></w:document>',
            '_rels/.rels':'<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="word/document.xml"/></Relationships>',
            '[Content_Types].xml':'<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'})
    if format=='xlsx':
        raw,text=workbook([{'name':key,'cells':[]}]);assert text=='';return raw
    out=BytesIO();pdf=canvas.Canvas(out,pagesize=(400,300),invariant=1);pdf.setTitle(key);pdf.showPage();pdf.save();return out.getvalue()

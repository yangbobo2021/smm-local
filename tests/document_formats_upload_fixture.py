"""Original upload bytes and independent text/table truth; no SMM imports."""
from io import BytesIO
from zipfile import ZipFile,ZIP_STORED
from document_formats_fixtures import docx_fixture
from document_formats_pdf_fixture import native_pdf
from document_formats_table_fixture import workbook


def upload_input(format,key):
    if format=='docx':
        raw,source=docx_fixture(key)
        out=BytesIO()
        with ZipFile(BytesIO(raw)) as z,ZipFile(out,'w',ZIP_STORED) as target:
            for name in z.namelist():
                body=z.read(name)
                if name=='word/document.xml':body=body.replace(b'<w:body>',b'<w:body><!--'+b'x'*1100000+b'-->',1)
                target.writestr(name,body)
        raw=out.getvalue()
        tables=[{'rows':max(c[0]+c[3]-1 for c in cells),'columns':max(c[1]+c[4]-1 for c in cells),'cells':cells,'location':{'part':'word/document.xml','path':path}} for cells,path in zip(source['tables'],source['table_paths'])]
        return raw,{'words':source['words'],'excluded':source['excluded'],'tables':tables}
    if format=='xlsx':
        sheets=[{'name':key+'Sheet'+str(i),'cells':[{'row':r,'column':c,'text':key+'S'+str(i)+'R'+str(r)+'C'+str(c)} for r in range(1,4) for c in range(1,3)]} for i in (1,2)]
        raw,text=workbook(sheets)
        tables=[{'rows':3,'columns':2,'cells':[(c['row'],c['column'],c['text'],1,1) for c in sheet['cells']],'location':{'sheet':sheet['name'],'sheet_index':i}} for i,sheet in enumerate(sheets,1)]
        return raw,{'words':text.split('\n'),'excluded':[],'tables':tables}
    raw,source=native_pdf(key)
    tables=[{'rows':t['rows'],'columns':t['columns'],'cells':[(c['row'],c['column'],c['text'],1,1) for c in t['cells']],'location':{'page':page['page'],'method':'native'}} for page in source['pages'] for t in page['tables']]
    return raw,{'words':source['order'],'excluded':[],'tables':tables}

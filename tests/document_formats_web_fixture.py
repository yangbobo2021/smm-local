"""Independent originals and truth for actual browser document views."""
from html import escape
from io import BytesIO
from zipfile import ZipFile,ZIP_DEFLATED
from document_formats_table_fixture import deep_word,deep_xlsx,deep_pdf

TRAP='<img src="data:image/png;base64,AAAA" onerror="window.__smmDocumentExecuted=true">'


def replace_member(raw,member,old,new):
    output=BytesIO()
    with ZipFile(BytesIO(raw)) as source,ZipFile(output,'w',ZIP_DEFLATED) as target:
        changed=False
        for name in source.namelist():
            data=source.read(name)
            if name==member:
                assert data.count(old)==1;data=data.replace(old,new,1);changed=True
            target.writestr(name,data)
        assert changed
    return output.getvalue()


def web_original(format,key):
    raw,truth={'docx':deep_word,'xlsx':deep_xlsx,'pdf':deep_pdf}[format](key)
    if format=='docx':
        heading=key+' Word Ω😀'
        old=escape(heading).encode()
        new=(escape(heading)+'</w:t></w:r></w:p><w:p><w:r><w:t>'+escape(TRAP)).encode()
        raw=replace_member(raw,'word/document.xml',old,new)
        truth['text']=truth['text'].replace(heading,heading+'\n'+TRAP,1)
        old=key+'Overview1';new=old+' '+('甲😀'*8001)
        raw=replace_member(raw,'word/document.xml',escape(old).encode(),escape(new).encode())
        truth['text']=truth['text'].replace(old,new,1)
        truth['quota_table']={'location':{'part':'word/document.xml','path':'body/table[1]'},'rows':1,'columns':2,'cells':[{'row':1,'column':1,'text':new},{'row':1,'column':2,'text':key+'Overview2'}]}
    elif format=='xlsx':
        cell=next(c for c in truth['cells'] if (c['row'],c['column'])==(1,11));old=cell['text'];new=TRAP+' '+old
        raw=replace_member(raw,'xl/worksheets/sheet2.xml',escape(old).encode(),escape(new).encode())
        cell['text']=new;truth['text']=truth['text'].replace(old,new,1)
    return raw,truth


def source_key(owner,key,format):
    return {'docx':'w','xlsx':'x','pdf':'p'}[format]+owner[0]+key[0]

"""Regenerate synthetic Office object fixtures in a separate SDK environment.

python-docx==1.2.0 openpyxl==3.1.5 Pillow==13.0.0; never imported by SMM.
CI consumes committed files and the manifest, not these optional SDKs.
"""
import hashlib,json,posixpath,sys,zipfile
from datetime import datetime
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from docx import Document
from docx.shared import Inches
from openpyxl import Workbook,load_workbook
from openpyxl.drawing.image import Image as SpreadsheetImage
from PIL import Image,ImageDraw


def inspect(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=set(z.namelist());assert len(names)==len(z.namelist())
        drawing_parts=[];text=[];images=[]
        for name in sorted(names):
            raw=z.read(name)
            if name.endswith('.png'):
                with Image.open(BytesIO(raw)) as image:
                    image.load();assert image.format=='PNG' and image.size==(24,24)
                    assert len(set(image.convert('RGB').getdata()))>1
                images.append({'part':name,'sha256':hashlib.sha256(raw).hexdigest()})
            if not name.endswith(('.xml','.rels')):continue
            root=ET.fromstring(raw)
            if any(n.tag.endswith('}drawing') for n in root.iter()):drawing_parts.append(name)
            text.extend(n.text for n in root.iter() if n.tag.endswith('}t') and n.text)
            if name.endswith('.rels'):
                part='' if name=='_rels/.rels' else posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])
                for r in root:
                    assert r.get('TargetMode')!='External'
                    target=r.attrib['Target'];target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(part),target))
                    assert target in names,(name,target)
        return {'drawing_parts':drawing_parts,'supported_text_nodes':text,'images':images}


def generate(folder):
    folder.mkdir(parents=True,exist_ok=True);items=[]
    for project in ('ordinary','global'):
        for format,kinds in (('docx',('body','header','footer','blank','text')),('xlsx',('object','blank','text'))):
            for kind in kinds:
                key=project+kind+format;expected=key+' supported value' if kind=='text' else ''
                image=Image.new('RGB',(24,24),'white');draw=ImageDraw.Draw(image);color=tuple(hashlib.sha256(key.encode()).digest()[:3]);draw.rectangle((2,2,21,21),fill=color);draw.line((2,21,21,2),fill='black',width=2)
                out=BytesIO();image.save(out,format='PNG');picture=out.getvalue()
                path=folder/(key+'.'+format)
                if format=='docx':
                    doc=Document();doc.core_properties.identifier=key;doc.core_properties.title=key
                    if expected:doc.add_paragraph(expected)
                    if kind!='blank':
                        paragraph=(doc.sections[0].header.paragraphs[0] if kind=='header' else doc.sections[0].footer.paragraphs[0] if kind=='footer' else doc.add_paragraph())
                        paragraph.add_run().add_picture(BytesIO(picture),width=Inches(.7))
                    doc.save(path);again=Document(path)
                    assert '\n'.join(p.text for p in again.paragraphs if p.text)==expected
                    expected_part=('word/header1.xml' if kind=='header' else 'word/footer1.xml' if kind=='footer' else 'word/document.xml')
                else:
                    wb=Workbook();ws=wb.active;ws.title=key[:31];wb.properties.identifier=key;wb.properties.title=key
                    if expected:ws['A1']=expected
                    if kind!='blank':ws.add_image(SpreadsheetImage(BytesIO(picture)),'C3')
                    wb.save(path);again=load_workbook(path)
                    assert again.active['A1'].value==(expected or None)
                    expected_part='xl/worksheets/sheet1.xml'
                checked=inspect(path)
                assert checked['supported_text_nodes']==([expected] if expected else [])
                assert checked['drawing_parts']==([] if kind=='blank' else [expected_part]),checked
                assert len(checked['images'])==int(kind!='blank')
                raw=path.read_bytes();items.append({'file':path.name,'project':project,'format':format,'kind':kind,'text':expected,'expected_status':'empty-success' if kind=='blank' else 'ready' if kind=='text' else 'failed','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),**checked})
    assert len(items)==16 and len({i['sha256'] for i in items})==16
    manifest={'schema':1,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sdk_versions':{p:version(p) for p in ('python-docx','openpyxl','Pillow','lxml')},'sources':['https://pypi.org/project/python-docx/1.2.0/','https://pypi.org/project/openpyxl/3.1.5/','https://python-docx.readthedocs.io/en/latest/api/section.html','https://openpyxl.readthedocs.io/en/stable/images.html'],'scope':'Synthetic SDK-created OPC files; independent SDK reopen, all internal relationship targets, actual PNG content and text/drawing parts verified. No standalone image product support. Committed bytes remain fixed between CI runs.','items':items}
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(items),'bytes':sum(i['bytes'] for i in items),'sdk_versions':manifest['sdk_versions']}))

if __name__=='__main__':generate(Path(sys.argv[1]))

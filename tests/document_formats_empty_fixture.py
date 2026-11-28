"""Legal empty containers and visible image-only negative, without product code."""
from io import BytesIO
from PIL import Image,ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from document_formats_fixtures import package,W,R,REL,CT


def empty_office(format,key,sheets=1):
    props='<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>'+key+'</dc:title></cp:coreProperties>'
    if format=='docx':
        main='word/document.xml';main_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
        files={main:'<w:document xmlns:w="'+W+'"><w:body/></w:document>'};parts=[main]
    else:
        main='xl/workbook.xml';main_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'
        namespace='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        declarations=''.join('<sheet name="'+key+str(i)+'" sheetId="'+str(i)+'" state="'+('visible' if i==1 else 'hidden')+'" r:id="s'+str(i)+'"/>' for i in range(1,sheets+1))
        files={main:'<workbook xmlns="'+namespace+'" xmlns:r="'+R+'"><sheets>'+declarations+'</sheets></workbook>'};parts=[];relations=''
        for i in range(1,sheets+1):
            part='xl/worksheets/sheet'+str(i)+'.xml';parts.append(part)
            files[part]='<worksheet xmlns="'+namespace+'"><sheetData/></worksheet>'
            relations+='<Relationship Id="s'+str(i)+'" Type="'+R+'/worksheet" Target="worksheets/sheet'+str(i)+'.xml"/>'
        files['xl/_rels/workbook.xml.rels']='<Relationships xmlns="'+REL+'">'+relations+'</Relationships>'
    overrides='<Override PartName="/'+main+'" ContentType="'+main_type+'"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    if format=='xlsx':overrides+=''.join('<Override PartName="/'+part+'" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for part in parts)
    files['[Content_Types].xml']='<Types xmlns="'+CT+'"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+overrides+'</Types>'
    files['_rels/.rels']='<Relationships xmlns="'+REL+'"><Relationship Id="main" Type="'+R+'/officeDocument" Target="'+main+'"/><Relationship Id="props" Type="'+REL+'/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'
    files['docProps/core.xml']=props
    return package(files),{'format':format,'key':key,'parts':parts,'text':''}


def empty_pdf(key):
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(200,120),invariant=1);pdf.setTitle(key)
    for page in (1,2):pdf.showPage()
    pdf.save();return output.getvalue(),{'format':'pdf','key':key,'pages':[1,2],'width':200,'height':120,'text':''}


def image_only_pdf():
    image=Image.new('RGB',(500,160),'white');ImageDraw.Draw(image).text((20,60),'VISIBLE SCANNED BODY 81723',fill='black')
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(120,40),invariant=1)
    pdf.drawImage(ImageReader(image),0,0,width=120,height=40);pdf.showPage();pdf.save();return output.getvalue()

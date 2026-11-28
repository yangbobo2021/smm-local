"""Real component smoke, deliberately separate from 008 business acceptance."""
import argparse,hashlib,json,os,re,subprocess,sys
from io import BytesIO
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--materials',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from document_formats_prepare import probe
    from PIL import Image,ImageDraw,ImageFont
    from reportlab.pdfgen import canvas
    import pdfplumber,pypdfium2,psutil
    from defusedxml import ElementTree
    from defusedxml.common import DefusedXmlException
    a.work.mkdir(parents=True,exist_ok=True);m=json.loads(a.materials.read_text(encoding='utf-8'))
    truth='文档检索\nINVOICE 12345.67';image=Image.new('RGB',(1400,500),'white');draw=ImageDraw.Draw(image);font=ImageFont.truetype(m['font']['path'],68)
    for index,line in enumerate(truth.splitlines()):draw.text((80,60+index*160),line,font=font,fill='black')
    png=a.work/'component.png';image.save(png)
    command=[m['ocr_executable'],str(png),'stdout','--tessdata-dir',m['ocr_data_dir'],'-l','chi_sim+eng','--psm','3']
    run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=30)
    (a.work/'ocr.stdout').write_text(run.stdout,encoding='utf-8');(a.work/'ocr.stderr').write_text(run.stderr,encoding='utf-8')
    assert run.returncode==0 and re.sub(r'\s+','',run.stdout)==re.sub(r'\s+','',truth),(run.returncode,run.stdout,run.stderr)
    pdf=a.work/'component.pdf';cv=canvas.Canvas(str(pdf),pagesize=(300,200),invariant=1)
    for number in (1,2):cv.drawString(30,100,'COMPONENT PAGE '+str(number));cv.showPage()
    cv.save()
    with pdfplumber.open(pdf) as document:assert len(document.pages)==2 and [page.extract_text() for page in document.pages]==['COMPONENT PAGE 1','COMPONENT PAGE 2']
    with pypdfium2.PdfDocument(pdf) as document:
        assert len(document)==2
        bitmap=document[1].render(scale=1);bitmap.to_pil().save(a.work/'render.png');bitmap.close()
    rejected=False
    try:ElementTree.fromstring('<!DOCTYPE a [<!ENTITY e "ENTITY">]><a>&e;</a>',forbid_dtd=True)
    except DefusedXmlException:rejected=True
    assert rejected and psutil.Process().memory_info().rss>0
    result={**probe(),'purpose':'components only; not DOCX/XLSX/PDF/OCR SMM acceptance','ocr_command':command,'ocr_stdout':run.stdout,'expected':truth,'font_sha256':hashlib.sha256(Path(m['font']['path']).read_bytes()).hexdigest(),'files':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in a.work.iterdir() if path.is_file()}}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'component_probe':'passed','output':str(a.output)}))

if __name__=='__main__':main()

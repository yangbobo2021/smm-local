"""Independent two-page input: native page plus OCR page beyond bitmap quota."""
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def partial_pdf(key,font):
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(300,200),invariant=1)
    anchor=key+' PartialSnapshot';pdf.drawString(30,100,anchor);pdf.showPage()
    pdf.setPageSize((2000,1000));image=Image.new('RGB',(600,200),'white');draw=ImageDraw.Draw(image)
    draw.text((25,65),key+' UNPROCESSED',font=ImageFont.truetype(str(font),32),fill='black')
    pdf.drawImage(ImageReader(image),0,0,width=2000,height=1000);pdf.showPage();pdf.save()
    return output.getvalue(),{'anchor':anchor,'page_count':2,'published_status':'partial','known_failure':{'page':2,'reason_contains':'1600万像素'},'native_page':1}

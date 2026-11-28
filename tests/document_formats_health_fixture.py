"""Independent partial PDF: available native table and unavailable scan page."""
from io import BytesIO
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def partial_with_table(key):
    stream=BytesIO();pdf=canvas.Canvas(stream,pagesize=(300,240),invariant=1)
    anchor=key+' PartialTable';pdf.setFont('Helvetica',10);pdf.drawString(20,210,anchor)
    left,bottom,width,height=20,100,130,30;cells=[]
    for row in range(3):pdf.line(left,bottom+row*height,left+2*width,bottom+row*height)
    for column in range(3):pdf.line(left+column*width,bottom,left+column*width,bottom+2*height)
    words=[anchor]
    for row in (1,2):
        for column in (1,2):
            text=key+'R'+str(row)+'C'+str(column);words.append(text)
            pdf.drawString(left+(column-1)*width+5,bottom+(2-row)*height+10,text)
            cells.append((row,column,text,1,1))
    pdf.showPage();pdf.drawImage(ImageReader(Image.new('RGB',(1,1),'black')),0,0,width=300,height=240)
    pdf.showPage();pdf.save()
    return stream.getvalue(),{'words':words,'excluded':[],'tables':[
        {'rows':2,'columns':2,'cells':cells,'location':{'page':1,'method':'native'}}]}

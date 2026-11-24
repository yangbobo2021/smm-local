"""Deterministic native PDFs; values, order and display geometry precede parsing."""
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

WIDTH,HEIGHT=612,792


def native_pdf(key):
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    buffer=BytesIO();c=canvas.Canvas(buffer,pagesize=(WIDTH,HEIGHT),invariant=1,pageCompression=1)
    pages=[];order=[]
    for page in (1,2):
        rotation=([0,90] if key!='nativebeta' else [180,270])[page-1]
        width,height=(792,612) if rotation in (90,270) else (WIDTH,HEIGHT)
        c.setPageSize((width,height));c.setPageRotation(rotation)
        # Counter-rotate the content so each strong grid remains horizontal in
        # the PDF's displayed orientation. Raw /Rotate is deliberately nonzero.
        if rotation==90:c.translate(height,0);c.rotate(90)
        elif rotation==270:c.translate(0,width);c.rotate(-90)
        elif rotation==180:c.translate(width,height);c.rotate(180)
        heading=key+' NativePage'+str(page)
        unicode_line='原生文档检索 '+key+' 第'+str(page)+'页'
        c.setFont('Helvetica',14);c.drawString(72,height-62,heading)
        c.setFont('STSong-Light',14);c.drawString(72,height-100,unicode_line)
        order.extend([heading,unicode_line])
        tables=[]
        for table_number,bottom in enumerate(([height-392] if page==1 else [height-392,height-560]),1):
            left,cellw,cellh=72,210,32;rows,columns=3,2;cells=[]
            c.setLineWidth(0.5)
            for row in range(rows+1):c.line(left,bottom+row*cellh,left+columns*cellw,bottom+row*cellh)
            for col in range(columns+1):c.line(left+col*cellw,bottom,left+col*cellw,bottom+rows*cellh)
            c.setFont('Helvetica',11)
            for row in range(1,rows+1):
                for col in range(1,columns+1):
                    text=key+'P'+str(page)+'T'+str(table_number)+'R'+str(row)+'C'+str(col)
                    x=left+(col-1)*cellw;y=bottom+(rows-row)*cellh
                    c.drawString(x+6,y+11,text)
                    box=[x/width,(height-y-cellh)/height,(x+cellw)/width,(height-y)/height]
                    cells.append({'row':row,'column':col,'text':text,'bbox':box});order.append(text)
            table_box=[left/width,(height-bottom-rows*cellh)/height,(left+columns*cellw)/width,(height-bottom)/height]
            tables.append({'page':page,'rows':rows,'columns':columns,'cells':cells,'bbox':table_box})
        paragraphs=[{'text':heading,'top_min':40,'top_max':80},{'text':unicode_line,'top_min':80,'top_max':120}]
        pages.append({'page':page,'heading':heading,'paragraphs':paragraphs,'rows':rows,'columns':columns,'cells':[cell for table in tables for cell in table['cells']],'tables':tables,'bbox':tables[0]['bbox'],'width':width,'height':height,'rotation':rotation})
        c.showPage()
    c.save();return buffer.getvalue(),{'key':key,'pages':pages,'order':order}

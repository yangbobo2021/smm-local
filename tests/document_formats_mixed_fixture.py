"""Two mixed raster/native pages and a purely native page, independent truth."""
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def mixed_pdf(key,font_path):
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(240,216),invariant=1);pages=[];order=[]
    for page in (1,2):
        image=Image.new('RGB',(1000,900),'white');draw=ImageDraw.Draw(image);font=ImageFont.truetype(str(font_path),48)
        title=key.upper()+' SCAN PAGE'+str(page);paragraph='扫描正文 中文英文'
        draw.text((100,140),title,font=font,fill='black');draw.text((100,220),paragraph,font=font,fill='black')
        ink_boxes=[[v/1000 if i%2==0 else v/900 for i,v in enumerate(draw.textbbox(point,text,font=font))] for point,text in [((100,140),title),((100,220),paragraph)]]
        tables=[]
        for number,ys in enumerate(([350,460,570,680],) if page==1 else ([350,460,570],[650,760,870]),1):
            xs=[100,600,900];rows=[['项目编号','关键金额'],['文档检索',str((10000 if key=='mixedalpha' else 20000)+page*10+number)+'.67']]
            if len(ys)==4:rows.append(['归档内容','3456.78' if key=='mixedalpha' else '8765.43'])
            for y in ys:draw.line((xs[0],y,xs[-1],y),fill='black',width=3)
            for x in xs:draw.line((x,ys[0],x,ys[-1]),fill='black',width=3)
            cells=[]
            for r,row in enumerate(rows):
                for c,text in enumerate(row):
                    draw.text((xs[c]+25,ys[r]+25),text,font=font,fill='black')
                    cells.append({'row':r+1,'column':c+1,'text':text,'bbox':[xs[c]/1000,ys[r]/900,xs[c+1]/1000,ys[r+1]/900]})
            tables.append({'rows':len(rows),'columns':2,'bbox':[xs[0]/1000,ys[0]/900,xs[-1]/1000,ys[-1]/900],'cells':cells})
        pdf.drawImage(ImageReader(image),0,0,width=240,height=216)
        heading=key.upper()+' NATIVEHEADER'+str(page);pdf.setFont('Helvetica',10);pdf.drawString(24,203,heading)
        pdf.showPage();order.extend([heading,title,paragraph,*[c['text'] for table in tables for c in table['cells']]])
        pages.append({'page':page,'width':240,'height':216,'heading':heading,'heading_bbox':[.09,0,.95,.12],'ink_boxes':ink_boxes,'title':title,'paragraph':paragraph,'tables':tables})
    heading=key.upper()+' NATIVEHEADER3';pdf.setFont('Helvetica',12);pdf.drawString(24,180,heading);pdf.showPage();order.append(heading)
    pages.append({'page':3,'width':240,'height':216,'heading':heading,'heading_bbox':[.09,.08,.95,.25],'tables':[]})
    pdf.save();return output.getvalue(),{'key':key,'pages':pages,'order':order,'text':'\n'.join(order)}

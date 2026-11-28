"""Independent scanned PDF material and source-coordinate truth."""
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def scanned_fixture(font_path,key):
    offset=0 if key=='alpha' else 100
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(240,216),invariant=1,pageCompression=1);pages=[]
    for page_number in (1,2):
        image=Image.new('RGB',(1000,900),'white');draw=ImageDraw.Draw(image);font=ImageFont.truetype(str(font_path),48)
        title=key.upper()+' PAGE '+str(page_number)
        rows=[['项目编号','关键金额'],['文档检索' if page_number==1 else '历史归档',str((12345 if key=='alpha' else 76543)+page_number)+'.67'],['中文英文',''+str(3400+offset+page_number)+'.50']]
        draw.text((100,55),title,font=font,fill='black')
        draw.text((100,125),'扫描资料 验收材料',font=font,fill='black')
        xs=[100,600,900];ys=[260,390,520,650]
        for y in ys:draw.line([(xs[0],y),(xs[-1],y)],fill='black',width=3)
        for x in xs:draw.line([(x,ys[0]),(x,ys[-1])],fill='black',width=3)
        for r,row in enumerate(rows):
            for c,text in enumerate(row):draw.text((xs[c]+25,ys[r]+25),text,font=font,fill='black')
        pdf.drawImage(ImageReader(image),0,0,width=240,height=216);pdf.showPage()
        cells=[{'row':r+1,'column':c+1,'text':text,'bbox':[xs[c]/1000,ys[r]/900,xs[c+1]/1000,ys[r+1]/900]} for r,row in enumerate(rows) for c,text in enumerate(row)]
        pages.append({'page':page_number,'title':title,'paragraph':'扫描资料 验收材料','title_region':[.1,55/900,.9,120/900],'paragraph_region':[.1,125/900,.9,190/900],'rows':rows,'cells':cells,'bbox':[.1,260/900,.9,650/900]})
    pdf.save()
    return output.getvalue(),{'key':key,'pages':pages,'text':'\n'.join(s for p in pages for s in [p['title'],p['paragraph'],*[c['text'] for c in p['cells']]])}

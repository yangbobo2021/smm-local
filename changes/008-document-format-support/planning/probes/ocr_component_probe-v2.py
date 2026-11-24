import csv, hashlib, io, json, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
import pdfplumber, pypdfium2
root,exe,data,font=map(Path,sys.argv[1:5]); out=root/'ocr-research-v2';out.mkdir(exist_ok=True)
def clusters(xs):
 g=[]
 for x in xs:
  if not g or x>g[-1][-1]+1:g.append([x])
  else:g[-1].append(x)
 return [sum(v)//len(v) for v in g]
def dist(a,b):
 d=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  q=[i]
  for j,y in enumerate(b,1):q.append(min(q[-1]+1,d[j]+1,d[j-1]+(x!=y)))
  d=q
 return d[-1]
results=[]
for number,rows,size in [(1,[['项目','金额'],['文档检索','731.25'],['本地解析','842.50']],48),(2,[['项目','金额'],['会话同步','912.75'],['资料归档','624.30']],52)]:
 im=Image.new('RGB',(1000,800),'white');dr=ImageDraw.Draw(im);f=ImageFont.truetype(str(font),size)
 for y in [200,320,440,560]:dr.line([(100,y),(900,y)],fill='black',width=3)
 for x in [100,600,900]:dr.line([(x,200),(x,560)],fill='black',width=3)
 for r,row in enumerate(rows):
  for c,text in enumerate(row):dr.text(([125,625][c],220+r*120),text,font=f,fill='black')
 png=out/f'scan-{number}.png';im.save(png);pdf=out/f'scan-{number}.pdf'
 cv=canvas.Canvas(str(pdf),pagesize=(240,192));cv.drawImage(str(png),0,0,width=240,height=192);cv.save()
 with pdfplumber.open(pdf) as pd:assert not (pd.pages[0].extract_text() or '').strip()
 with pypdfium2.PdfDocument(pdf) as pd:bitmap=pd[0].render(scale=300/72);page=bitmap.to_pil().convert('RGB');bitmap.close()
 gray=page.convert('L');width,height=gray.size;pixels=gray.tobytes()
 ys=clusters([y for y in range(height) if sum(v<128 for v in pixels[y*width:(y+1)*width])>=width*.7])
 assert len(ys)==4,ys
 xs=clusters([x for x in range(width) if sum(pixels[y*width+x]<128 for y in range(ys[0],ys[-1]+1))>=(ys[-1]-ys[0])*.85])
 assert len(xs)==3,xs
 clean=page.copy();cd=ImageDraw.Draw(clean)
 for y in ys:cd.rectangle((xs[0]-3,y-3,xs[-1]+3,y+3),fill='white')
 for x in xs:cd.rectangle((x-3,ys[0]-3,x+3,ys[-1]+3),fill='white')
 crop=clean.crop((xs[0],ys[0],xs[-1]+1,ys[-1]+1));imagefile=out/f'layout-{number}.png';crop.save(imagefile)
 command=[str(exe),str(imagefile),'stdout','--tessdata-dir',str(data),'-l','eng+chi_sim','--oem','1','--psm','6','-c','tessedit_create_tsv=1']
 run=subprocess.run(command,capture_output=True,timeout=30);assert run.returncode==0,run.stderr.decode('utf8','replace')
 (out/f'ocr-{number}.tsv').write_bytes(run.stdout)
 cells=[['',''] for _ in range(3)]
 for word in csv.DictReader(io.StringIO(run.stdout.decode('utf8')),delimiter='\t'):
  if not word.get('text','').strip():continue
  x=int(word['left'])+int(word['width'])/2+xs[0];y=int(word['top'])+int(word['height'])/2+ys[0]
  rr=next((k for k in range(3) if ys[k]<y<ys[k+1]),None);cc=next((k for k in range(2) if xs[k]<x<xs[k+1]),None)
  if rr is not None and cc is not None:cells[rr][cc]+=word['text']
 expected=''.join(''.join(row) for row in rows);actual=re.sub(r'\s+','',''.join(''.join(row) for row in cells));cer=dist(expected,actual)/len(expected)
 results.append({'sample':number,'grid':[3,2],'expected':rows,'actual':cells,'cer':cer,'cells_exact':cells==rows,'native_text_empty':True,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()})
value={'purpose':'OCR and grid component feasibility, not SMM acceptance','tesseract_version':subprocess.check_output([str(exe),'--version']).decode('utf8').splitlines()[0],'languages':'eng+chi_sim','samples':results,'passed':all(x['cells_exact'] and x['cer']<=.01 for x in results),'font_sha256':hashlib.sha256(font.read_bytes()).hexdigest()}
(out/'result.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(value,ensure_ascii=False))

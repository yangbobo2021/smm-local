"""Worker-only local OCR and explicit raster grid layout; no network/downloads."""
from __future__ import annotations
import csv,io,math,re,subprocess,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops

PIXELS=16000000


class PageFailure(ValueError):pass


def binary_threshold(image):
    """Choose a bounded grayscale split from the actual page's ink/background."""
    histogram=image.histogram();total=sum(histogram)
    intensity=sum(level*count for level,count in enumerate(histogram))
    weight=0;partial=0;best=-1;threshold=127
    for level,count in enumerate(histogram):
        weight+=count;partial+=level*count
        if not weight or weight==total:continue
        score=(partial*total-intensity*weight)**2/(weight*(total-weight))
        if score>best:best=score;threshold=level
    return threshold


def clusters(values,tolerance=3):
    groups=[]
    for value in values:
        if not groups or value-groups[-1][-1]>tolerance:groups.append([value])
        else:groups[-1].append(value)
    return [round(sum(g)/len(g)) for g in groups]


def grids(image):
    gray=image.convert('L');width,height=gray.size;data=gray.tobytes();minimum=max(40,width//8);segments=[]
    for y in range(height):
        row=data[y*width:(y+1)*width];start=None
        for x,value in enumerate(row):
            if value<128:
                if start is None:start=x
            elif start is not None:
                if x-start>=minimum:segments.append((y,start,x-1))
                start=None
        if start is not None and width-start>=minimum:segments.append((y,start,width-1))
    groups=[]
    for y,left,right in segments:
        group=next((g for g in groups if abs(g['left']-left)<=4 and abs(g['right']-right)<=4),None)
        if group is None:group={'left':left,'right':right,'ys':[]};groups.append(group)
        group['ys'].append(y)
    tables=[]
    for group in groups:
        ys=clusters(group['ys']);left,right=group['left'],group['right']
        # Equal-width tables can occur above one another. A whitespace gap
        # lacks continuous outer borders and must split the connected grids.
        components=[];current=[]
        def vertical(x,top,bottom):
            return sum(data[y*width+x]<128 for y in range(top,bottom+1))>=(bottom-top+1)*.90
        for y in ys:
            if current:
                top=current[-1]
                connected=all(any(vertical(x,top,y) for x in range(max(0,border-3),min(width,border+4))) for border in (left,right))
                if not connected:components.append(current);current=[]
            current.append(y)
        if current:components.append(current)
        for rows in components:
            if len(rows)<2:continue
            top,bottom=rows[0],rows[-1]
            if bottom-top<30:continue
            xs=clusters([x for x in range(max(0,left-3),min(width,right+4)) if vertical(x,top,bottom)])
            if len(xs)<3 or abs(xs[0]-left)>4 or abs(xs[-1]-right)>4:continue
            # Every admitted boundary is uninterrupted across this component;
            # partial/merged grids are not converted into guessed columns.
            if any(sum(data[y*width+x]<128 for x in range(xs[0],xs[-1]+1))<(xs[-1]-xs[0]+1)*.95 for y in rows):continue
            rect=(xs[0],rows[0],xs[-1],rows[-1])
            if any(abs(rect[0]-t['box'][0])<5 and abs(rect[1]-t['box'][1])<5 for t in tables):continue
            tables.append({'xs':xs,'ys':rows,'box':rect})
    return sorted(tables,key=lambda t:(t['box'][1],t['box'][0]))


def text(words):
    value='';previous=None
    for word in sorted(words,key=lambda w:(w['line'],w['left'])):
        current=word['text']
        if value and previous:
            if word['line']!=previous['line']:value+='\n'
            elif re.search(r'[A-Za-z0-9]$',value) and re.match(r'[A-Za-z0-9]',current):value+=' '
        value+=current;previous=word
    return value


def rect(words):return [min(w['left'] for w in words),min(w['top'] for w in words),max(w['left']+w['width'] for w in words),max(w['top']+w['height'] for w in words)]


def contains(rectangle,x,y):return rectangle[0]<=x<=rectangle[2] and rectangle[1]<=y<=rectangle[3]


def component_profile(config):
    from ..document_processing import Configuration
    probe=config.get('probe',{})
    if not probe.get('ready'):raise PageFailure('未取得当前配置的有效组件探测，请明确processing-status --check')
    try:executable=Configuration._file_hash(config['ocr_executable'])
    except (OSError,ValueError) as exc:raise PageFailure('OCR程序不可读取: '+str(exc)) from exc
    expected=probe.get('component',{}).get('executable')
    if executable!=expected:raise PageFailure('OCR程序自探测后发生变化，请重新配置/检查')
    try:languages={name:Configuration._file_hash(Path(config['ocr_data_dir'])/(name+'.traineddata')) for name in config['languages'].split('+')}
    except (OSError,ValueError) as exc:raise PageFailure('OCR语言不可读取: '+str(exc)) from exc
    if languages!=probe.get('language_data'):raise PageFailure('OCR语言数据自探测后变化，请重新配置/检查')
    return {'executable':executable,'version':probe['component']['version'],'language_data':languages,'languages':config['languages'],'pipeline':'grid3-body11-otsu-connected-v3'}


def page_events(document,number,page,config,*,native_boxes=(),regions=None):
    started=time.monotonic();deadline=started+30
    if not all(config.get(k) for k in ('ocr_executable','ocr_data_dir','languages')):raise PageFailure('缺少本地OCR配置或语言')
    engine=Path(config['ocr_executable']);data=Path(config['ocr_data_dir'])
    if not engine.is_absolute() or not data.is_absolute():raise PageFailure('OCR配置须为绝对路径')
    if not {'eng','chi_sim'}.issubset(config['languages'].split('+')):raise PageFailure('OCR配置缺少eng/chi_sim')
    for language in config['languages'].split('+'):
        path=data/(language+'.traineddata')
        if not path.is_file():raise PageFailure('OCR语言缺失: '+language)
    import pypdfium2
    with pypdfium2.PdfDocument(document) as pdf:
        rendered=pdf[number-1];width,height=rendered.get_size();scale=300/72
        if not math.isfinite(width*height) or math.ceil(width*scale)*math.ceil(height*scale)>PIXELS:raise PageFailure('OCR页面位图超过1600万像素')
        bitmap=rendered.render(scale=scale,may_draw_forms=False)
        try:image=bitmap.to_pil().convert('RGB')
        finally:bitmap.close();rendered.close()
    width,height=image.size
    if width*height>PIXELS:raise PageFailure('OCR页面位图超过1600万像素')
    tables=grids(image);clean=image.copy();draw=ImageDraw.Draw(clean)
    def pixel(rectangle):return [rectangle[0]*width,rectangle[1]*height,rectangle[2]*width,rectangle[3]*height]
    # Areas with usable native content are white before OCR; they cannot be
    # emitted a second time, including native tables beneath image overlays.
    for rectangle in native_boxes:draw.rectangle(pixel(rectangle),fill='white')
    allowed=regions or [[0,0,1,1]]
    mask=Image.new('RGB',image.size,'white')
    for rectangle in allowed:
        bounds=tuple(max(0,min(width if i%2==0 else height,round(v))) for i,v in enumerate(pixel(rectangle)))
        if bounds[2]>bounds[0] and bounds[3]>bounds[1]:mask.paste(clean.crop(bounds),bounds[:2])
    clean=mask;draw=ImageDraw.Draw(clean)
    for table in tables:
        xs,ys=table['xs'],table['ys']
        for y in ys:draw.rectangle((xs[0]-3,y-3,xs[-1]+3,y+3),fill='white')
        for x in xs:draw.rectangle((x-3,ys[0]-3,x+3,ys[-1]+3),fill='white')
    clean=clean.convert('L');threshold=binary_threshold(clean)
    clean=clean.point(lambda value:255 if value>threshold else 0)
    # Grid cells share one OCR pass per complete table. Body text uses a
    # separate remaining-ink block; no per-cell processes or guessed columns.
    crops=[];outside=clean.copy();outside_draw=ImageDraw.Draw(outside)
    for table in tables:
        x0,y0,x1,y1=table['box'];bounds=(max(0,x0-4),max(0,y0-4),min(width,x1+5),min(height,y1+5))
        crops.append(bounds);outside_draw.rectangle((x0-4,y0-4,x1+4,y1+4),fill=255)
    if body_box:=ImageChops.invert(outside).getbbox():
        crops.append((max(0,body_box[0]-8),max(0,body_box[1]-8),min(width,body_box[2]+8),min(height,body_box[3]+8)))
    words=[]
    for crop_number,bounds in enumerate(crops):
        source=clean if crop_number<len(tables) else outside
        imagefile=Path.cwd()/('ocr-page-'+str(number)+'-region-'+str(crop_number)+'.png');source.crop(bounds).save(imagefile,dpi=(300,300))
        remaining=deadline-time.monotonic()
        if remaining<=0:raise PageFailure('OCR单页布局/渲染超过30秒')
        mode='3' if crop_number<len(tables) else '11'
        command=[str(engine),str(imagefile),'stdout','--tessdata-dir',str(data),'-l',config['languages'],'--oem','1','--psm',mode,'-c','tessedit_create_tsv=1']
        try:
            run=subprocess.run(command,capture_output=True,timeout=remaining)
            if run.returncode:raise PageFailure('OCR进程失败: '+run.stderr.decode('utf-8','replace')[-1000:])
            response=run.stdout.decode('utf-8')
        except subprocess.TimeoutExpired as exc:raise PageFailure('OCR单页超过30秒') from exc
        except OSError as exc:raise PageFailure('OCR执行失败: '+str(exc)) from exc
        finally:imagefile.unlink(missing_ok=True)
        for item in csv.DictReader(io.StringIO(response),delimiter='\t'):
            if item.get('level')!='5' or not item.get('text','').strip():continue
            word={'text':item['text'],'left':int(item['left'])+bounds[0],'top':int(item['top'])+bounds[1],'width':int(item['width']),'height':int(item['height']),'confidence':float(item['conf']),'line':(crop_number,*(int(item[k]) for k in ('block_num','par_num','line_num')))}
            if word['width']<0 or word['height']<0 or not 0<=word['confidence']<=100:raise PageFailure('OCR词框或置信无效')
            cx=(word['left']+word['width']/2)/width;cy=(word['top']+word['height']/2)/height
            if not any(contains(r,cx,cy) for r in allowed) or any(contains(r,cx,cy) for r in native_boxes):continue
            words.append(word)
    if not words:raise PageFailure('OCR未识别出可用文字，不能冒称空白成功')
    def normalized(rectangle):return [rectangle[0]/width,rectangle[1]/height,rectangle[2]/width,rectangle[3]/height]
    def location(rectangle,items):return {'page':number,'page_width':page.width,'page_height':page.height,'rotation':page.rotation,'method':'ocr','bbox':normalized(rectangle),'confidence':sum(w['confidence'] for w in items)/len(items) if items else None}
    events=[];used=set()
    for table in tables:
        xs,ys=table['xs'],table['ys'];cells=[]
        for r in range(len(ys)-1):
            for c in range(len(xs)-1):
                bounds=(xs[c],ys[r],xs[c+1],ys[r+1]);selected=[]
                for index,word in enumerate(words):
                    if contains(bounds,word['left']+word['width']/2,word['top']+word['height']/2):selected.append(word);used.add(index)
                value=text(selected)
                cells.append({'row':r+1,'column':c+1,'text':value,'type':'string' if selected else 'empty','row_span':1,'column_span':1,'location':location(bounds,selected)})
        if any(cell['text'] for cell in cells):events.append((table['box'][1]/height,table['box'][0]/width,'ocr-table',{'rows':len(ys)-1,'columns':len(xs)-1,'location':location(table['box'],words),'cells':cells},None))
    lines={}
    for index,word in enumerate(words):
        if index not in used:lines.setdefault(word['line'],[]).append(word)
    for items in lines.values():
        value=text(items);bounds=rect(items)
        events.append((bounds[1]/height,bounds[0]/width,'ocr-text',{'text':value,'location':location(bounds,items)},None))
    return events,{'page':number,'method':'ocr','status':'ready','regions':allowed,'languages':config['languages'],'preprocessing':{'threshold':threshold,'binarization':'between-class-variance','grid_lines_removed':True,'table_psm':3,'body_psm':11,'dpi_target':300},'warning':'识别文字，可能有误；质量承诺为清晰水平简体中文/英文印刷文字','elapsed_seconds':time.monotonic()-started}

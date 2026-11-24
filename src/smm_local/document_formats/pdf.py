"""Creator-side PDF text and explicit grids over a guarded private PDF."""
from __future__ import annotations
from pathlib import Path
import tempfile
import pdfplumber
from ..document_results import Builder
from .pdf_guard import intermediate


def box(value,page):
    x0,top,x1,bottom=value;left,ybase,_,_=page.bbox
    result=[(x0-left)/page.width,(top-ybase)/page.height,(x1-left)/page.width,(bottom-ybase)/page.height]
    if any(x < -0.00001 or x > 1.00001 for x in result):raise ValueError('PDF定位越过显示页面')
    return [max(0.0,min(1.0,float(v))) for v in result]


def inside(char,rect):
    x=(char['x0']+char['x1'])/2;y=(char['top']+char['bottom'])/2
    return rect[0]<=x<=rect[2] and rect[1]<=y<=rect[3]


def grid(table):
    rows=table.rows
    if not rows:return None
    columns=len(rows[0].cells)
    if not columns or any(len(row.cells)!=columns or any(cell is None for cell in row.cells) for row in rows):return None
    xs=sorted({x for row in rows for cell in row.cells for x in (cell[0],cell[2])});ys=sorted({y for row in rows for cell in row.cells for y in (cell[1],cell[3])})
    if len(xs)!=columns+1 or len(ys)!=len(rows)+1:return None
    for ri,row in enumerate(rows):
        for ci,cell in enumerate(row.cells):
            if any(abs(a-b)>0.01 for a,b in zip(cell,(xs[ci],ys[ri],xs[ci+1],ys[ri+1]))):return None
    values=table.extract()
    if len(values)!=len(rows) or any(len(row)!=columns or any(value is None for value in row) for row in values):return None
    return values


def parse(raw,raw_sha,profile,*,config=None):
    builder=Builder('pdf',raw_sha,{**profile,'pdf_pipeline':'guarded-native-local-ocr-v1'});partial=False;unsupported=False;ocr_pages=0
    # Worker cwd is its private, supervised task directory, never a source path.
    with tempfile.TemporaryDirectory(prefix='pdf-',dir=Path.cwd()) as directory:
        decoded=Path(directory)/'decoded.pdf';budget=intermediate(raw,decoded)
        with pdfplumber.open(decoded) as pdf:
            for number,original in enumerate(pdf.pages,1):
                page=original
                if original.cropbox!=original.bbox:page=original.crop(original.cropbox,strict=False)
                base={'page':number,'page_width':page.width,'page_height':page.height,'rotation':original.rotation,'method':'native'}
                chars=page.chars
                unreliable=any('(cid:' in str(char.get('text','')) or '\ufffd' in str(char.get('text','')) for char in chars)
                need_ocr=bool(page.images) or unreliable or (not chars and bool(page.curves))
                ready=[];events=[]
                for found in page.find_tables():
                    values=grid(found)
                    if values is None:
                        partial=True;unsupported=True;builder.coverage['units'].append({**base,'kind':'table','bbox':box(found.bbox,page),'status':'unsupported','reason':'表格不在完整单页矩形网格范围'})
                    else:
                        ready.append(found);events.append((found.bbox[1],found.bbox[0],'table',found,values))
                outside=page.filter(lambda item:item.get('object_type')!='char' or not any(inside(item,t.bbox) for t in ready))
                for line in outside.extract_text_lines(strip=True,return_chars=True):
                    if not line['text'].strip():continue
                    if '(cid:' in line['text'] or '\ufffd' in line['text']:continue
                    events.append((line['top'],line['x0'],'text',line,None))
                if need_ocr:
                    from .ocr import page_events,PageFailure,component_profile
                    ocr_pages+=1
                    try:
                        if 'ocr' not in builder.profile:builder.profile['ocr']=component_profile(config or {})
                        if ocr_pages>50:raise PageFailure('PDF超过50个需OCR页')
                        native_boxes=[box(t.bbox,page) for t in ready]
                        native_boxes.extend(box((v['x0'],v['top'],v['x1'],v['bottom']),page) for _,__,kind,v,___ in events if kind=='text')
                        regions=[box((image['x0'],image['top'],image['x1'],image['bottom']),page) for image in page.images] if page.images else None
                        recognized,unit=page_events(decoded,number,page,config or {},native_boxes=native_boxes,regions=regions)
                        events.extend((y*page.height+page.bbox[1],x*page.width+page.bbox[0],kind,value,values) for y,x,kind,value,values in recognized)
                        builder.coverage['units'].append(unit)
                    except PageFailure as exc:
                        partial=True;builder.coverage['errors'].append({'page':number,'method':'ocr','reason':str(exc),'region':'uncovered'})
                        builder.coverage['units'].append({**base,'method':'ocr','status':'failed','reason':str(exc)})
                else:builder.coverage['units'].append({**base,'status':'ready' if chars or ready else 'empty'})
                for _,__,kind,value,values in sorted(events,key=lambda event:(event[0],event[1])):
                    if kind=='ocr-text':builder.add(value['text'],value['location'])
                    elif kind=='ocr-table':
                        table=builder.table(value['location'],value['rows'],value['columns'])
                        for cell in value['cells']:
                            location=builder.add(cell['text'],cell['location']) or cell['location']
                            table['cells'].append({**cell,'location':location})
                    elif kind=='text':builder.add(value['text'],{**base,'bbox':box((value['x0'],value['top'],value['x1'],value['bottom']),page)})
                    else:
                        table=builder.table({**base,'bbox':box(value.bbox,page)},len(values),len(values[0]))
                        for ri,row in enumerate(values,1):
                            for ci,text in enumerate(row,1):
                                location={**base,'bbox':box(value.rows[ri-1].cells[ci-1],page)}
                                span=builder.add(text,location)
                                table['cells'].append({'row':ri,'column':ci,'text':text,'type':'string','row_span':1,'column_span':1,'location':span or location})
                if page.images:builder.coverage['excluded'].append('image_semantics')
                original.close()
        builder.coverage['decoded_bytes']=budget['decoded_bytes']
    if partial and not builder.fragments:raise ValueError('PDF没有可用支持内容；'+str(builder.coverage['errors']))
    return builder.finish('partial' if partial else None)

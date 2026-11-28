"""Pure, bounded processed-document values; no parser/OCR or optional imports."""
from __future__ import annotations
import hashlib
import json
import math

MIB=1024*1024
TEXT_LIMIT=8*MIB
RESULT_LIMIT=16*MIB
SCHEMA='processed_documents_v1'


def encode(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def sha(raw):return hashlib.sha256(raw).hexdigest()


class Builder:
    def __init__(self,format,raw_sha,profile):
        self.format=format;self.raw_sha=raw_sha;self.profile=profile
        self.fragments=[];self.length=0;self.text_bytes=0;self.locations=[];self.tables=[]
        self.coverage={'excluded':[],'revisions_present':False,'units':[],'errors':[]}
    def add(self,text,location):
        if '\0' in text:raise ValueError('提取文字包含NUL')
        text=text.replace('\r\n','\n').replace('\r','\n')
        if not text:return None
        if self.fragments:self.fragments.append('\n');self.length+=1;self.text_bytes+=1
        start=self.length;self.fragments.append(text);self.length+=len(text);self.text_bytes+=len(text.encode('utf-8'))
        if self.text_bytes>TEXT_LIMIT:raise ValueError('规范提取文本超过8MiB')
        loc={**location,'start':start,'end':self.length};self.locations.append(loc);return loc
    def table(self,location,rows,columns,*,header_rows=(),**metadata):
        ident=sha(encode([self.raw_sha,location]))[:32]
        table={'table_id':ident,'location':location,'rows':rows,'columns':columns,'header_rows':list(header_rows),'cells':[],**metadata}
        self.tables.append(table);return table
    def finish(self,status=None):
        text=''.join(self.fragments)
        value={'schema':SCHEMA,'format':self.format,'raw_sha256':self.raw_sha,'text':text,'text_length':len(text),'text_sha256':sha(text.encode('utf-8')),'locations':self.locations,'tables':self.tables,'coverage':self.coverage,'profile':self.profile,'status':status or ('ready' if text else 'empty-success')}
        validate(value);return value


def validate(value):
    if not isinstance(value,dict) or set(value)!={'schema','format','raw_sha256','text','text_length','text_sha256','locations','tables','coverage','profile','status'}:
        raise ValueError('处理结果字段不完整或含未知字段')
    if value['schema']!=SCHEMA or value['format'] not in {'docx','xlsx','pdf'} or value['status'] not in {'ready','partial','empty-success'}:raise ValueError('不支持的结果schema/格式/状态')
    text=value['text']
    if not isinstance(text,str) or len(text.encode('utf-8'))>TEXT_LIMIT or '\r' in text or '\0' in text or text.startswith('\ufeff'):raise ValueError('规范文本无效或超过8MiB')
    if type(value['text_length']) is not int or value['text_length']!=len(text) or value['text_sha256']!=sha(text.encode('utf-8')):raise ValueError('处理文本摘要/长度不匹配')
    if not isinstance(value['raw_sha256'],str) or len(value['raw_sha256'])!=64 or any(c not in '0123456789abcdef' for c in value['raw_sha256']):raise ValueError('原件摘要无效')
    if not isinstance(value['locations'],list) or not isinstance(value['tables'],list) or not isinstance(value['coverage'],dict) or not isinstance(value['profile'],dict):raise ValueError('结果结构无效')
    # Creation and receive-only validation share the same declared coverage.
    if value['format'] in {'docx','xlsx'} and not text and value['coverage'].get('excluded'):
        raise ValueError('Office无可用支持文字且存在未支持对象；不能标为空内容成功')
    def location(loc):
        if not isinstance(loc,dict):raise ValueError('定位须为对象')
        if 'start' in loc or 'end' in loc:
            if type(loc.get('start')) is not int or type(loc.get('end')) is not int or not 0<=loc['start']<loc['end']<=len(text):raise ValueError('定位超出规范文本')
        if 'page' in loc and (type(loc['page']) is not int or not 1<=loc['page']<=200):raise ValueError('页码无效')
        if 'bbox' in loc:
            box=loc['bbox']
            if not isinstance(box,list) or len(box)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1 for x in box) or box[0]>box[2] or box[1]>box[3]:raise ValueError('页面区域无效')
    for loc in value['locations']:location(loc)
    ids=set()
    for table in value['tables']:
        if not isinstance(table,dict) or not isinstance(table.get('table_id'),str) or table['table_id'] in ids:raise ValueError('表格身份重复/无效')
        ids.add(table['table_id']);location(table.get('location'))
        if any(type(table.get(k)) is not int or table[k]<1 for k in ('rows','columns')):raise ValueError('表格尺寸无效')
        cells=table.get('cells')
        if not isinstance(cells,list):raise ValueError('表格单元格须为列表')
        coords=set()
        for cell in cells:
            if not isinstance(cell,dict):raise ValueError('单元格须为对象')
            row,column=cell.get('row'),cell.get('column')
            if type(row) is not int or type(column) is not int or not 1<=row<=table['rows'] or not 1<=column<=table['columns'] or (row,column) in coords:raise ValueError('单元格重复/越界')
            coords.add((row,column));location(cell.get('location'))
            if cell.get('text') is not None and not isinstance(cell['text'],str):raise ValueError('单元格文字类型无效')
            if not cell.get('merged_into'):
                if any(type(cell.get(k)) is not int or cell[k]<1 for k in ('row_span','column_span')) or row+cell['row_span']>table['rows']+1 or column+cell['column_span']>table['columns']+1:raise ValueError('合并跨度越界')
    if len(encode(value))>RESULT_LIMIT:raise ValueError('完整处理结果超过16MiB')
    return value


def _covers_columns(cell, start, end):
    # Merge continuations address one coordinate; only the real master spans.
    span = 1 if cell.get('merged_into') else cell['column_span']
    return cell['column'] < end and start < cell['column'] + span


def table_view(result,table_id=None,*,row_start=None,row_end=None,column_start=None,column_end=None,anchor=None):
    tables=result['tables']
    if table_id is None:
        if len(tables)!=1:raise ValueError('须从tables定位选择table_id')
        table=tables[0]
    else:
        table=next((t for t in tables if t['table_id']==table_id),None)
        if table is None:raise ValueError('表格不属于当次文档快照')
    explicit=any(x is not None for x in (row_start,row_end,column_start,column_end))
    if anchor and anchor.get('table_id')==table['table_id'] and not explicit:
        r=max(1,min(anchor['row'],table['rows']-19));c=max(1,min(anchor['column'],table['columns']-9));origin='search_hit'
    else:r=c=1;origin='explicit' if explicit else 'table_start'
    suggested=anchor.get('suggested_window') if anchor and anchor.get('table_id')==table['table_id'] and not explicit else None
    r=row_start if row_start is not None else (suggested['row_start'] if suggested else r);c=column_start if column_start is not None else (suggested['column_start'] if suggested else c)
    re=row_end if row_end is not None else (suggested['row_end'] if suggested else min(table['rows']+1,r+20));ce=column_end if column_end is not None else (suggested['column_end'] if suggested else min(table['columns']+1,c+10))
    if any(type(x) is not int for x in (r,re,c,ce)) or not 1<=r<re<=table['rows']+1 or not 1<=c<ce<=table['columns']+1:raise ValueError('表格窗口越界')
    selected=[x for x in table['cells'] if r<=x['row']<re and c<=x['column']<ce]
    header_rows=table.get('header_rows') or ([min(x['row'] for x in table['cells'] if x.get('text') not in ('',None))] if any(x.get('text') not in ('',None) for x in table['cells']) else [])
    headers=[x for x in table['cells'] if x['row'] in header_rows and _covers_columns(x,c,ce)]
    union={(x['row'],x['column']):x for x in selected+headers}
    if len(union)>1000 or sum(len(x.get('text') or '') for x in union.values())>16000:raise ValueError('表格窗口及必要表头超过1000格/16000字符，请缩小范围或核对原件')
    return {**{k:v for k,v in table.items() if k!='cells'},'cells':selected,'window':{'row_start':r,'row_end':re,'column_start':c,'column_end':ce},'window_origin':origin,'header_context':{'role':'explicit_header' if table.get('header_rows') else 'first_content_row','cells':headers}}


def hit_context(result,point):
    """Locate the actual normalized-text hit without parsing the source again.

    Word cell locations address a structural container, while its paragraphs
    carry normalized character spans. Choose the deepest matching container so
    nested tables cannot borrow an outer cell's row/column.
    """
    locations=[loc for loc in result['locations'] if loc.get('start',-1)<=point<loc.get('end',-1)]
    matches=[]
    for table in result['tables']:
        for cell in table['cells']:
            loc=cell['location'];specificity=-1
            if loc.get('start',-1)<=point<loc.get('end',-1):specificity=0
            elif 'path' in loc:
                prefix=loc['path']+'/'
                if any(part.get('part')==loc.get('part') and part.get('path','').startswith(prefix) for part in locations):specificity=len(prefix)
            if specificity>=0:matches.append((specificity,table,cell))
    if not matches:return None,None,2000
    _,table,cell=max(matches,key=lambda item:item[0])
    anchor={'table_id':table['table_id'],'row':cell['row'],'column':cell['column']}
    rows=min(20,table['rows']);columns=min(10,table['columns']);view=None
    while True:
        r=max(1,min(cell['row'],table['rows']-rows+1));c=max(1,min(cell['column'],table['columns']-columns+1))
        window={'row_start':r,'row_end':r+rows,'column_start':c,'column_end':c+columns}
        try:
            view=table_view(result,table['table_id'],**window);break
        except ValueError as exc:
            if '1000' not in str(exc) or '16000' not in str(exc):raise
            if rows>1:rows-=1
            elif columns>1:columns-=1
            else:break
    if view is None:
        # A table-read quota does not erase source context from search. Summarize
        # the true headers for this cell's columns and retain the original hint.
        c=cell['column'];ce=min(table['columns']+1,c+cell['column_span'])
        header_rows=table.get('header_rows') or ([min(x['row'] for x in table['cells'] if x.get('text') not in ('',None))] if any(x.get('text') not in ('',None) for x in table['cells']) else [])
        headers={'role':'explicit_header' if table.get('header_rows') else 'first_content_row',
                 'cells':[x for x in table['cells'] if x['row'] in header_rows and _covers_columns(x,c,ce)]}
        window=None
    else:
        anchor['suggested_window']=window;headers=view['header_context']
    budget=1600;header_cells=[];truncated=False
    for value in headers['cells']:
        text=value.get('text');length=len(text or '');shown=min(length,budget);budget-=shown
        clipped={**value,'text':text[:shown] if isinstance(text,str) else text}
        if shown<length:clipped.update(text_truncated=True,text_length=length);truncated=True
        header_cells.append(clipped)
    used=sum(len(value.get('text') or '') for value in header_cells)
    context={'table_id':table['table_id'],'matched_cells':[{k:cell[k] for k in ('row','column','row_span','column_span','location')}],
             'suggested_window':window,'header_context':{'role':headers['role'],'cells':header_cells},'needs_expansion':truncated or view is None}
    if view is None:context['reason']='命中单元格及必要上下文超过1000格/16000字符，请核对原件'
    return context,anchor,2000-used

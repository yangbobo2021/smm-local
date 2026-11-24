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
        ids.add(table['table_id']);location(table['location'])
        if any(type(table.get(k)) is not int or table[k]<1 for k in ('rows','columns')):raise ValueError('表格尺寸无效')
        coords=set()
        for cell in table['cells']:
            row,column=cell.get('row'),cell.get('column')
            if type(row) is not int or type(column) is not int or not 1<=row<=table['rows'] or not 1<=column<=table['columns'] or (row,column) in coords:raise ValueError('单元格重复/越界')
            coords.add((row,column));location(cell['location'])
            if cell.get('text') is not None and not isinstance(cell['text'],str):raise ValueError('单元格文字类型无效')
            if not cell.get('merged_into'):
                if any(type(cell.get(k)) is not int or cell[k]<1 for k in ('row_span','column_span')) or row+cell['row_span']>table['rows']+1 or column+cell['column_span']>table['columns']+1:raise ValueError('合并跨度越界')
    if len(encode(value))>RESULT_LIMIT:raise ValueError('完整处理结果超过16MiB')
    return value


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
    r=row_start if row_start is not None else r;c=column_start if column_start is not None else c
    re=row_end if row_end is not None else min(table['rows']+1,r+20);ce=column_end if column_end is not None else min(table['columns']+1,c+10)
    if any(type(x) is not int for x in (r,re,c,ce)) or not 1<=r<re<=table['rows']+1 or not 1<=c<ce<=table['columns']+1:raise ValueError('表格窗口越界')
    selected=[x for x in table['cells'] if r<=x['row']<re and c<=x['column']<ce]
    header_rows=table.get('header_rows') or ([min(x['row'] for x in table['cells'] if x.get('text') not in ('',None))] if any(x.get('text') not in ('',None) for x in table['cells']) else [])
    headers=[x for x in table['cells'] if x['row'] in header_rows and c<=x['column']<ce]
    union={(x['row'],x['column']):x for x in selected+headers}
    if len(union)>1000 or sum(len(x.get('text') or '') for x in union.values())>16000:raise ValueError('表格窗口及必要表头超过1000格/16000字符，请缩小范围或核对原件')
    return {**{k:v for k,v in table.items() if k!='cells'},'cells':selected,'window':{'row_start':r,'row_end':re,'column_start':c,'column_end':ce},'window_origin':origin,'header_context':{'role':'explicit_header' if table.get('header_rows') else 'first_content_row','cells':headers}}

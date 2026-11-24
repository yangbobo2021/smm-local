"""SpreadsheetML values and formula caches; no calculation, Office or networking."""
from __future__ import annotations
from datetime import datetime,timedelta
from decimal import Decimal,InvalidOperation
import re
from .ooxml import Package,local,children,first,attr,truth
from ..document_results import Builder

BUILTIN={0:'General',14:'mm-dd-yy',15:'d-mmm-yy',16:'d-mmm',17:'mmm-yy',18:'h:mm AM/PM',19:'h:mm:ss AM/PM',20:'h:mm',21:'h:mm:ss',22:'m/d/yy h:mm',45:'mm:ss',46:'[h]:mm:ss',47:'mmss.0'}
DATE_IDS=set(range(14,23))|set(range(27,37))|{45,46,47}|set(range(50,59))


def position(value):
    match=re.fullmatch(r'([A-Za-z]{1,3})([1-9][0-9]{0,6})',value or '')
    if not match:raise ValueError('无效的A1坐标')
    column=0
    for letter in match[1].upper():column=column*26+ord(letter)-64
    row=int(match[2])
    if row>1048576 or column>16384:raise ValueError('单元格超出XLSX范围')
    return row,column


def letters(column):
    if not 1<=column<=16384:raise ValueError('共享公式引用越界')
    result=''
    while column:column,remainder=divmod(column-1,26);result=chr(65+remainder)+result
    return result


def bounds(value):
    ends=value.split(':')
    if len(ends) not in {1,2}:raise ValueError('单元格范围无效')
    r,c=position(ends[0]);re_,ce=position(ends[-1])
    if r>re_ or c>ce:raise ValueError('单元格范围顺序无效')
    return r,c,re_,ce


def translate(formula,base,target):
    br,bc=position(base);tr,tc=position(target)
    def replace(match):
        absolute_col,col,absolute_row,row=match.groups();rr,cc=position(col+row)
        if not absolute_col:cc+=tc-bc
        if not absolute_row:rr+=tr-br
        if not 1<=rr<=1048576:raise ValueError('共享公式引用越界')
        return absolute_col+letters(cc)+absolute_row+str(rr)
    # Formula quoted literals/sheet names are retained, never interpreted.
    pieces=re.split(r"""("(?:[^"]|"")*"|'(?:[^']|'')*')""",formula)
    pattern=r'(?<![A-Za-z0-9_.])([$]?)([A-Za-z]{1,3})([$]?)([1-9][0-9]*)(?![A-Za-z0-9_(])'
    return ''.join(piece if i%2 else re.sub(pattern,replace,piece) for i,piece in enumerate(pieces))


def text_runs(node):
    if node is None:return ''
    if local(node.tag)=='rPh':return ''
    if local(node.tag)=='t':return node.text or ''
    return ''.join(text_runs(child) for child in node)


def date_value(serial,format,date1904):
    try:value=Decimal(serial)
    except InvalidOperation as exc:raise ValueError('日期序列无效') from exc
    if not value.is_finite():raise ValueError('日期序列非有限值')
    # Excel deliberately preserves the fictitious 1900 leap day. Preserve its
    # serial and explain the absence of a valid ISO calendar date.
    # https://learn.microsoft.com/en-us/office/troubleshoot/excel/wrongly-assumes-1900-is-leap-year
    if not date1904 and 60<=value<61:
        return {'serial':serial,'number_format':format,'date_system':'1900','iso':None,'reason':'excel_1900_fictitious_leap_day'}
    days=int(value//1);fraction=value-Decimal(days)
    if not date1904 and value>=61:days-=1
    try:
        converted=(datetime(1904,1,1) if date1904 else datetime(1899,12,31))+timedelta(days=days,microseconds=int(fraction*Decimal(86400000000)))
    except (OverflowError,ValueError) as exc:raise ValueError('日期超出ISO日期范围') from exc
    iso=converted.date().isoformat() if not fraction else converted.isoformat()
    return {'serial':serial,'iso':iso,'number_format':format,'date_system':'1904' if date1904 else '1900'}


def parse(raw,raw_sha,profile):
    package=Package(raw,'xlsx');builder=Builder('xlsx',raw_sha,profile)
    book=package.xml(package.main)
    if local(book.tag)!='workbook':raise ValueError('Excel主部件结构无效')
    prop=first(book,'workbookPr');date1904=truth(attr(prop,'date1904','0'))
    sheets_node=first(book,'sheets');sheets=children(sheets_node,'sheet') if sheets_node is not None else []
    if len(sheets)>64:raise ValueError('XLSX工作表超过64')
    relations=package.relationships(package.main);shared=[];formats=dict(BUILTIN);styles=[0]
    for rel in relations.values():
        if rel['external']:continue
        if rel['type'].endswith('/sharedStrings'):
            shared=[text_runs(node) for node in package.xml(package.target(package.main,rel)) if local(node.tag)=='si']
        if rel['type'].endswith('/styles'):
            root=package.xml(package.target(package.main,rel));custom=first(root,'numFmts');xfs=first(root,'cellXfs')
            if custom is not None:
                for node in custom:formats[int(attr(node,'numFmtId'))]=attr(node,'formatCode','')
            if xfs is not None:styles=[int(attr(node,'numFmtId','0')) for node in xfs]
    targets=[];names=set();ids=set();total=0
    for index,sheet in enumerate(sheets,1):
        name=attr(sheet,'name');ident=attr(sheet,'sheetId');rid=attr(sheet,'id')
        if not name or name.casefold() in names or not ident or ident in ids or rid not in relations:raise ValueError('工作表名称或关系无效/重复')
        names.add(name.casefold());ids.add(ident);rel=relations[rid]
        if not rel['type'].endswith('/worksheet'):
            builder.coverage['excluded'].append('non_worksheet_sheet');continue
        part=package.target(package.main,rel);root=package.xml(part);data=first(root,'sheetData');entries=[];seen=set();hidden_rows=set()
        if local(root.tag)!='worksheet':raise ValueError('工作表结构无效')
        for row in children(data,'row') if data is not None else []:
            if truth(attr(row,'hidden','0')):hidden_rows.add(int(attr(row,'r')))
            for cell in children(row,'c'):
                coordinate=attr(cell,'r');rc=position(coordinate)
                if rc in seen:raise ValueError('单元格坐标重复')
                seen.add(rc)
                v=first(cell,'v');inline=first(cell,'is');formula=first(cell,'f')
                if formula is None and (v is None or v.text is None) and not text_runs(inline):continue
                entries.append((rc,coordinate.upper(),cell));total+=1
        if total>100000:raise ValueError('XLSX非空值/公式单元格超过100000')
        state=attr(sheet,'state','visible')
        if state not in {'visible','hidden','veryHidden'}:raise ValueError('工作表可见性无效')
        targets.append((index,name,state,part,root,sorted(entries),hidden_rows))
    for index,name,state,part,root,entries,hidden_rows in targets:
        location={'part':part,'sheet':name,'sheet_index':index};columns=first(root,'cols');hidden_columns=[]
        if columns is not None:
            for col in children(columns,'col'):
                start=int(attr(col,'min'));end=int(attr(col,'max'))
                if not 1<=start<=end<=16384:raise ValueError('列范围无效')
                if truth(attr(col,'hidden','0')):hidden_columns.append((start,end))
        merged=[];merge_node=first(root,'mergeCells')
        if merge_node is not None:merged=[bounds(attr(m,'ref')) for m in children(merge_node,'mergeCell')]
        shared_formulas={}
        for rc,coordinate,cell in entries:
            formula=first(cell,'f')
            if formula is not None and attr(formula,'t')=='shared' and formula.text is not None:
                si=attr(formula,'si')
                if si in shared_formulas:raise ValueError('共享公式基准重复')
                shared_formulas[si]=(coordinate,formula.text,attr(formula,'ref'))
        cells=[];maxrow=max([rc[0] for rc,_,_ in entries]+[x[2] for x in merged]+[1]);maxcol=max([rc[1] for rc,_,_ in entries]+[x[3] for x in merged]+[1])
        table=builder.table(location,maxrow,maxcol,sheet_state=state)
        for (row,col),coordinate,node in entries:
            typ=attr(node,'t','n');v=first(node,'v');value=v.text if v is not None and v.text is not None else '';formula=first(node,'f');style=int(attr(node,'s','0'))
            if not 0<=style<len(styles):raise ValueError('单元格样式引用无效')
            numfmt=styles[style];fmt=formats.get(numfmt,'builtin:'+str(numfmt))
            plain=re.sub(r'"[^"]*"|\\.|\[[^\]]*\]','',fmt).lower()
            is_date=numfmt in DATE_IDS or bool(re.search(r'[ymdhs]',plain))
            date=None
            if typ=='s':
                try:text=shared[int(value)]
                except (ValueError,IndexError) as exc:raise ValueError('共享字符串引用无效') from exc
                data_type='string'
            elif typ=='inlineStr':text=text_runs(first(node,'is'));data_type='string'
            elif typ in {'str','e'}:text=value;data_type='string' if typ=='str' else 'error'
            elif typ=='b':
                if value not in {'0','1'}:raise ValueError('布尔值无效')
                text='TRUE' if value=='1' else 'FALSE';data_type='boolean'
            elif typ=='d':
                try:datetime.fromisoformat(value.replace('Z','+00:00'))
                except ValueError as exc:raise ValueError('ISO日期值无效') from exc
                text=value;data_type='date';date={'serial':None,'iso':value,'number_format':fmt,'date_system':'1904' if date1904 else '1900'}
            elif typ=='n':
                if value:
                    try:number=Decimal(value)
                    except InvalidOperation as exc:raise ValueError('数值无效') from exc
                    if not number.is_finite():raise ValueError('非有限数值无效')
                text=value;data_type='number'
                if value and is_date:date=date_value(value,fmt,date1904);text=date['iso'] or value;data_type='date'
            else:raise ValueError('不支持的单元格数据类型')
            cell={'row':row,'column':col,'text':text,'type':data_type,'row_span':1,'column_span':1,'row_hidden':row in hidden_rows,'column_hidden':any(a<=col<=b for a,b in hidden_columns),'sheet_state':state,'location':{**location,'coordinate':coordinate}}
            if date:cell['date']=date
            if formula is not None:
                actual=formula.text or '';kind=attr(formula,'t','normal')
                if kind=='shared' and not actual:
                    base=shared_formulas.get(attr(formula,'si'))
                    if base is None:raise ValueError('共享公式缺少基准')
                    actual=translate(base[1],base[0],coordinate);cell['formula_source']={'coordinate':base[0],'text':base[1]}
                cell['formula']=actual;cell['formula_kind']=kind;cell['type']='formula'
                cache={'status':'present','value':value,'type':data_type,'freshness':'unknown'} if v is not None else {'status':'missing','value':None,'freshness':'unknown'}
                cell['cache']=cache;cell['text']='='+actual+(' [cached: '+text+']' if v is not None else ' [cache: missing]')
            for r,c,re_,ce in merged:
                if r<=row<=re_ and c<=col<=ce:
                    if (row,col)==(r,c):cell.update(row_span=re_-r+1,column_span=ce-c+1)
                    else:
                        # Do not invent values at merge continuations. A real
                        # nonempty conflicting continuation makes input invalid.
                        if cell['text']:raise ValueError('合并续格包含独立值，无法无损表示')
                        cell.update(text=None,merged_into={'row':r,'column':c})
            if cell['text']:cell['location']=builder.add(cell['text'],cell['location'])
            table['cells'].append(cell)
        builder.coverage['units'].append({**location,'method':'native','status':'ready'})
    excluded=set(builder.coverage['excluded'])
    for root in package.xml_cache.values():
        for node in root.iter():
            if local(node.tag) in {'drawing','legacyDrawing','externalLink','comment','chart','pivotTableDefinition'}:excluded.add(local(node.tag))
    builder.coverage['excluded']=sorted(excluded)
    return builder.finish()

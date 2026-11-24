"""WordprocessingML visible text, source paths and explicit merged grids."""
from .ooxml import Package,local,children,first,attr,truth
from ..document_results import Builder

EXCLUDED={'drawing','pict','object','comment','instrText','delText'}


def parse(raw,raw_sha,profile):
    package=Package(raw,'docx');builder=Builder('docx',raw_sha,profile)
    root=package.xml(package.main)
    if local(root.tag)!='document' or first(root,'body') is None:raise ValueError('Word主部件结构无效')
    excluded=set()
    for xml in package.xml_cache.values():
        for element in xml.iter():
            name=local(element.tag)
            if name in {'ins','del','moveFrom','moveTo'}:builder.coverage['revisions_present']=True
            if name in EXCLUDED and name not in {'delText','instrText'}:excluded.add('drawing' if name=='pict' else name)
    builder.coverage['excluded']=sorted(excluded)

    def visible(node):
        name=local(node.tag)
        if name in EXCLUDED|{'del','moveFrom'}:return ''
        if name=='t':return node.text or ''
        if name=='tab':return '\t'
        if name in {'br','cr'}:return '\n'
        return ''.join(visible(child) for child in node)

    def blocks(node):
        for child in node:
            name=local(child.tag)
            if name in {'p','tbl'}:yield child
            elif name in {'sdt','sdtContent','customXml','ins','moveTo'}:yield from blocks(child)

    def walk(node,part,path):
        counters={'p':0,'tbl':0};own=[]
        for child in blocks(node):
            name=local(child.tag);counters[name]+=1
            current=path+'/'+('paragraph' if name=='p' else 'table')+'['+str(counters[name])+']'
            if name=='p':
                text=visible(child)
                if text:builder.add(text,{'part':part,'path':current});own.append(text)
            else:table(child,part,current)
        return '\n'.join(own)

    def table(node,part,path):
        rows=children(node,'tr');data=[];previous={};width=0;headers=[]
        for ri,row in enumerate(rows,1):
            prop=first(row,'trPr')
            header=first(prop,'tblHeader') if prop is not None else None
            if header is not None and truth(attr(header,'val','true')):headers.append(ri)
            before=first(prop,'gridBefore') if prop is not None else None
            col=int(attr(before,'val','0'))+1;current={}
            for cell in children(row,'tc'):
                pr=first(cell,'tcPr');span=first(pr,'gridSpan') if pr is not None else None
                colspan=int(attr(span,'val','1'))
                if colspan<1:raise ValueError('Word合并跨度无效')
                vm=first(pr,'vMerge') if pr is not None else None
                continuation=vm is not None and attr(vm,'val','continue')!='restart'
                if continuation:
                    anchor=previous.get(col)
                    if anchor is None or anchor['column_span']!=colspan:raise ValueError('Word纵向合并缺少匹配主格')
                    anchor['row_span']+=1
                    for c in range(col,col+colspan):current[c]=anchor
                else:
                    location={'part':part,'path':path+'/row['+str(ri)+']/cell['+str(col)+']'}
                    text=walk(cell,part,location['path'])
                    value={'row':ri,'column':col,'text':text,'type':'string','row_span':1,'column_span':colspan,'location':location}
                    data.append(value)
                    if vm is not None:
                        for c in range(col,col+colspan):current[c]=value
                col+=colspan
            width=max(width,col-1);previous=current
        value=builder.table({'part':part,'path':path},len(rows),width,header_rows=headers)
        value['cells']=data
    walk(first(root,'body'),package.main,'body')
    parts=[package.main]
    relations=package.relationships(package.main)
    for kind,root_name in [('header','header'),('footer','footer'),('footnotes','footnotes'),('endnotes','endnotes')]:
        selected=sorted({package.target(package.main,r) for r in relations.values() if r['type'].endswith('/'+kind) and not r['external']})
        for part in selected:
            node=package.xml(part);parts.append(part)
            if kind in {'footnotes','endnotes'}:
                for note in node:
                    if attr(note,'type') in {'separator','continuationSeparator'} or int(attr(note,'id','-1'))<0:continue
                    walk(note,part,root_name+'/note['+attr(note,'id')+']')
            else:walk(node,part,root_name)
    builder.coverage['parts']=parts
    builder.coverage['units']=[{'part':p,'method':'native','status':'ready'} for p in parts]
    return builder.finish()

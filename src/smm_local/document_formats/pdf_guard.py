"""Worker-local bounded PDF streams and a decoded, private PDF intermediate."""
from __future__ import annotations
from contextlib import contextmanager
from io import BytesIO
import math
import os
from pathlib import Path
from . import pdf_filters

MIB=1024*1024
PAGE_LIMIT=32*MIB
TOTAL_LIMIT=128*MIB
PIXELS=16000000


class Budget:
    def __init__(self):self.total=0;self.pages={};self.owners={};self.sizes={};self.streams={}
    def remaining(self,stream):
        key=id(stream);limits=[TOTAL_LIMIT-self.total]
        limits.extend(PAGE_LIMIT-self.pages.get(page,0) for page in self.owners.get(key,set()))
        return max(0,min(limits))
    def charge(self,stream,count):
        if count>self.remaining(stream):raise ValueError('PDF实际解压超过单页32MiB或全文件128MiB')
        self.total+=count;key=id(stream);self.sizes[key]=self.sizes.get(key,0)+count
        for page in self.owners.get(key,set()):self.pages[page]=self.pages.get(page,0)+count
    def content(self,stream,page):
        key=id(stream);self.streams[key]=stream;owners=self.owners.setdefault(key,set())
        if page not in owners:
            decoded=self.sizes.get(key,0)
            if self.pages.get(page,0)+decoded>PAGE_LIMIT:raise ValueError('PDF同页内容流累计超过32MiB')
            self.pages[page]=self.pages.get(page,0)+decoded;owners.add(page)


def install(budget):
    import pdfminer.pdfparser as parser_module
    from pdfminer.pdftypes import PDFStream,resolve1
    from importlib.metadata import version
    if version('pdfminer.six')!='20260107' or parser_module.PDFStream is not PDFStream:raise ValueError('guard_unavailable: PDF解码接入版本不符')
    class Stream(PDFStream):
        def decode(self):
            if self.decipher:raise ValueError('加密PDF不支持')
            data=self.rawdata
            if data is None:raise ValueError('PDF流缺少原字节')
            filters=self.get_filters()
            if not filters:budget.charge(self,len(data))
            for name,parameters in filters:
                name=getattr(name,'name',None);params=resolve1(parameters) or {}
                if not isinstance(params,dict):raise ValueError('PDF解码参数无效')
                params={k:resolve1(v) for k,v in params.items()};sink=pdf_filters.Sink(budget,self)
                if name in {'FlateDecode','Fl'}:data=pdf_filters.flate(data,sink)
                elif name in {'ASCII85Decode','A85'}:data=pdf_filters.ascii_85(data,sink)
                elif name in {'ASCIIHexDecode','AHx'}:data=pdf_filters.ascii_hex(data,sink)
                elif name in {'RunLengthDecode','RL'}:data=pdf_filters.run_length(data,sink)
                elif name in {'LZWDecode','LZW'}:data=pdf_filters.lzw(data,sink,int(params.get('EarlyChange',1)))
                elif name in {'DCTDecode','DCT','JPXDecode','JBIG2Decode','CCITTFaxDecode','CCF'}:raise ValueError('guard_unavailable: 图像编解码安全路径尚未建立')
                else:raise ValueError('不支持或不安全的PDF过滤器: '+str(name))
                if 'Predictor' in params:data=pdf_filters.predictor(data,params,TOTAL_LIMIT)
            self.data=data;self.rawdata=None
    @contextmanager
    def patch():
        original=parser_module.PDFStream;parser_module.PDFStream=Stream
        try:yield
        finally:parser_module.PDFStream=original
    return patch()


def normalize_name(value):
    raw=value.encode('utf-8') if isinstance(value,str) else bytes(value)
    return b'/'+b''.join(bytes([c]) if 33<=c<=126 and c not in b'#%()/<>[]{}' else ('#%02X'%c).encode('ascii') for c in raw)


def intermediate(raw,output):
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdftypes import PDFObjRef,PDFStream,resolve1
    from pdfminer.psparser import PSLiteral
    if not raw.startswith(b'%PDF-'):raise ValueError('扩展名与实际PDF容器不符')
    budget=Budget();output=Path(output)
    with install(budget):
        doc=PDFDocument(PDFParser(BytesIO(raw)))
        if doc.encryption:raise ValueError('加密PDF不支持')
        pages=[]
        for page in PDFPage.create_pages(doc):
            pages.append(page)
            if len(pages)>200:raise ValueError('PDF页数超过200')
        for number,page in enumerate(pages,1):
            box=page.mediabox
            if len(box)!=4 or any(not math.isfinite(float(v)) for v in box) or box[2]<=box[0] or box[3]<=box[1]:raise ValueError('PDF页面尺寸无效')
            def content(value):
                value=resolve1(value)
                if isinstance(value,list):
                    for item in value:content(item)
                elif isinstance(value,PDFStream):budget.content(value,number)
                elif value is not None:raise ValueError('PDF页面内容流类型无效')
            content(page.contents);visited=set()
            def resources(value):
                value=resolve1(value)
                if not isinstance(value,dict):raise ValueError('PDF页资源无效')
                if id(value) in visited:return
                visited.add(id(value));xobjects=resolve1(value.get('XObject',{}))
                if not isinstance(xobjects,dict):raise ValueError('PDF XObject资源无效')
                for resource in xobjects.values():
                    resource=resolve1(resource)
                    if not isinstance(resource,PDFStream):raise ValueError('PDF XObject不是流')
                    subtype=getattr(resolve1(resource.attrs.get('Subtype')),'name',None)
                    if subtype=='Form':
                        budget.content(resource,number);nested=resource.attrs.get('Resources')
                        if nested is not None:resources(nested)
                    elif subtype=='Image':
                        width=resolve1(resource.attrs.get('Width'));height=resolve1(resource.attrs.get('Height'))
                        if type(width) is not int or type(height) is not int or width<1 or height<1 or width*height>PIXELS:raise ValueError('PDF待解码图像超过1600万像素或尺寸无效')
            resources(page.resources)
        root_ref=None
        for xref in doc.xrefs:
            root=xref.get_trailer().get('Root')
            if isinstance(root,PDFObjRef):root_ref=root.objid;break
        mapping={root_ref:1} if root_ref is not None else {};queue=[doc.catalog];offsets=[0];written=0
        def reference(obj):
            if obj.objid not in mapping:
                mapping[obj.objid]=len(queue)+1;queue.append(doc.getobj(obj.objid))
            return (str(mapping[obj.objid])+' 0 R').encode('ascii')
        def scalar(obj):
            if isinstance(obj,PDFObjRef):return reference(obj)
            if isinstance(obj,PSLiteral):return normalize_name(obj.name)
            if obj is None:return b'null'
            if type(obj) is bool:return b'true' if obj else b'false'
            if type(obj) is int:return str(obj).encode('ascii')
            if type(obj) is float:
                if not math.isfinite(obj):raise ValueError('PDF非有限数值无效')
                return format(obj,'.15g').encode('ascii')
            if isinstance(obj,bytes):return b'<'+obj.hex().encode('ascii')+b'>'
            if isinstance(obj,str):return b'<'+obj.encode('utf-8').hex().encode('ascii')+b'>'
            if isinstance(obj,(list,tuple)):return b'['+b' '.join(scalar(x) for x in obj)+b']'
            if isinstance(obj,dict):return b'<<'+b' '.join(normalize_name(k)+b' '+scalar(v) for k,v in obj.items())+b'>>'
            raise ValueError('无法安全序列化PDF对象')
        with output.open('xb') as stream:
            def write(value):
                nonlocal written
                if written+len(value)>256*MIB:raise ValueError('PDF私有中间材料超过任务临时预算')
                stream.write(value);written+=len(value)
            write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
            index=0
            while index<len(queue):
                obj=queue[index];index+=1;offsets.append(written);write((str(index)+' 0 obj\n').encode('ascii'))
                if isinstance(obj,PDFStream):
                    data=obj.get_data();attrs={k:v for k,v in obj.attrs.items() if k not in {'Length','Filter','F','DecodeParms','DP','FDecodeParms'}};attrs['Length']=len(data)
                    write(scalar(attrs));write(b'\nstream\n')
                    for start in range(0,len(data),65536):write(data[start:start+65536])
                    write(b'\nendstream')
                else:write(scalar(obj))
                write(b'\nendobj\n')
            xref_at=written;write(('xref\n0 '+str(len(offsets))+'\n0000000000 65535 f \n').encode('ascii'))
            for offset in offsets[1:]:write(('%010d 00000 n \n'%offset).encode('ascii'))
            write(('trailer\n<< /Size '+str(len(offsets))+' /Root 1 0 R >>\nstartxref\n'+str(xref_at)+'\n%%EOF\n').encode('ascii'));stream.flush();os.fsync(stream.fileno())
    return {'path':str(output),'pages':len(pages),'decoded_bytes':budget.total,'page_content_bytes':budget.pages,'intermediate_bytes':written}

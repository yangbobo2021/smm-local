"""Creator-worker-only bounded OPC reading. No filesystem extraction or network."""
from __future__ import annotations
import io
import posixpath
import stat
import zipfile
from urllib.parse import unquote,urlsplit
from defusedxml import ElementTree as ET

MIB=1024*1024
MAX_MEMBERS=10000
MAX_EXPANDED=100*MIB
REL='http://schemas.openxmlformats.org/package/2006/relationships'


def local(tag):return tag.rsplit('}',1)[-1]
def children(node,name):return [c for c in node if local(c.tag)==name]
def first(node,name):return next((c for c in node if local(c.tag)==name),None)
def attr(node,name,default=None):return next((v for k,v in node.attrib.items() if local(k)==name),default) if node is not None else default

def truth(value):return str(value).lower() not in {'0','false','off','no'}


class Package:
    def __init__(self,raw,format):
        if not raw.startswith(b'PK'):raise ValueError('扩展名与实际OOXML容器不符')
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                infos=archive.infolist()
                if len(infos)>MAX_MEMBERS:raise ValueError('容器成员超过10000')
                self.files={};total=0
                for info in infos:
                    name=info.filename
                    if not name or name.startswith(('/','\\')) or '\\' in name or ':' in name or any(p in {'.','..'} for p in name.rstrip('/').split('/')) or name in self.files or stat.S_ISLNK(info.external_attr>>16):raise ValueError('不安全或重复的容器成员路径')
                    if info.flag_bits&1:raise ValueError('加密容器不支持')
                    if info.is_dir():continue
                    chunks=[]
                    with archive.open(info) as stream:
                        while True:
                            block=stream.read(min(65536,MAX_EXPANDED-total+1))
                            if not block:break
                            total+=len(block)
                            if total>MAX_EXPANDED:raise ValueError('容器展开超过100MiB')
                            chunks.append(block)
                    self.files[name]=b''.join(chunks)
                self.expanded_bytes=total
        except (zipfile.BadZipFile,RuntimeError,NotImplementedError) as exc:raise ValueError('损坏或不支持的OOXML容器') from exc
        self.xml_cache={}
        # Parsing every XML part rejects hidden DTD/entity payloads as well.
        for name in self.files:
            if name.endswith(('.xml','.rels')):self.xml(name)
        types=self.xml('[Content_Types].xml')
        self.types={attr(x,'PartName','').lstrip('/'):attr(x,'ContentType','') for x in types if local(x.tag)=='Override'}
        if any('macroenabled' in t.lower() or 'vbaproject' in t.lower() for t in self.types.values()) or any('vbaproject' in n.lower() for n in self.files):raise ValueError('含宏容器不支持')
        main_rels=self.relationships('')
        mains=[r for r in main_rels.values() if r['type'].endswith('/officeDocument')]
        if len(mains)!=1:raise ValueError('OOXML主部件关系无效')
        self.main=self.target('',mains[0])
        expected={'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'}[format]
        if self.types.get(self.main)!=expected:raise ValueError('扩展名与实际OOXML内容类型不符')
    def xml(self,name):
        if name not in self.files:raise ValueError('缺少OOXML部件: '+name)
        if name not in self.xml_cache:
            try:self.xml_cache[name]=ET.fromstring(self.files[name],forbid_dtd=True,forbid_entities=True,forbid_external=True)
            except Exception as exc:raise ValueError('不合法XML或外部实体/DTD: '+name) from exc
        return self.xml_cache[name]
    def relationships(self,part):
        name=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels') if part else '_rels/.rels'
        if name not in self.files:return {}
        result={}
        for node in self.xml(name):
            if local(node.tag)!='Relationship':continue
            ident=attr(node,'Id')
            if not ident or ident in result:raise ValueError('OOXML关系身份重复/无效')
            result[ident]={'type':attr(node,'Type',''),'target':attr(node,'Target',''),'external':attr(node,'TargetMode','')=='External'}
        return result
    def target(self,part,rel):
        target=unquote(rel['target']);url=urlsplit(target)
        if rel['external'] or url.scheme or url.netloc or url.query or url.fragment or '\\' in target:raise ValueError('不能跟随外部或不安全OOXML关系')
        target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(posixpath.dirname(part),target))
        if target.startswith('../') or target in {'.','..'} or target not in self.files:raise ValueError('OOXML关系越界或目标缺失')
        return target

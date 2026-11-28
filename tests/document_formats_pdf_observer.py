"""Independent child import hooks: actual readers only accept completed guard output."""
import hashlib,json,os,sys
from pathlib import Path

HOOK=r'''import hashlib,importlib.abc,importlib.machinery,json,os,sys
from pathlib import Path
registered={}
log=Path(os.environ['SMM_008_GUARD_LOG'])
root=Path(os.environ['SMM_008_GUARD_ROOT']).resolve()
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def emit(value):
    with log.open('a',encoding='utf-8') as stream:stream.write(json.dumps({'pid':os.getpid(),**value})+'\n')
def check(value,reader):
    if not isinstance(value,(str,Path)):
        emit({'kind':'rejected','reader':reader,'input_type':type(value).__name__});raise AssertionError('reader bypassed validated private PDF')
    path=Path(value).resolve();entry=registered.get(str(path))
    if not path.is_relative_to(root) or not entry or digest(path)!=entry['sha256']:
        emit({'kind':'rejected','reader':reader,'path':str(path)});raise AssertionError('reader bypassed validated private PDF')
    emit({'kind':'reader','reader':reader,'path':str(path),**entry})
class Loader(importlib.abc.Loader):
    def __init__(self,original,name):self.original=original;self.name=name
    def create_module(self,spec):return self.original.create_module(spec) if hasattr(self.original,'create_module') else None
    def exec_module(self,module):
        self.original.exec_module(module)
        if self.name=='smm_local.document_formats.pdf_guard':
            original=module.intermediate
            def guarded(raw,output,*args,**kwargs):
                result=original(raw,output,*args,**kwargs)
                path=Path(output).resolve()
                if not path.is_relative_to(root):raise AssertionError('guard output is outside the private task')
                entry={'sha256':digest(path),'source_sha256':hashlib.sha256(raw).hexdigest(),'guard_completed':True}
                registered[str(path)]=entry;emit({'kind':'guard','path':str(path),**entry});return result
            module.intermediate=guarded
        elif self.name=='pypdfium2':
            original=module.PdfDocument.__init__
            def init(obj,value,*args,**kwargs):check(value,'pdfium');return original(obj,value,*args,**kwargs)
            module.PdfDocument.__init__=init
        elif self.name=='pdfplumber':
            original=module.PDF.open
            def opened(cls,value,*args,**kwargs):check(value,'pdfplumber');return original(value,*args,**kwargs)
            module.PDF.open=classmethod(opened);module.open=module.PDF.open
class Finder(importlib.abc.MetaPathFinder):
    names={'smm_local.document_formats.pdf_guard','pypdfium2','pdfplumber'}
    def find_spec(self,fullname,path=None,target=None):
        if fullname in self.names:
            spec=importlib.machinery.PathFinder.find_spec(fullname,path)
            if spec and spec.loader:spec.loader=Loader(spec.loader,fullname)
            return spec
sys.meta_path.insert(0,Finder())
'''


def install(root,monkeypatch):
    folder=root/'pdf-reader-observer';folder.mkdir();log=folder/'observations.jsonl'
    (folder/'sitecustomize.py').write_text(HOOK,encoding='utf-8')
    monkeypatch.setenv('SMM_008_GUARD_LOG',str(log));monkeypatch.setenv('SMM_008_GUARD_ROOT',str(root.resolve()))
    monkeypatch.setenv('PYTHONPATH',str(folder)+os.pathsep+os.environ.get('PYTHONPATH',''))
    return log


def records(log):return [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []

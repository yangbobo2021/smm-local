"""Extend the validated-PDF reader observer with actual OCR inputs and output."""
import os
from pathlib import Path
from document_formats_pdf_observer import HOOK,records

OCR_HOOK=r'''
import subprocess
engine=os.path.normcase(os.path.realpath(os.environ['SMM_008_OCR_EXECUTABLE']))
artifacts=Path(os.environ['SMM_008_OCR_OBSERVER_FILES']);artifacts.mkdir(exist_ok=True)
original_popen=subprocess.Popen.__init__;original_run=subprocess.run
counter=0;captures={}
def image_request(argv):
    if not isinstance(argv,(list,tuple)) or len(argv)<2:return None
    if os.path.normcase(os.path.realpath(os.fsdecode(argv[0])))!=engine:return None
    path=Path(argv[1])
    return path if path.is_file() else None
def popen(obj,argv,*args,**kwargs):
    global counter
    image=image_request(argv)
    if image is not None:
        entries=list(registered.values())
        if len(entries)!=1:
            emit({'kind':'ocr-rejected','reason':'no unique completed PDF guard'});raise AssertionError('OCR has no validated PDF source')
        counter+=1;label=str(os.getpid())+'-'+str(counter);raw=image.read_bytes();saved=artifacts/(label+'.png');saved.write_bytes(raw)
        event={'label':label,'kind':'ocr-input','input_name':image.name,'input_sha256':hashlib.sha256(raw).hexdigest(),'file':str(saved),'source_sha256':entries[0]['source_sha256'],'argv':list(map(str,argv))}
        captures[str(image.resolve())]=event;emit(event)
    return original_popen(obj,argv,*args,**kwargs)
def run(argv,*args,**kwargs):
    image=image_request(argv);result=original_run(argv,*args,**kwargs)
    if image is not None:
        event=captures[str(image.resolve())];out=result.stdout.encode('utf-8') if isinstance(result.stdout,str) else result.stdout or b''
        err=result.stderr.encode('utf-8') if isinstance(result.stderr,str) else result.stderr or b''
        (artifacts/(event['label']+'.tsv')).write_bytes(out);(artifacts/(event['label']+'.stderr')).write_bytes(err)
        emit({**event,'kind':'ocr-result','exit_code':result.returncode,'stdout_sha256':hashlib.sha256(out).hexdigest(),'stdout_file':str(artifacts/(event['label']+'.tsv'))})
    return result
subprocess.Popen.__init__=popen;subprocess.run=run
'''


def install(root,monkeypatch):
    folder=root/'mixed-observer';folder.mkdir();log=folder/'events.jsonl';files=folder/'inputs';files.mkdir()
    (folder/'sitecustomize.py').write_text(HOOK+OCR_HOOK,encoding='utf-8')
    monkeypatch.setenv('SMM_008_GUARD_LOG',str(log));monkeypatch.setenv('SMM_008_GUARD_ROOT',str(root.resolve()));monkeypatch.setenv('SMM_008_OCR_OBSERVER_FILES',str(files))
    monkeypatch.setenv('PYTHONPATH',str(folder)+os.pathsep+os.environ.get('PYTHONPATH',''))
    return log,files

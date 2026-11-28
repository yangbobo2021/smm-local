"""Fresh CLI processes may only read saved archive material."""
import os,shutil
from pathlib import Path
from document_formats_platform import utf8_environment

HOOK=r'''
import json,os,sys,socket
from document_formats_platform import internal_socketpair
protected={os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['SMM_008_CLI_SOURCES'])}
forbidden={'pdfplumber','pdfminer','pypdfium2','PIL','defusedxml','psutil'}
def audit(event,args):
    reason=None
    if event=='open' and isinstance(args[0],(str,bytes)) and os.path.normcase(os.path.abspath(os.fsdecode(args[0]))) in protected:reason='source-open'
    if event=='import' and (args[0].split('.')[0] in forbidden or args[0].startswith('smm_local.document_formats')):reason='content-import'
    if event=='subprocess.Popen':reason='spawn'
    if event=='socket.getaddrinfo':reason='network'
    if event=='socket.connect' and not internal_socketpair(sys._getframe(1),args[0],args[1]):reason='network'
    if reason:
        with open(os.environ['SMM_008_CLI_OBSERVER'],'a',encoding='utf-8') as out:out.write(json.dumps({'kind':reason,'event':event,'pid':os.getpid()})+'\n')
        raise AssertionError('CLI read observer forbidden: '+reason)
sys.addaudithook(audit)
'''


def install(root,paths):
    folder=root/'cli-observer';folder.mkdir();log=folder/'events.jsonl'
    shutil.copyfile(Path(__file__).with_name('document_formats_platform.py'),folder/'document_formats_platform.py')
    (folder/'sitecustomize.py').write_text(HOOK,encoding='utf-8')
    env=utf8_environment(os.environ,SMM_008_CLI_SOURCES=__import__('json').dumps(list(map(str,paths))),SMM_008_CLI_OBSERVER=str(log),PYTHONPATH=str(folder)+os.pathsep+os.environ.get('PYTHONPATH',''))
    return env,log

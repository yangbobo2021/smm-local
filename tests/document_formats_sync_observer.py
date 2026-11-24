"""C1 observer: all content processing/spawn/external sockets are forbidden."""
import builtins,socket,subprocess


def install(monkeypatch):
    from smm_local.documents import Documents
    from smm_local.document_snapshots import Snapshots
    attempts=[]
    def forbid(*args,**kwargs):attempts.append('processing-or-external-call');raise AssertionError('receiver attempted processing or external call')
    monkeypatch.setattr(Documents,'_scan',forbid);monkeypatch.setattr(Snapshots,'process',forbid)
    original=builtins.__import__
    def no_readers(name,*args,**kwargs):
        if name.split('.')[0] in {'pdfplumber','pdfminer','pypdfium2','PIL','defusedxml','psutil'}:attempts.append(name);raise AssertionError('receiver imported optional content reader')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',no_readers)
    monkeypatch.setattr(socket.socket,'connect',forbid);monkeypatch.setattr(socket,'create_connection',forbid);monkeypatch.setattr(subprocess,'Popen',forbid)
    return attempts

"""Independent 007 business witnesses; no product imports or file-source reads."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time


def normalized(raw):
    assert isinstance(raw,bytes) and b'\0' not in raw
    return raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_read(actual,raw,start=0,end=None):
    text=normalized(raw);end=len(text) if end is None else end
    assert type(start) is int and type(end) is int and 0<=start<end<=len(text)
    assert actual['text']==text[start:end],('wrong text',actual['text'],text[start:end])
    assert (actual['start'],actual['end'])==(start,end)
    assert actual['start_line']==1+text.count('\n',0,start)
    assert actual['end_line']==1+text.count('\n',0,end-1)


def document_set(actual,expected):
    """Expected entries are independent fixture raw bytes and explicit identities.

    Identity comes from archive creation/ingest receipts; content comes only from
    the fixture that was submitted. All observations are checked, not two product
    endpoints against each other. A provenance/source check is opt-in per target
    because a bundled same-version hit legitimately has multiple exact endpoints.
    """
    def identity(d):
        o=d['origin'];return(o['device_id'],o['archive_id'],o['document_id'],d['version'])
    observed={identity(d):d for d in actual}
    assert len(observed)==len(actual),'duplicate origin/version rows'
    wanted={identity(d):d for d in expected}
    assert len(wanted)==len(expected) and set(observed)==set(wanted),('wrong complete identity set',list(observed),list(wanted))
    for key,w in wanted.items():
        d=observed[key];text=normalized(w['raw'])
        assert d['sha256']==digest(w['raw'])
        assert d['text_sha256']==digest(text.encode('utf-8'))
        assert d['text_length']==len(text)
        if 'project_ids' in w:assert set(d['project_ids'])==set(w['project_ids'])
        if 'source_ids' in w:assert set(d['source_ids'])==set(w['source_ids'])
        if 'qualifications' in w:assert d['qualifications']==w['qualifications']
        exact_read(d,w['raw'],d['start'],d['end'])


def process_alive(pid):
    assert type(pid) is int and pid>0
    if os.name=='nt':
        result=subprocess.run(['tasklist','/FI','PID eq '+str(pid),'/FO','CSV','/NH'],capture_output=True,timeout=15)
        if result.returncode:raise AssertionError('cannot verify actual Windows PID')
        # tasklist emits a quoted numeric PID field, not a localized status name.
        # Native tasklist uses the Windows code page, regardless of Python UTF8.
        # Only the quoted numeric second field is relevant; keep bytes intact.
        return any(len(row)>1 and row[1].strip(b'\"')==str(pid).encode('ascii')
                   for row in (line.split(b',') for line in result.stdout.splitlines()))
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


def stopped(pids,ports):
    for pid in pids:assert not process_alive(pid),('still alive',pid)
    for host,port in ports:
        with socket.socket() as sock:
            sock.settimeout(2)
            assert sock.connect_ex((host,port))!=0,('still listening',host,port)


def selfcheck():
    from copy import deepcopy
    raw_a='\ufeff前言😀e\u0301\r\nneedle 甲\r尾\n'.encode();raw_b='needle 独立乙\n第二行😀'.encode()
    expected=[];actual=[]
    for i,raw in enumerate([raw_a,raw_b],1):
        origin={'device_id':str(i)*32,'archive_id':str(i+2)*32,'document_id':str(i+4)*32}
        text=normalized(raw);item={'origin':origin,'version':i,'raw':raw,'project_ids':[i],'source_ids':[str(i+6)*32],'qualifications':[{'source_id':str(i+6)*32,'revision':1,'qualification':i}]}
        expected.append(item)
        actual.append({k:v for k,v in item.items() if k!='raw'}|{'text':text,'start':0,'end':len(text),'start_line':1,'end_line':1+text.count('\n',0,len(text)-1),'sha256':digest(raw),'text_sha256':digest(text.encode()),'text_length':len(text)})
    outcomes=[]
    def accept(name,fn):fn();outcomes.append({'check':name,'expected':'accept','actual':'accept'})
    def reject(name,fn):
        try:fn()
        except AssertionError:outcomes.append({'check':name,'expected':'reject','actual':'reject'});return
        raise AssertionError('bad witness unexpectedly accepted: '+name)
    accept('two independent originals',lambda:document_set(actual,expected))
    for i in range(2):
        for key,value in [('text','wrong'),('start',1),('end',1),('start_line',2),('end_line',999),('version',99),('sha256','f'*64),('text_sha256','e'*64),('source_ids',[]),('project_ids',[]),('qualifications',[])]:
            bad=deepcopy(actual);bad[i][key]=value;reject(f'target {i} corrupt {key}',lambda bad=bad:document_set(bad,expected))
        bad=deepcopy(actual);bad[i]['origin']['document_id']='f'*32;reject(f'target {i} wrong document',lambda bad=bad:document_set(bad,expected))
    reject('missing target',lambda:document_set(actual[:1],expected))
    reject('duplicate target',lambda:document_set(actual+actual[:1],expected))
    # An actual live child and live listener exercise process/port checks.
    child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen();port=sock.getsockname()[1]
    try:
        reject('real live child PID',lambda:stopped([child.pid],[]))
        reject('real live port',lambda:stopped([],[('127.0.0.1',port)]))
    finally:
        child.terminate();child.wait(timeout=10);sock.close()
    accept('real terminated PID and closed port',lambda:stopped([child.pid],[('127.0.0.1',port)]))
    return {'status':'passed','pid':os.getpid(),'platform':sys.platform,'checks':outcomes}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--selfcheck',action='store_true',required=True);p.parse_args()
    print(json.dumps(selfcheck(),ensure_ascii=False,indent=2))

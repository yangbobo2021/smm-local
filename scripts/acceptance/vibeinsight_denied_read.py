# SPDX-License-Identifier: Apache-2.0
"""Check actual credential access with a principal/token outside its allowed ACL."""
import argparse
import ctypes
import errno
import json
import os
from pathlib import Path


def denied(path):
    try:
        with Path(path).open('rb') as stream: stream.read(1)
    except PermissionError as exc:
        return {'attempted':True,'denied':True,'errno':exc.errno,'uid':os.geteuid() if os.name!='nt' else None}
    raise AssertionError('non-authorized principal could read credential')


def windows_denied(path):
    # A separate temporary normal account, not a reduced token of the authorized maintainer.
    from ctypes import wintypes as w
    import secrets
    import subprocess
    net=ctypes.WinDLL('netapi32',use_last_error=True)
    adv=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    class User(ctypes.Structure):
        _fields_=[('name',w.LPWSTR),('password',w.LPWSTR),('age',w.DWORD),('privilege',w.DWORD),
                  ('home',w.LPWSTR),('comment',w.LPWSTR),('flags',w.DWORD),('script',w.LPWSTR)]
    name='SmmProbe'+secrets.token_hex(4)
    password=secrets.token_urlsafe(28)+'1!aA'
    info=User(name,password,0,1,None,'Disposable SMM credential access probe',0x10000|1,None)
    error=w.DWORD()
    net.NetUserAdd.argtypes=[w.LPCWSTR,w.DWORD,ctypes.c_void_p,ctypes.POINTER(w.DWORD)]
    net.NetUserDel.argtypes=[w.LPCWSTR,w.LPCWSTR]
    status=net.NetUserAdd(None,1,ctypes.byref(info),ctypes.byref(error))
    assert status==0,('could not create task test principal',status)
    token=w.HANDLE()
    try:
        group=subprocess.run(['powershell','-NoProfile','-Command',
            "Add-LocalGroupMember -SID S-1-5-32-545 -Member '"+name+"'"],capture_output=True)
        assert group.returncode==0,'could not add task principal to normal Users group'
        adv.LogonUserW.argtypes=[w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,w.DWORD,w.DWORD,ctypes.POINTER(w.HANDLE)]
        assert adv.LogonUserW(name,'.',password,2,0,ctypes.byref(token)),ctypes.get_last_error()
        adv.ImpersonateLoggedOnUser.argtypes=[w.HANDLE]
        assert adv.ImpersonateLoggedOnUser(token),ctypes.get_last_error()
        result=denied(path)
        result['principal']='task-owned temporary normal user'
        return result
    finally:
        adv.RevertToSelf()
        kernel.CloseHandle.argtypes=[w.HANDLE]
        if token:kernel.CloseHandle(token)
        assert net.NetUserDel(None,name)==0,'could not delete task-owned test principal'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('credential',type=Path);p.add_argument('--owner-uid',type=int)
    a=p.parse_args()
    if os.name=='nt': result=windows_denied(a.credential)
    else:
        assert a.owner_uid is not None and os.geteuid()!=a.owner_uid,'must run under a different principal'
        result=denied(a.credential)
        assert result['errno'] in (errno.EACCES,errno.EPERM)
    print(json.dumps(result))


if __name__=='__main__':main()

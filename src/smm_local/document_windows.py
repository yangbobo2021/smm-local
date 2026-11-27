"""Windows worker creation and exit proof using kernel-owned handles only.

Workers enter the private kill-on-close Job atomically at CreateProcess; no
redirector or parser can run outside it. This module has no parser dependencies.
"""
from __future__ import annotations
import os
import subprocess
import sys


def kernel():
    import ctypes as c
    from ctypes import wintypes as w
    k=c.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CloseHandle':([w.HANDLE],w.BOOL),
        'GetCurrentProcess':([],w.HANDLE),
        'GetProcessTimes':([w.HANDLE,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p],w.BOOL),
        'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
        'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
        'GetExitCodeProcess':([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),
        'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
    }
    for name,(args,result) in signatures.items():
        f=getattr(k,name);f.argtypes=args;f.restype=result
    return k


def creation_ticks(handle):
    import ctypes as c
    values=[c.c_ulonglong() for _ in range(4)]
    if not kernel().GetProcessTimes(handle,*[c.byref(v) for v in values]):raise c.WinError(c.get_last_error())
    return values[0].value


def identity_exited(pid,ticks):
    """False includes access denied/unknown. Never signal an unverified PID."""
    import ctypes as c
    k=kernel();h=k.OpenProcess(0x100000|0x1000,False,pid)
    if not h:return c.get_last_error()==87 # ERROR_INVALID_PARAMETER: no PID
    try:
        if creation_ticks(h)!=ticks:return True # That exact identity ended.
        return k.WaitForSingleObject(h,0)==0
    except OSError:return False
    finally:k.CloseHandle(h)


class Child:
    def __init__(self,handle,pid,args,stdin):
        self._handle=handle;self.pid=pid;self.args=args;self.stdin=stdin;self.returncode=None
    def poll(self):
        import ctypes as c
        from ctypes import wintypes as w
        if self.returncode is None and kernel().WaitForSingleObject(self._handle,0)==0:
            code=w.DWORD()
            if not kernel().GetExitCodeProcess(self._handle,c.byref(code)):raise c.WinError(c.get_last_error())
            self.returncode=code.value
        return self.returncode
    def wait(self,timeout=None):
        result=kernel().WaitForSingleObject(self._handle,0xffffffff if timeout is None else max(0,int(timeout*1000)))
        if result==258:raise subprocess.TimeoutExpired(self.args,timeout)
        if result!=0:
            import ctypes as c
            raise c.WinError(c.get_last_error())
        return self.poll()
    def kill(self):
        if self.poll() is None and not kernel().TerminateProcess(self._handle,1):
            import ctypes as c
            raise c.WinError(c.get_last_error())
    def close(self):
        if self.stdin is not None and not self.stdin.closed:self.stdin.close()
        if self._handle:kernel().CloseHandle(self._handle);self._handle=None


def spawn(job,args,*,stdout,stderr,cwd):
    """Create a gated child in the Job before its first user instruction."""
    import ctypes as c
    from ctypes import wintypes as w
    import msvcrt
    k=kernel()
    class SECURITY(c.Structure):_fields_=[('size',w.DWORD),('descriptor',c.c_void_p),('inherit',w.BOOL)]
    class STARTUP(c.Structure):
        _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
            *[(name,w.DWORD) for name in ('x','y','xsize','ysize','xchars','ychars','fill','flags')],
            ('show',w.WORD),('reserved_size',w.WORD),('reserved_bytes',c.c_void_p),
            ('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
    class STARTUP_EX(c.Structure):_fields_=[('startup',STARTUP),('attributes',c.c_void_p)]
    class INFO(c.Structure):_fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
    signatures={
      'CreatePipe':([c.POINTER(w.HANDLE),c.POINTER(w.HANDLE),c.POINTER(SECURITY),w.DWORD],w.BOOL),
      'SetHandleInformation':([w.HANDLE,w.DWORD,w.DWORD],w.BOOL),
      'DuplicateHandle':([w.HANDLE,w.HANDLE,w.HANDLE,c.POINTER(w.HANDLE),w.DWORD,w.BOOL,w.DWORD],w.BOOL),
      'InitializeProcThreadAttributeList':([c.c_void_p,w.DWORD,w.DWORD,c.POINTER(c.c_size_t)],w.BOOL),
      'UpdateProcThreadAttribute':([c.c_void_p,w.DWORD,c.c_size_t,c.c_void_p,c.c_size_t,c.c_void_p,c.c_void_p],w.BOOL),
      'DeleteProcThreadAttributeList':([c.c_void_p],None),
      'CreateProcessW':([w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(STARTUP_EX),c.POINTER(INFO)],w.BOOL),
    }
    for name,(a,r) in signatures.items():f=getattr(k,name);f.argtypes=a;f.restype=r
    def check(value):
        if not value:raise c.WinError(c.get_last_error())
        return value
    handles=[];attributes=None;initialized=False;write=None;info=INFO()
    try:
        read=w.HANDLE();write=w.HANDLE();sa=SECURITY(c.sizeof(SECURITY),None,True)
        check(k.CreatePipe(c.byref(read),c.byref(write),c.byref(sa),0));handles.extend([read.value,write.value])
        check(k.SetHandleInformation(write,1,0))
        inherited=[read.value]
        for stream in (stdout,stderr):
            duplicate=w.HANDLE();current=k.GetCurrentProcess()
            check(k.DuplicateHandle(current,w.HANDLE(msvcrt.get_osfhandle(stream.fileno())),current,c.byref(duplicate),0,True,2))
            handles.append(duplicate.value);inherited.append(duplicate.value)
        size=c.c_size_t();k.InitializeProcThreadAttributeList(None,2,0,c.byref(size))
        attributes=c.create_string_buffer(size.value)
        check(k.InitializeProcThreadAttributeList(attributes,2,0,c.byref(size)));initialized=True
        inherited_array=(w.HANDLE*3)(*inherited);job_array=(w.HANDLE*1)(job.handle)
        check(k.UpdateProcThreadAttribute(attributes,0,0x20002,inherited_array,c.sizeof(inherited_array),None,None))
        check(k.UpdateProcThreadAttribute(attributes,0,0x2000d,job_array,c.sizeof(job_array),None,None))
        startup=STARTUP_EX();startup.startup.cb=c.sizeof(startup);startup.startup.flags=0x100
        startup.startup.stdin, startup.startup.stdout,startup.startup.stderr=inherited
        startup.attributes=c.cast(attributes,c.c_void_p)
        command=subprocess.list2cmdline(args)
        sys.audit('subprocess.Popen',None,command,str(cwd),None)
        check(k.CreateProcessW(None,c.create_unicode_buffer(command),None,None,True,0x80000,None,str(cwd),c.byref(startup),c.byref(info)))
        k.CloseHandle(info.thread)
        fd=msvcrt.open_osfhandle(write.value,os.O_WRONLY|os.O_BINARY);handles.remove(write.value)
        child=Child(info.process,info.pid,args,os.fdopen(fd,'wb'));info.process=None
        return child
    except BaseException:
        if info.process:
            k.TerminateProcess(info.process,1);k.WaitForSingleObject(info.process,3000);k.CloseHandle(info.process)
        raise
    finally:
        if initialized:k.DeleteProcThreadAttributeList(attributes)
        for h in handles:k.CloseHandle(h)

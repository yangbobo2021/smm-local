"""Identical stdlib-only audit primitives injected into private E/X hooks."""
import inspect


def actual_identity():
    import ctypes
    import os
    import sys
    value = {'pid': os.getpid(), 'platform': sys.platform}
    if os.name != 'nt':
        value.update(uid=os.getuid(), gid=os.getgid(), euid=os.geteuid(), egid=os.getegid())
        return value
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    advapi.OpenProcessToken.restype = w.BOOL
    advapi.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
    advapi.GetTokenInformation.restype = w.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)]
    advapi.ConvertSidToStringSidW.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.ProcessIdToSessionId.argtypes = [w.DWORD, ctypes.POINTER(w.DWORD)]
    kernel.ProcessIdToSessionId.restype = w.BOOL
    session = w.DWORD()
    assert kernel.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
    token = w.HANDLE()
    assert advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token))
    try:
        size = w.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        assert advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size))
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        text = w.LPWSTR()
        assert advapi.ConvertSidToStringSidW(sid, ctypes.byref(text))
        try:
            value['sid'] = text.value
        finally:
            kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)
    value.update(session_id=session.value, is_admin=bool(ctypes.windll.shell32.IsUserAnAdmin()))
    return value


IDENTITY_SOURCE = inspect.getsource(actual_identity)

AUDIT_PRIMITIVES = r'''
import ctypes,os,socket,sys,subprocess
PROCESS_EVENTS={'subprocess.Popen','os.system','os.posix_spawn','os.spawn','os.exec','os.fork','os.forkpty','os.startfile','os.startfile/2','_winapi.CreateProcess'}
NETWORK_EVENTS={'socket.connect','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','socket.getnameinfo','socket.sendto','socket.sendmsg'}
def native_argv(value):
 if isinstance(value,(list,tuple)):return [os.fsdecode(item) for item in value]
 if not isinstance(value,str) or os.name!='nt':return None
 from ctypes import wintypes as w
 shell=ctypes.WinDLL('shell32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 shell.CommandLineToArgvW.argtypes=[w.LPCWSTR,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(w.LPWSTR)
 kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
 count=ctypes.c_int();items=shell.CommandLineToArgvW(value,ctypes.byref(count))
 if not items:raise ctypes.WinError(ctypes.get_last_error())
 try:return [items[index] for index in range(count.value)]
 finally:kernel.LocalFree(ctypes.cast(items,ctypes.c_void_p))
def same_image(a,b):
 return os.path.normcase(os.path.realpath(os.path.abspath(os.fsdecode(a))))==os.path.normcase(os.path.realpath(os.path.abspath(os.fsdecode(b))))
def effective_process_arguments(event,args,frame):
 # CPython 3.14.10 Windows emits a corrupt command_line in the native audit
 # event (PyObject* passed with a wide-string format). Only the immediate,
 # canonical stdlib Popen frame may supply its actual invocation arguments.
 # Calls to the private API from any other frame keep their original values
 # and cannot acquire the MCP exception.
 if event=='_winapi.CreateProcess':
  method=subprocess.Popen._execute_child
  if frame.f_code is not method.__code__ or frame.f_globals is not subprocess.__dict__:return None,'untrusted-native-caller'
  return (frame.f_locals.get('executable'),frame.f_locals.get('args')),'stdlib-popen-callframe'
 return args,'audit-event'
def exact_child_command(event,args,expected):
 if args is None or event not in {'subprocess.Popen','os.posix_spawn','_winapi.CreateProcess'} or len(args)<2:return False
 actual=native_argv(args[1])
 if not actual or not expected or len(actual)!=len(expected):return False
 if not os.path.isabs(actual[0]) or not same_image(actual[0],expected[0]) or actual[1:]!=expected[1:]:return False
 # Windows Popen/CreateProcess may leave the explicit application unset; the
 # completely checked absolute first command-line argument then selects it.
 return args[0] in (None,'') or same_image(args[0],expected[0])
def internal_socketpair(frame,channel,address):
 codes={getattr(getattr(socket,name,None),'__code__',None) for name in ('socketpair','_fallback_socketpair')}-{None}
 if frame.f_code not in codes or frame.f_globals is not socket.__dict__:return False
 listener=frame.f_locals.get('lsock')
 return (channel is frame.f_locals.get('csock') and listener is not None
  and channel.family==listener.family and channel.family in (socket.AF_INET,socket.AF_INET6)
  and isinstance(address,tuple) and len(address)>=2 and address[0] in {'127.0.0.1','::1'}
  and address[:2]==listener.getsockname()[:2])
def accepted_server_reply(channel,address,listeners):
 if address is not None or channel.family not in (socket.AF_INET,socket.AF_INET6) or channel.type & socket.SOCK_STREAM!=socket.SOCK_STREAM:return False
 try:local=channel.getsockname();peer=channel.getpeername()
 except OSError:return False
 return (tuple(local[:2]) in listeners and peer[0] in {'127.0.0.1','::1'})
def network_decision(event,args,frame,endpoints,listeners=set()):
 if event in {'socket.connect','socket.sendto','socket.sendmsg'}:
  address=args[1];internal=event=='socket.connect' and internal_socketpair(frame,args[0],address)
  endpoint=tuple(address[:2]) if isinstance(address,tuple) and len(address)>=2 else None
  reply=event in {'socket.sendto','socket.sendmsg'} and accepted_server_reply(args[0],address,listeners)
  return internal or endpoint in endpoints or reply,internal,False,address,reply
 if event=='socket.getaddrinfo':
  address=args[:2]
  try:endpoint=(address[0],int(address[1]))
  except (TypeError,ValueError):endpoint=None
  return endpoint in endpoints,False,False,address,False
 # HTTPServer and OS socket setup can ask for the constant loopback name.
 # No arbitrary name/address or payload is allowed through this exception.
 address=args[0]
 host=address[0] if event=='socket.getnameinfo' and isinstance(address,tuple) else address
 local=host in {'127.0.0.1','::1','localhost'}
 return local,False,local,address,False
'''

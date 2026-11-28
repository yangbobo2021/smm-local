"""Stable role permissions for new managed Windows Hub snapshot directories.

Python 3.13+ mkdir(0700) uses OWNER RIGHTS, which follows each file's
creator. An administrator capture must instead remain readable by LocalService.
Existing ACLs are never rewritten or recursively propagated.
"""
from __future__ import annotations
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
import sys

# Only the already configured Windows service archive opts into this factory.
# Local archives and unconfigured foreground Hubs retain their private policy.
def configure(db):
    if sys.platform != 'win32' or db.db_path.name != 'smm-hub.sqlite3':
        return
    state = db.db_path.resolve().parent
    profile = state / 'hub.json'
    if not profile.is_file() or profile.is_symlink():
        return
    config = json.loads(profile.read_text(encoding='utf-8'))
    if (not isinstance(config, dict) or not {'address', 'bind', 'port', 'enabled'} <= config.keys()
            or type(config['enabled']) is not bool):
        raise ValueError('Windows Hub 服务配置无效')
    import ctypes
    from ._archive import document_execution_identity
    if (not ctypes.windll.shell32.IsUserAnAdmin()
            and document_execution_identity()['sid'] != 'S-1-5-19'):
        raise ValueError('Windows受管Hub快照只允许管理员或服务账户管理')
    db._document_snapshot_directory = Directories(state).create


class Directories:
    def __init__(self, state):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.state = Path(state)
        self.root = self.state / '.document-snapshots'
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.a = c.WinDLL('advapi32', use_last_error=True)
        class Info(c.Structure):
            _fields_ = [('attributes', w.DWORD), ('created', w.FILETIME), ('accessed', w.FILETIME),
                ('written', w.FILETIME), ('volume', w.DWORD), ('size_high', w.DWORD),
                ('size_low', w.DWORD), ('links', w.DWORD), ('index_high', w.DWORD), ('index_low', w.DWORD)]
        class Acl(c.Structure):
            _fields_ = [('revision', w.BYTE), ('reserved', w.BYTE), ('size', w.WORD),
                ('count', w.WORD), ('reserved2', w.WORD)]
        class Unicode(c.Structure):
            _fields_ = [('length', w.USHORT), ('maximum', w.USHORT), ('buffer', w.LPWSTR)]
        class Attributes(c.Structure):
            _fields_ = [('length', w.ULONG), ('root', w.HANDLE), ('name', c.POINTER(Unicode)),
                ('flags', w.ULONG), ('security', c.c_void_p), ('qos', c.c_void_p)]
        class Status(c.Structure):
            _fields_ = [('status_or_pointer', c.c_void_p), ('information', c.c_size_t)]
        self.Info, self.Acl = Info, Acl
        self.Unicode, self.Attributes, self.Status = Unicode, Attributes, Status
        self.nt = c.WinDLL('ntdll', use_last_error=True)
        self.nt.NtCreateFile.argtypes = [c.POINTER(w.HANDLE), w.ULONG, c.POINTER(Attributes),
            c.POINTER(Status), c.c_void_p, w.ULONG, w.ULONG, w.ULONG, w.ULONG, c.c_void_p, w.ULONG]
        self.nt.NtCreateFile.restype = w.LONG
        self.nt.RtlNtStatusToDosError.argtypes = [w.LONG]
        self.nt.RtlNtStatusToDosError.restype = w.ULONG
        signatures = {
            'GetFileInformationByHandle': ([w.HANDLE, c.POINTER(Info)], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'LocalFree': ([c.c_void_p], c.c_void_p),
        }
        for name, (args, result) in signatures.items():
            f = getattr(self.k, name); f.argtypes = args; f.restype = result
        signatures = {
            'ConvertStringSecurityDescriptorToSecurityDescriptorW': ([w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p], w.BOOL),
            'GetSecurityInfo': ([w.HANDLE, w.DWORD, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p,
                c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p)], w.DWORD),
            'GetAce': ([c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)], w.BOOL),
            'ConvertSidToStringSidW': ([c.c_void_p, c.POINTER(w.LPWSTR)], w.BOOL),
            'ConvertStringSidToSidW': ([w.LPCWSTR, c.POINTER(c.c_void_p)], w.BOOL),
            'SetSecurityInfo': ([w.HANDLE, w.DWORD, w.DWORD, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p], w.DWORD),
        }
        for name, (args, result) in signatures.items():
            f = getattr(self.a, name); f.argtypes = args; f.restype = result

    def _sid(self, value):
        c, w = self.c, self.w
        text = w.LPWSTR()
        if not self.a.ConvertSidToStringSidW(value, c.byref(text)):
            raise c.WinError(c.get_last_error())
        try:
            return text.value
        finally:
            self.k.LocalFree(c.cast(text, c.c_void_p))

    @contextmanager
    def _open(self, name, *, parent=None, descriptor=None, claim=False):
        c, w = self.c, self.w
        if parent is None:
            name = str(Path(name))
            # Root is already canonicalized by Hub; native child names below
            # are single components resolved relative to its pinned handle.
            name = ('\\??\\UNC\\' + name[2:]) if name.startswith('\\\\') else '\\??\\' + name
        elif not name or any(ch in name for ch in ('/', '\\', ':')) or name in {'.', '..'}:
            raise ValueError('Hub快照目录名称无效')
        raw = name.encode('utf-16le')
        if len(raw) > 65532:
            raise ValueError('Hub快照目录路径过长')
        buffer = c.create_unicode_buffer(name)
        text = self.Unicode(len(raw), len(raw) + 2, c.cast(buffer, w.LPWSTR))
        attributes = self.Attributes(c.sizeof(self.Attributes), parent, c.pointer(text), 0x40, descriptor, None)
        handle, status = w.HANDLE(), self.Status()
        # FILE_LIST_DIRECTORY counts as real read access for delete sharing.
        # No parent-directory listing privilege is required outside this root.
        access = 0x120081 | (0x80000 if claim else 0)
        result = self.nt.NtCreateFile(c.byref(handle), access, c.byref(attributes), c.byref(status),
            None, 0x10, 3, 3 if descriptor is not None else 1, 0x200021, None, 0)
        if result < 0:
            raise c.WinError(self.nt.RtlNtStatusToDosError(result))
        try:
            info = self.Info()
            if not self.k.GetFileInformationByHandle(handle, c.byref(info)):
                raise c.WinError(c.get_last_error())
            if not info.attributes & 0x10 or info.attributes & 0x400:
                raise ValueError('Hub快照目录不能经过链接、junction或非目录')
            yield handle
        finally:
            self.k.CloseHandle(handle)

    def _pin(self, path):
        return self._open(path)

    def claim_owner(self):
        # Explicit administrator setup/enable only, handle-bound owner update.
        # No DACL flag, no recursive call, no pathname-based privileged write.
        c = self.c
        if not c.windll.shell32.IsUserAnAdmin():
            raise ValueError('设置Hub服务根所有者需要管理员权限')
        sid = c.c_void_p()
        if not self.a.ConvertStringSidToSidW('S-1-5-32-544', c.byref(sid)):
            raise c.WinError(c.get_last_error())
        try:
            with self._open(self.state, claim=True) as handle:
                error = self.a.SetSecurityInfo(handle, 1, 1, sid, None, None, None)
                if error:
                    raise c.WinError(error)
        finally:
            self.k.LocalFree(sid)

    def _check(self, handle, *, state=False):
        c, w = self.c, self.w
        sd, acl, owner = c.c_void_p(), c.c_void_p(), c.c_void_p()
        error = self.a.GetSecurityInfo(handle, 1, 5, c.byref(owner), None, c.byref(acl), None, c.byref(sd))
        if error:
            raise c.WinError(error)
        try:
            if not acl.value:
                raise ValueError('Hub快照存储缺少受限目录权限')
            allowed = {'S-1-5-18': 0x1f01ff, 'S-1-5-32-544': 0x1f01ff, 'S-1-5-19': 0x1301bf}
            if state and self._sid(owner) not in allowed:
                raise ValueError('Hub数据根所有者不符合服务隔离要求；请由管理员运行 hub enable')
            found = set()
            for index in range(c.cast(acl, c.POINTER(self.Acl)).contents.count):
                ace = c.c_void_p()
                if not self.a.GetAce(acl, index, c.byref(ace)):
                    raise c.WinError(c.get_last_error())
                kind, flags = (c.c_ubyte * 2).from_address(ace.value)
                if kind != 0:
                    raise ValueError('Hub快照目录权限包含不受支持的访问规则')
                mask = w.DWORD.from_address(ace.value + 4).value
                value = self._sid(c.c_void_p(ace.value + 8))
                # Legacy root OWNER RIGHTS is retained; it never substitutes
                # for the explicit service SID required on storage directories.
                if state and value == 'S-1-3-4':
                    continue
                if value not in allowed or flags & 8 or flags & 3 != 3 or mask & allowed[value] != allowed[value]:
                    raise ValueError('Hub快照目录权限不符合服务账户隔离要求；请检查独立Hub数据目录')
                found.add(value)
            if found != set(allowed):
                raise ValueError('Hub快照目录缺少固定服务账户权限；已有目录不会自动修改权限')
        finally:
            if sd.value:
                self.k.LocalFree(sd)

    def create(self, path):
        path = Path(path)
        relative = path.relative_to(self.root)
        if any(part in {'.', '..'} for part in relative.parts):
            raise ValueError('Hub快照目录越界')
        c = self.c
        sd = c.c_void_p()
        if not self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1301bf;;;LS)', 1, c.byref(sd), None):
            raise c.WinError(c.get_last_error())
        try:
            with ExitStack() as stack:
                handle = stack.enter_context(self._pin(self.state))
                self._check(handle, state=True)
                for part in ['.document-snapshots', *relative.parts]:
                    handle = stack.enter_context(self._open(part, parent=handle, descriptor=sd))
                    self._check(handle)
            return path
        finally:
            self.k.LocalFree(sd)

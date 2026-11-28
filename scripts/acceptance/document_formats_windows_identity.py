"""Read an actual Windows process token without changing its permissions."""
from __future__ import annotations


def process_token(pid):
    import ctypes as c
    from ctypes import wintypes as w
    kernel = c.WinDLL('kernel32', use_last_error=True)
    advapi = c.WinDLL('advapi32', use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.LocalFree.argtypes = [c.c_void_p]
    kernel.ProcessIdToSessionId.argtypes = [w.DWORD, c.POINTER(w.DWORD)]
    kernel.GetProcessTimes.argtypes = [w.HANDLE, c.POINTER(w.FILETIME), c.POINTER(w.FILETIME), c.POINTER(w.FILETIME), c.POINTER(w.FILETIME)]
    advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    advapi.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]
    process = kernel.OpenProcess(0x1000, False, pid)
    if not process:raise c.WinError(c.get_last_error())
    token = w.HANDLE()
    try:
        creation, exited, system, user = (w.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(process, c.byref(creation), c.byref(exited), c.byref(system), c.byref(user)):
            raise c.WinError(c.get_last_error())
        ticks = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
        if not advapi.OpenProcessToken(process, 8, c.byref(token)):raise c.WinError(c.get_last_error())
        needed = w.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, c.byref(needed))
        if not needed.value:raise c.WinError(c.get_last_error())
        buffer = c.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token, 1, buffer, needed.value, c.byref(needed)):raise c.WinError(c.get_last_error())
        sid = c.cast(buffer, c.POINTER(c.c_void_p)).contents
        text = w.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, c.byref(text)):raise c.WinError(c.get_last_error())
        try:actual_sid = text.value
        finally:kernel.LocalFree(c.cast(text, c.c_void_p))
        session = w.DWORD()
        if not kernel.ProcessIdToSessionId(pid, c.byref(session)):raise c.WinError(c.get_last_error())
        return {'pid': pid, 'sid': actual_sid, 'session_id': session.value,
                'creation_filetime': ticks, 'created': ticks / 10000000 - 11644473600}
    finally:
        if token.value:kernel.CloseHandle(token)
        kernel.CloseHandle(process)


def sample_process(process):
    """Bind a token sample to the live process observed before and after it."""
    before = (process.pid, process.create_time(), process.exe(), process.cmdline(), process.ppid())
    token = process_token(process.pid)
    after = (process.pid, process.create_time(), process.exe(), process.cmdline(), process.ppid())
    assert before == after and process.is_running(), 'process identity changed during token sampling'
    assert token['pid'] == before[0] and abs(token['created'] - before[1]) < .001
    return {**token, 'kernel_created': token['created'], 'created': before[1],
            'executable': before[2], 'argv': before[3], 'parent_pid': before[4]}


def validate_chain(ocr, worker, service, *, sid, session, attempt_id, ancestors):
    """Validate the three sampled OS identities and the actual worker command."""
    assert all(sample['sid'] == sid and sample['session_id'] == session for sample in (ocr, worker, service))
    assert ocr['parent_pid'] == worker['pid'] and service['pid'] in ancestors
    assert 'smm_hub._archive.document_worker' in worker['argv']
    assert worker['argv'][worker['argv'].index('--task-token') + 1] == attempt_id


def validate_worker_enrollment(executing, registered, controller, state, *, sid, session,
        attempt_id, module, declared_python, base_python):
    """Bind the real interpreter to its atomically enrolled venv redirector."""
    import os
    assert state['token'] == attempt_id and state['windows_job']['atomic'] is True
    assert state['worker'] == {'pid': registered['pid'], 'created': registered['created']}
    assert state['controller'] == {'pid': controller['pid'], 'created': controller['created']}
    assert registered['parent_pid'] == controller['pid']
    assert controller['sid'] == sid and controller['session_id'] == session
    assert state['windows_job']['worker_ticks'] == registered['creation_filetime']
    assert state['windows_job']['controller_ticks'] == controller['creation_filetime']
    tail = ['-B', '-m', module, '--task-token', attempt_id]
    for sample in (executing, registered):
        assert sample['sid'] == sid and sample['session_id'] == session
        assert sample['argv'][1:] == tail
        assert os.path.samefile(sample['argv'][0], declared_python)
        assert {'pid': sample['pid'], 'created': sample['created']} in state['children']
    assert os.path.samefile(registered['executable'], declared_python)
    if executing['pid'] != registered['pid']:
        assert executing['parent_pid'] == registered['pid']
        assert executing['created'] >= registered['created']
        assert os.path.samefile(executing['executable'], base_python)
    else:
        assert executing['creation_filetime'] == registered['creation_filetime']
        assert os.path.samefile(executing['executable'], registered['executable'])

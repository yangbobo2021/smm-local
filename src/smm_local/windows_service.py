# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""The Windows Service Control Manager interface for the hub process."""

from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import threading

advapi = ct.WinDLL("advapi32", use_last_error=True)
MAIN = ct.WINFUNCTYPE(None, wt.DWORD, ct.POINTER(wt.LPWSTR))
HANDLER = ct.WINFUNCTYPE(wt.DWORD, wt.DWORD, wt.DWORD, wt.LPVOID, wt.LPVOID)


class Status(ct.Structure):
    _fields_ = [(name, wt.DWORD) for name in
                ("kind", "state", "accepts", "exit", "specific", "checkpoint", "wait_hint")]


class Entry(ct.Structure):
    _fields_ = [("name", wt.LPWSTR), ("main", MAIN)]


def bind(name, result, *arguments):
    function = getattr(advapi, name)
    function.restype = result
    function.argtypes = arguments
    return function


start_dispatcher = bind("StartServiceCtrlDispatcherW", wt.BOOL, ct.POINTER(Entry))
register_handler = bind("RegisterServiceCtrlHandlerExW", wt.HANDLE, wt.LPCWSTR, HANDLER, wt.LPVOID)
set_status = bind("SetServiceStatus", wt.BOOL, wt.HANDLE, ct.POINTER(Status))
open_manager = bind("OpenSCManagerW", wt.HANDLE, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD)
open_service = bind("OpenServiceW", wt.HANDLE, wt.HANDLE, wt.LPCWSTR, wt.DWORD)
query_status = bind("QueryServiceStatus", wt.BOOL, wt.HANDLE, ct.POINTER(Status))
close = bind("CloseServiceHandle", wt.BOOL, wt.HANDLE)


def service_state(name):
    manager = open_manager(None, None, 1)
    if not manager:
        raise ct.WinError(ct.get_last_error())
    try:
        service = open_service(manager, name, 4)
        if not service:
            raise ct.WinError(ct.get_last_error())
        try:
            status = Status()
            if not query_status(service, ct.byref(status)):
                raise ct.WinError(ct.get_last_error())
            return status.state
        finally:
            close(service)
    finally:
        close(manager)


def serve(name, create_server):
    handle = None
    server = None
    stopping = threading.Event()
    errors = []

    def report(state, error=0):
        pending = state in (2, 3)
        status = Status(0x10, state, 5 if state == 4 else 0, error, 0,
                        int(pending), 120000 if state == 2 else 30000 if state == 3 else 0)
        if not set_status(handle, ct.byref(status)):
            raise ct.WinError(ct.get_last_error())

    @HANDLER
    def handle_control(control, _event, _data, _context):
        if control in (1, 5):
            stopping.set()
            report(3)
            if server is not None:
                server.should_exit = True
        return 0

    @MAIN
    def main(_count, _values):
        nonlocal handle, server
        handle = register_handler(name, handle_control, None)
        if not handle:
            errors.append(ct.WinError(ct.get_last_error()))
            return
        try:
            report(2)
            server = create_server()
            if not stopping.is_set():
                report(4)
                server.run()
                if not server.started and not stopping.is_set():
                    raise RuntimeError("Windows 汇总服务未能启动")
        except BaseException as exc:
            errors.append(exc)
        finally:
            report(1, 1067 if errors else 0)

    table = (Entry * 2)(Entry(name, main), Entry(None, MAIN()))
    if not start_dispatcher(table):
        raise ct.WinError(ct.get_last_error())
    if errors:
        raise RuntimeError("Windows 汇总服务退出") from errors[0]


def boot():
    """Connect to the SCM before importing the web stack."""
    import sys

    name, root = sys.argv[1:]

    def create_server():
        from pathlib import Path
        from site import addsitedir

        addsitedir(sys.path[0])
        from .hub_admin import Hub

        return Hub(Path(root)).server()

    from contextlib import redirect_stderr, redirect_stdout
    from pathlib import Path

    with (Path(root) / "hub.log").open("a", encoding="utf-8", buffering=1) as log:
        with redirect_stdout(log), redirect_stderr(log):
            try:
                serve(name, create_server)
            except BaseException:
                import traceback

                traceback.print_exc()
                raise

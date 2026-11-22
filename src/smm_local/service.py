# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Discover and control the local sync service for one archive."""

from __future__ import annotations

import base64
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode, urlsplit
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from .core import Archive
from .support import NoRedirect, _service_lock


Action = Literal["status", "open", "sync", "pause", "resume"]
DEFAULT_PORT = 8766
STARTUP_TIMEOUT = 30 if os.name == "nt" else 8


LOCAL_HTTP = build_opener(ProxyHandler({}), NoRedirect())


def _service_file(db: Archive) -> Path:
    return db.db_path.resolve().with_suffix(db.db_path.suffix + ".service.json")


def serve(db: Archive, host: str, port: int, *, on_demand: bool = False,
          sync_on_start: bool = True) -> None:
    import uvicorn

    from .api import create_app

    descriptor = _service_file(db)
    with _service_lock(descriptor.with_suffix(".lock")):
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as listener:
            if os.name == "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind((host, port))
            except OSError:
                if not on_demand or port != DEFAULT_PORT:
                    raise
                listener.bind((host, 0))
            token = secrets.token_urlsafe(32)
            local_host = "[::1]" if family == socket.AF_INET6 else "127.0.0.1"

            def shutdown() -> None:
                server.should_exit = True

            app = create_app(db, sync_on_start=sync_on_start, service_token=token,
                             shutdown=shutdown if on_demand else None)
            server = uvicorn.Server(uvicorn.Config(app, host=host, port=listener.getsockname()[1]))
            temporary = descriptor.with_suffix(".tmp")
            temporary.unlink(missing_ok=True)
            with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
                json.dump({"url": f"http://{local_host}:{listener.getsockname()[1]}",
                           "token": token, "on_demand": on_demand}, stream)
            try:
                temporary.replace(descriptor)
                server.run(sockets=[listener])
            finally:
                descriptor.unlink(missing_ok=True)
                temporary.unlink(missing_ok=True)


def _request(endpoint: dict, path: str, *, method: str = "GET", data: dict | None = None,
             timeout: float = 2) -> dict:
    request = Request(endpoint["url"] + path, method=method,
                      headers={"Content-Type": "application/json", "X-SMM-Service": endpoint["token"]},
                      data=json.dumps(data).encode() if data is not None else None)
    with LOCAL_HTTP.open(request, timeout=timeout) as response:
        return json.load(response)


def running_service(db: Archive) -> dict | None:
    try:
        endpoint = json.loads(_service_file(db).read_text(encoding="utf-8"))
        url = urlsplit(endpoint["url"])
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1"}
                or url.port is None or url.path or url.query or url.fragment
                or url.username is not None):
            return None
        if _request(endpoint, "/api/service", timeout=0.5) == {"service": "smm-local"}:
            return endpoint
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return None


def _windows_start_service(command: list[str], log: Path) -> None:
    # A detached process can still belong to the Agent's Windows Job Object.
    # Ask Windows to start the service under the same user, outside that job.
    overrides = {name: os.environ[name] for name in ("SMM_CODEX_ROOT", "SMM_CLAUDE_ROOT", "CLAUDE_CONFIG_DIR",
                                                   "SMM_SERVICE_PORT", "SSL_CERT_FILE", "SSL_CERT_DIR")
                 if name in os.environ}
    bootstrap = (
        "import os, runpy, sys\n"
        f"os.environ.update({overrides!r})\n"
        f"with open({str(log)!r}, 'a', encoding='utf-8', buffering=1) as stream:\n"
        "    sys.stdout = sys.stderr = stream\n"
        "    runpy.run_module(sys.argv.pop(1), run_name='__main__')\n"
    )
    arguments = subprocess.list2cmdline([command[0], "-c", bootstrap, *command[2:]])
    quoted = arguments.replace("'", "''")
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly "
        "-Property @{CreateFlags=[uint32]8}\n"
        "$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
        f"-Arguments @{{CommandLine='{quoted}';ProcessStartupInformation=$startup}}\n"
        "if ($result.ReturnValue -ne 0) { throw ('Win32_Process.Create: ' + $result.ReturnValue) }\n"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                            stdin=subprocess.DEVNULL, capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW, timeout=STARTUP_TIMEOUT)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Windows 无法启动本地同步服务，请检查日志 {log}。{detail}")


def ensure_service(db: Archive, *, sync_on_start: bool = True) -> dict:
    endpoint = running_service(db)
    if endpoint is not None:
        return endpoint
    log = db.db_path.resolve().parent / "logs" / "on-demand.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("SMM_SERVICE_PORT", DEFAULT_PORT))
    command = [sys.executable, "-m", "smm_local.cli", "--db", str(db.db_path.resolve()),
               "serve", "--on-demand", "--port", str(port)]
    if not sync_on_start:
        command.append("--skip-initial-sync")
    deadline = time.monotonic() + STARTUP_TIMEOUT
    child = None
    if os.name == "nt":
        try:
            _windows_start_service(command, log)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"等待 Windows 启动本地同步服务超时，请检查日志 {log}") from exc
    else:
        with log.open("ab") as stream:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
    while time.monotonic() < deadline:
        endpoint = running_service(db)
        if endpoint is not None:
            return endpoint
        # Reap an unsuccessful child while another caller may be starting the service.
        if child is not None:
            child.poll()
        time.sleep(0.1)
    if child is not None and child.poll() is not None:
        raise RuntimeError(f"本地同步服务未能启动，请检查端口 {port} 和日志 {log}")
    raise RuntimeError(f"等待本地同步服务就绪超时（{STARTUP_TIMEOUT} 秒），请检查日志 {log}")


def stop_on_demand(db: Archive) -> None:
    endpoint = running_service(db)
    if endpoint and endpoint["on_demand"]:
        _request(endpoint, "/api/service/stop", method="PUT")
        deadline = time.monotonic() + 8
        while _service_file(db).is_file():
            if time.monotonic() >= deadline:
                raise RuntimeError("等待本地同步服务停止超时")
            time.sleep(0.1)


def control_source(db: Archive, source: str, enabled: bool) -> dict:
    from urllib.parse import quote

    endpoint = ensure_service(db, sync_on_start=False)
    return _request(endpoint, f"/api/sources/{quote(source, safe='')}/enabled", method="PUT",
                    data={"enabled": enabled})


def maintain(db: Archive, action: Action, source: str | None = None) -> dict:
    if source is not None and action not in {"status", "sync"}:
        raise ValueError("只有 status 和 sync 可指定来源")
    if action == "pause":
        endpoint = running_service(db)
        if endpoint is None:
            db.set_settings(sync_paused=True)
            return {"service_running": False, "paused": True}
    else:
        endpoint = ensure_service(db, sync_on_start=action not in ("sync", "resume"))

    base = {"service_running": True, "url": endpoint["url"]}
    if action == "status":
        info = _request(endpoint, "/api/status", timeout=8)
        if source is not None:
            sources = info["sync"]["sources"]
            if source not in sources:
                raise ValueError("未知对话来源")
            info["sync"]["sources"] = {source: sources[source]}
        return {**base, "conversations": info["conversations"], "messages": info["messages"],
                "last_file_sync": info["last_sync"], "errors": info["errors"], "sync": info["sync"]}
    if action == "open":
        try:
            opened = webbrowser.open(endpoint["url"])
        except (OSError, webbrowser.Error):
            opened = False
        return {**base, "opened": opened}
    if action == "sync":
        params = {"wait": "true"}
        if source is not None:
            params["source"] = source
        try:
            return {**base, **_request(endpoint, "/api/sync?" + urlencode(params), method="POST", timeout=20)}
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("detail")
            except (ValueError, AttributeError):
                detail = None
            raise ValueError(detail or str(exc)) from exc
    return {**base, **_request(endpoint, "/api/sync/pause", method="PUT",
                               data={"paused": action == "pause"})}

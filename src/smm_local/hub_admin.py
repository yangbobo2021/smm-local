# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Persistent settings and lifecycle for a managed aggregation server."""

from __future__ import annotations

import argparse
from contextlib import closing, redirect_stderr, redirect_stdout
from importlib.metadata import version
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from .core import shared_db_path
from .federation import hub_url
from .hub_os import Service, command as run_command
from .service import NoRedirect, _service_lock


def add_arguments(commands) -> None:
    hub = commands.add_parser("hub", help="配置和管理汇总服务")
    hub.add_argument("--state-dir", type=Path, default=Path.home() / ".local/share/smm-hub",
                     help="持久化汇总数据目录")
    actions = hub.add_subparsers(dest="hub_action", required=True)
    setup = actions.add_parser("setup", help="配置并启动汇总服务")
    setup.add_argument("--address", help="客户端使用的 HTTPS 地址")
    setup.add_argument("--tls-cert", type=Path)
    setup.add_argument("--tls-key", type=Path)
    setup.add_argument("--ca-file", type=Path, help="私有 CA 的证书，用于检查 HTTPS")
    setup.add_argument("--bind", default="0.0.0.0")
    setup.add_argument("--port", type=int, help="监听端口，默认为 HTTPS 地址的端口")
    for name, label in (("status", "查看汇总服务状态"), ("enable", "启用并启动汇总服务"),
                        ("disable", "停用汇总服务")):
        actions.add_parser(name, help=label)
    upgrade = actions.add_parser("upgrade", help="升级 uv 安装的汇总程序并检查服务")
    upgrade.add_argument("--uv", default="uv")
    upgrade.add_argument("--index", help="Python 包索引")
    upgrade.add_argument("--prerelease", action="store_true")
    upgrade.add_argument("--version", help="切换到指定的发行版本")
    actions.add_parser("run", help=argparse.SUPPRESS)


def write_file(path: Path, content: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        stream.write(content)
    temporary = Path(stream.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def choice(value, prompt):
    if value is not None:
        return str(value)
    if not sys.stdin.isatty():
        raise ValueError(f"缺少参数：{prompt}")
    return input(prompt + "：").strip()


class Hub:
    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.profile = self.root / "hub.json"
        self.database = self.root / "smm-hub.sqlite3"
        self.token = self.root / "hub-token"
        self.certificate = self.root / "tls.pem"
        self.key = self.root / "tls-key.pem"
        self.ca = self.root / "ca.pem"
        self.service = Service(self.root)

    def config(self):
        try:
            return json.loads(self.profile.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError("汇总服务尚未配置，请运行 smm hub setup") from exc

    def setup(self, args):
        if self.profile.is_file():
            cfg = self.config()
            if not any((args.address, args.tls_cert, args.tls_key, args.ca_file, args.port)):
                return self.enable()
            if self.database.is_file():
                raise ValueError(f"汇总端已配置为 {cfg['address']}，请用 hub enable 启动已有配置")
            self.service.preflight()
            self.service.stop(disable=True)
        address = hub_url(choice(args.address, "其他电脑访问的 HTTPS 地址（例如 https://hub.example.net:8770）"))
        parsed = urlsplit(address)
        if parsed.scheme != "https":
            raise ValueError("汇总端需要 HTTPS 地址")
        port = args.port if args.port is not None else parsed.port or 443
        if not 1 <= port <= 65535:
            raise ValueError("监听端口必须在 1 到 65535 之间")
        if sys.platform == "linux" and port < 1024:
            limit = Path("/proc/sys/net/ipv4/ip_unprivileged_port_start")
            if not limit.is_file() or port < int(limit.read_text()):
                raise ValueError("Linux 用户服务需要可由普通账户绑定的端口，例如 8770")
        local = shared_db_path().resolve()
        if self.database.resolve() == local or (self.database.exists() and local.exists()
                                                and self.database.samefile(local)):
            raise ValueError("汇总服务必须使用独立数据库")
        cert = Path(choice(args.tls_cert, "HTTPS 证书文件路径")).expanduser()
        key = Path(choice(args.tls_key, "HTTPS 私钥文件路径")).expanduser()
        ca = args.ca_file.expanduser() if args.ca_file else None
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key, password="")
        if ca:
            ssl.create_default_context(cafile=str(ca))
        self.service.preflight()
        self.service.protect_state()
        for source, target in ((cert, self.certificate), (key, self.key), (ca, self.ca)):
            if source:
                write_file(target, source.read_bytes())
        if not self.token.exists():
            write_file(self.token, (secrets.token_urlsafe(48) + "\n").encode("ascii"))
        cfg = {"address": address, "bind": args.bind, "port": port, "enabled": True}
        write_file(self.profile, json.dumps(cfg, indent=2).encode())
        try:
            return self.enable()
        except (OSError, RuntimeError, ValueError):
            # Keep an existing archive and its credentials on failed recovery.
            if not self.database.is_file():
                self.profile.unlink(missing_ok=True)
            raise

    def identity(self, cfg):
        address = urlsplit(cfg["address"])
        context = ssl.create_default_context(cafile=str(self.ca) if self.ca.is_file() else None)
        opener = build_opener(ProxyHandler({}), NoRedirect(), HTTPSHandler(context=context))
        request = Request(address.geturl() + "/v1/info", headers={
            "Authorization": "Bearer " + self.token.read_text(encoding="ascii").strip(),
        })
        with opener.open(request, timeout=2) as response:
            info = json.load(response)
        if info.get("protocol") != 1 or not info.get("hub_id"):
            raise ValueError("地址返回了无效的汇总服务信息")
        with closing(sqlite3.connect(self.database.as_uri() + "?mode=ro", uri=True)) as database:
            row = database.execute("SELECT value FROM settings WHERE key='hub_identity'").fetchone()
        if not row or json.loads(row[0]) != info["hub_id"]:
            raise ValueError("访问地址与本机汇总数据库的标识不一致")
        return info["hub_id"]

    def status(self, *, wait=False):
        cfg = self.config()
        result = {"enabled": cfg["enabled"], "address": cfg["address"], "running": False,
                  "credential_file": str(self.token), "database": str(self.database),
                  "version": cfg.get("version", version("smm-local")), "service": self.service.name,
                  "log_file": str(self.root / "hub.log")}
        if self.ca.is_file():
            result["ca_file"] = str(self.ca)
        deadline = time.monotonic() + (20 if wait else 0)
        while True:
            try:
                result["hub_id"] = self.identity(cfg)
                result["running"] = True
                result.pop("error", None)
                return result
            except (OSError, ValueError, sqlite3.Error) as exc:
                result["error"] = str(exc)
            if time.monotonic() >= deadline:
                if wait:
                    raise RuntimeError(f"汇总服务健康检查失败：{result['error']}。日志：{result['log_file']}")
                return result
            time.sleep(.25)

    def enable(self):
        cfg = self.config()
        self.service.preflight()
        self.service.install(cfg)
        if not cfg["enabled"]:
            cfg["enabled"] = True
            write_file(self.profile, json.dumps(cfg, indent=2).encode())
        self.service.start()
        return self.status(wait=True)

    def disable(self):
        cfg = self.config()
        self.service.preflight()
        self.service.stop(disable=True)
        cfg["enabled"] = False
        write_file(self.profile, json.dumps(cfg, indent=2).encode())
        deadline = time.monotonic() + 25
        while (result := self.status())["running"]:
            if time.monotonic() >= deadline:
                raise RuntimeError("汇总服务已禁用，但进程尚未停止")
            time.sleep(.25)
        return result

    def upgrade(self, args):
        cfg = self.config()
        self.service.preflight()
        manager = shutil.which(args.uv)
        if manager is None:
            raise ValueError("找不到 uv，请用 --uv 指定安装此 SMM 的包管理器")
        uv = [manager, "tool"]
        if args.index:
            source = urlsplit(args.index)
            if source.username or source.password:
                raise ValueError("请通过 uv 的认证配置提供包索引凭证")
        listing = run_command(*uv, "dir").stdout.strip()
        if Path(sys.prefix).resolve() != (Path(listing).expanduser() / "smm-local").resolve():
            raise ValueError("请在通过 uv tool 安装此汇总端的账户和环境中运行升级")
        if sys.platform == "win32":
            return self.upgrade_windows(cfg, args, uv)
        current = version("smm-local")
        base_python = sys._base_executable
        install = [*uv, "install", "--python", base_python]
        options = ["--index", args.index] if args.index else []
        if args.prerelease:
            options += ["--prerelease", "allow"]
        if args.version:
            if not re.fullmatch(r"[0-9][A-Za-z0-9.!+_-]*", args.version):
                raise ValueError("请输入有效的 SMM 版本号")
            update = [*install, f"smm-local=={args.version}"]
        else:
            update = [*uv, "upgrade", "smm-local"]
        backup = None
        attempted_start = False
        if cfg["enabled"]:
            self.service.stop(disable=False)
        try:
            if self.database.is_file():
                backup = self.backup()
            subprocess.run([*update, *options], check=True, stdout=sys.stderr)
            updated = run_command(sys.executable, "-c",
                "from importlib.metadata import version; print(version('smm-local'))").stdout.strip()
            run_command(sys.executable, "-m", "smm_local.cli", "hub", "--help")
            if cfg["enabled"]:
                self.service.install(cfg)
                attempted_start = True
                self.service.start()
            result = self.status(wait=cfg["enabled"])
        except (OSError, RuntimeError, ValueError, sqlite3.Error, subprocess.SubprocessError) as exc:
            try:
                if attempted_start:
                    self.service.stop(disable=False)
                    if backup:
                        self.restore(backup)
                subprocess.run([*install, "--reinstall", f"smm-local=={current}", *options],
                               check=True, stdout=sys.stderr)
                if cfg["enabled"]:
                    self.service.install(cfg)
                    self.service.start()
                    self.status(wait=True)
            except (OSError, RuntimeError, ValueError, sqlite3.Error, subprocess.SubprocessError) as recovery:
                raise RuntimeError(f"升级失败：{exc}；恢复失败：{recovery}；数据库备份：{backup}") from exc
            raise RuntimeError(f"升级失败，已恢复 {current}：{exc}") from exc
        result["version"] = updated
        if backup:
            result["backup_file"] = str(backup)
        return result

    def upgrade_windows(self, cfg, args, uv):
        if args.version and not re.fullmatch(r"[0-9][A-Za-z0-9.!+_-]*", args.version):
            raise ValueError("请输入有效的 SMM 版本号")
        runtime = self.service.new_runtime_directory()
        env = {**os.environ, "UV_TOOL_DIR": str(runtime / "tools"),
               "UV_TOOL_BIN_DIR": str(runtime / "bin")}
        package = f"smm-local=={args.version}" if args.version else "smm-local"
        base = str(Path(sys.base_prefix) / "python.exe")
        options = ["--index", args.index] if args.index else []
        if args.prerelease:
            options += ["--prerelease", "allow"]
        try:
            subprocess.run([*uv, "install", "--python", base, package, *options],
                           check=True, env=env, stdout=sys.stderr)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("包管理器未能安装新版本，汇总服务继续使用旧版本") from exc
        python = runtime / "tools" / "smm-local" / "Scripts" / "python.exe"
        run_command(str(python), "-m", "smm_local.cli", "hub", "--help")
        installed = run_command(str(python), "-c",
            "from importlib.metadata import version; print(version('smm-local'))").stdout.strip()
        next_cfg = {**cfg, "python": str(python), "base_python": base, "version": installed}
        if cfg["enabled"]:
            self.service.stop(disable=False)
        backup = None
        try:
            if self.database.is_file():
                backup = self.backup()
            write_file(self.profile, json.dumps(next_cfg, indent=2).encode())
            if cfg["enabled"]:
                self.service.install(next_cfg)
                self.service.start()
            result = self.status(wait=cfg["enabled"])
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            try:
                if cfg["enabled"]:
                    self.service.stop(disable=False)
                    if backup:
                        self.restore(backup)
                write_file(self.profile, json.dumps(cfg, indent=2).encode())
                if cfg["enabled"]:
                    self.service.install(cfg)
                    self.service.start()
                    self.status(wait=True)
            except (OSError, RuntimeError, sqlite3.Error) as recovery:
                raise RuntimeError(f"升级失败：{exc}；恢复失败：{recovery}；数据库备份：{backup}") from exc
            raise RuntimeError(f"升级失败，已恢复原汇总服务：{exc}") from exc
        if backup:
            result["backup_file"] = str(backup)
        return result

    def backup(self):
        backup = self.root / f"backup-{time.time_ns()}.sqlite3"
        write_file(backup, b"")
        with closing(sqlite3.connect(self.database)) as source, closing(sqlite3.connect(backup)) as target:
            source.backup(target)
        return backup

    def restore(self, backup):
        with closing(sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(self.database)) as target:
                source.backup(target)

    def server(self):
        import uvicorn

        from .core import Archive
        from .hub import create_hub

        cfg = self.config()
        token = self.token.read_text(encoding="ascii").strip()
        return uvicorn.Server(uvicorn.Config(create_hub(Archive(self.database), token),
            host=cfg["bind"], port=cfg["port"], ssl_certfile=str(self.certificate),
            ssl_keyfile=str(self.key)))

    def run(self):
        with (self.root / "hub.log").open("a", encoding="utf-8", buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                if sys.platform == "win32":
                    from .windows_service import serve
                    serve(self.service.name, self.server)
                else:
                    self.server().run()


def dispatch(args: argparse.Namespace):
    hub = Hub(args.state_dir)
    action = args.hub_action
    if action in ("status", "run"):
        return getattr(hub, action)()
    hub.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _service_lock(hub.root / "admin.lock"):
        if action in ("setup", "upgrade"):
            return getattr(hub, action)(args)
        return getattr(hub, action)()

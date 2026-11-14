# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Provision SMM from a Python package index once, then execute the requested operation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit


PACKAGE = "smm-local==0.2.0rc16"
DEFAULT_INDEX = "https://pypi.org/simple"
TEST_INDEX = "https://test.pypi.org/simple"


@contextmanager
def install_lock(path: Path):
    with path.open("a+b") as lock:
        deadline = time.monotonic() + 900
        while True:
            try:
                if os.name == "nt":
                    import msvcrt

                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("等待另一会话完成 SMM 安装超时")
                time.sleep(0.25)
        yield


def installed_cli(manifest: Path) -> Path | None:
    if manifest.is_file():
        cli = Path(json.loads(manifest.read_text(encoding="utf-8")).get("cli_path", ""))
        if cli.is_absolute() and cli.is_file():
            try:
                probe = subprocess.run([str(cli), "--help"], capture_output=True, text=True, timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                return None
            if probe.returncode == 0 and "configure-hub" in probe.stdout:
                return cli
    return None


def install_package(data: Path) -> None:
    environment = data / "package"
    windows = os.name == "nt"
    python = environment / ("Scripts/python.exe" if windows else "bin/python")
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(environment)],
                       check=True, stdout=sys.stderr, timeout=120)
    index = os.environ.get("SMM_PACKAGE_INDEX", DEFAULT_INDEX)
    source = urlsplit(index)
    if source.username or source.password:
        raise ValueError("请通过包管理器的认证配置提供凭证")
    pip_env = {**os.environ, "PIP_CONFIG_FILE": os.devnull}
    pip = [str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input",
           "--timeout", "15", "--retries", "1"]
    options = {"env": pip_env, "check": True, "stdout": sys.stderr, "timeout": 900}
    with tempfile.TemporaryDirectory() as directory:
        package = PACKAGE
        if index.rstrip("/") == TEST_INDEX:
            subprocess.run([*pip, "download", "--no-deps", "--only-binary", ":all:", "--index-url",
                            index, "--dest", directory, PACKAGE], **options)
            wheel, = Path(directory).glob("*.whl")
            package = str(wheel)
            index = DEFAULT_INDEX
        subprocess.run([*pip, "install", "--only-binary", ":all:", "--index-url", index, package], **options)
    register = [str(python), "-I", "-m", "smm_local.installation", "install"]
    if os.environ.get("SMM_NO_LOGIN_SERVICE") == "1":
        register.append("--no-service")
    subprocess.run(register, check=True, stdout=sys.stderr, timeout=120)


def ensure_cli() -> Path:
    data = Path.home() / ".local/share/smm-local"
    data.mkdir(parents=True, exist_ok=True)
    manifest = data / "install.json"
    with install_lock(data / "install.lock"):
        cli = installed_cli(manifest)
        if cli is not None:
            return cli
        install_package(data)
        cli = installed_cli(manifest)
        if cli is None:
            raise RuntimeError("SMM 安装完成后未找到可用的命令")
        return cli


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in {"maintenance", "configure-hub", "projects", "resolve-project", "search", "read"}:
        print("用法：first_use <maintenance|configure-hub|projects|resolve-project|search|read> [参数]", file=sys.stderr)
        return 2
    try:
        cli = ensure_cli()
        if args[0] == "search":
            deadline = time.monotonic() + 15
            while True:
                status = subprocess.run([str(cli), "maintenance", "status"], capture_output=True, text=True)
                if status.returncode:
                    print(status.stderr.strip(), file=sys.stderr)
                    break
                sync = json.loads(status.stdout)["sync"]
                if sync["paused"] or sync["last_result"] is not None or time.monotonic() >= deadline:
                    break
                time.sleep(0.25)
        return subprocess.run([str(cli), *args]).returncode
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        detail = f"包安装或注册失败（退出码 {exc.returncode}），请查看上方错误" if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(f"SMM 首次启动失败：{detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

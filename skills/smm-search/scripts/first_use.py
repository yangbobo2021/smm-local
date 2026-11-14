# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Provision SMM from a Python package index once, then execute the requested operation."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit


PACKAGE = "smm-local==0.2.0"
DEFAULT_INDEX = "https://pypi.org/simple"
TEST_INDEX = "https://test.pypi.org/simple"
PROGRESS_INTERVAL = 15
INSTALL_ATTEMPTS = 3


def progress(message: str) -> None:
    print(f"SMM 安装：{message}", file=sys.stderr, flush=True)


@contextmanager
def install_lock(path: Path):
    with path.open("a+b") as lock:
        next_notice = time.monotonic() + PROGRESS_INTERVAL
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
            except OSError as exc:
                if not isinstance(exc, BlockingIOError) and not (os.name == "nt" and exc.errno == 13):
                    raise
                if time.monotonic() >= next_notice:
                    progress("另一会话正在安装，等待复用其结果")
                    next_notice = time.monotonic() + PROGRESS_INTERVAL
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


def run_pip(command: list[str], env: dict[str, str], stage: str) -> None:
    for attempt in range(1, INSTALL_ATTEMPTS + 1):
        progress(f"{stage}（第 {attempt}/{INSTALL_ATTEMPTS} 次）")
        started = time.monotonic()
        next_notice = started + PROGRESS_INTERVAL
        latest = ""
        lines: queue.Queue[str | None] = queue.Queue()
        with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding="utf-8", errors="replace") as process:
            assert process.stdout is not None

            def read_output() -> None:
                try:
                    for line in process.stdout:
                        lines.put(line)
                finally:
                    lines.put(None)

            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            try:
                while True:
                    try:
                        line = lines.get(timeout=max(0, next_notice - time.monotonic()))
                    except queue.Empty:
                        line = ""
                    if line is None:
                        break
                    if line.startswith("Progress "):
                        latest = line.strip().removeprefix("Progress ") + " 字节"
                    elif line:
                        if line.lstrip().startswith(("Downloading ", "Using cached ")):
                            latest = ""
                        print(line, end="", file=sys.stderr, flush=True)
                    now = time.monotonic()
                    if now >= next_notice:
                        detail = f"，当前文件 {latest}" if latest else ""
                        progress(f"{stage}仍在进行，已等待 {int(now - started)} 秒{detail}")
                        next_notice = now + PROGRESS_INTERVAL
                code = process.wait()
            except BaseException:
                process.kill()
                raise
            finally:
                reader.join()
        if not code:
            return
        if attempt < INSTALL_ATTEMPTS:
            progress("本次安装未完成，将自动重试并复用已下载的文件")
            time.sleep(2 ** attempt)
    raise subprocess.CalledProcessError(code, command)


def install_package(data: Path) -> None:
    environment = data / "package"
    windows = os.name == "nt"
    python = environment / ("Scripts/python.exe" if windows else "bin/python")
    if not python.is_file():
        progress("准备本机 Python 环境")
        subprocess.run([sys.executable, "-m", "venv", str(environment)],
                       check=True, stdout=sys.stderr, timeout=120)
    index = os.environ.get("SMM_PACKAGE_INDEX", DEFAULT_INDEX)
    source = urlsplit(index)
    if source.username or source.password:
        raise ValueError("请通过包管理器的认证配置提供凭证")
    pip_env = {**os.environ, "PIP_CONFIG_FILE": os.devnull, "PYTHONIOENCODING": "utf-8"}
    pip = [str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "--no-input",
           "--timeout", "30", "--retries", "2", "--cache-dir", str(data / "pip-cache")]
    # A cancelled venv creation can leave the interpreter but not pip.
    probe = subprocess.run([*pip, "--help"], env=pip_env, capture_output=True, text=True, timeout=20)
    if probe.returncode:
        progress("修复未完成的 Python 环境")
        subprocess.run([str(python), "-I", "-m", "ensurepip", "--upgrade"],
                       check=True, stdout=sys.stderr, timeout=120)
        probe = subprocess.run([*pip, "--help"], env=pip_env, capture_output=True, text=True, check=True, timeout=20)
    if "--resume-retries" in probe.stdout:
        pip.extend(("--resume-retries", "5"))
    install_options = ["--only-binary", ":all:", "--progress-bar",
                       "raw" if "--resume-retries" in probe.stdout else "on"]
    with tempfile.TemporaryDirectory() as directory:
        package = PACKAGE
        if index.rstrip("/") == TEST_INDEX:
            run_pip([*pip, "download", "--no-deps", *install_options, "--index-url", index,
                     "--dest", directory, PACKAGE], pip_env, "下载测试包")
            wheel, = Path(directory).glob("*.whl")
            package = str(wheel)
            index = DEFAULT_INDEX
        run_pip([*pip, "install", *install_options, "--index-url", index, package], pip_env, "下载并安装本机组件")
    register = [str(python), "-I", "-m", "smm_local.installation", "install"]
    if os.environ.get("SMM_NO_LOGIN_SERVICE") == "1":
        register.append("--no-service")
    progress("配置本机入口")
    subprocess.run(register, check=True, stdout=sys.stderr, timeout=120)
    progress("已完成，继续处理原请求")


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

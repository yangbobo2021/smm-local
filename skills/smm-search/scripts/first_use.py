# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Provision the bundled SMM runtime once, then execute the requested operation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


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
        cli = Path(json.loads(manifest.read_text(encoding="utf-8"))["cli_path"])
        if cli.is_absolute() and cli.is_file():
            try:
                probe = subprocess.run([str(cli), "--help"], capture_output=True, text=True, timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                return None
            if probe.returncode == 0 and "configure-hub" in probe.stdout:
                return cli
    return None


def unpack(bundle: Path, target: Path) -> None:
    with tempfile.TemporaryDirectory(dir=target.parent) as directory:
        staging = Path(directory) / "runtime"
        staging.mkdir()
        with ZipFile(bundle) as archive:
            for entry in archive.infolist():
                name = PurePosixPath(entry.filename)
                if (name.is_absolute() or ".." in name.parts or "\\" in entry.filename
                        or any(":" in part for part in name.parts) or entry.is_dir()):
                    raise ValueError(f"安装包包含无效路径：{entry.filename}")
                dest = staging.joinpath(*name.parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, dest.open("xb") as output:
                    shutil.copyfileobj(source, output)
        staging.rename(target)


def ensure_cli() -> Path:
    data = Path.home() / ".local/share/smm-local"
    data.mkdir(parents=True, exist_ok=True)
    manifest = data / "install.json"
    with install_lock(data / "install.lock"):
        cli = installed_cli(manifest)
        if cli is not None:
            return cli
        bundle = Path(__file__).resolve().with_name("runtime.zip")
        if not bundle.is_file():
            raise RuntimeError("当前 Skill 缺少随附安装包，请使用完整的发行版 Skill")
        digest = bundle.with_suffix(".sha256").read_text(encoding="ascii").strip()
        if hashlib.sha256(bundle.read_bytes()).hexdigest() != digest:
            raise ValueError("SMM Skill 随附的安装包校验失败，请重新安装 Skill")
        target = data / f"runtime-{digest[:16]}"
        if not target.exists():
            unpack(bundle, target)
        install = subprocess.run([sys.executable, str(target / "scripts/install.py"), "--keep-skills"],
                                 stdout=sys.stderr, timeout=900)
        if install.returncode:
            raise RuntimeError("SMM 安装失败，请查看上方错误；下次使用可以重试")
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
        return subprocess.run([str(cli), *args]).returncode
    except (OSError, ValueError, RuntimeError, KeyError, BadZipFile, subprocess.SubprocessError) as exc:
        print(f"SMM 首次启动失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

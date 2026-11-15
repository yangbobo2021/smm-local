"""Create a source-only coworker trial bundle from an explicit allowlist."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import re
import tarfile
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
ALLOW_FILES = ("README.md", "TRIAL_GUIDE.md", "LICENSE", "pyproject.toml")
ALLOW_DIRS = ("src/smm_local", "scripts", "skills/smm-search", "skills/smm-source-adapter")
DENY_PARTS = {"__pycache__", ".venv", ".git", ".acceptance", ".acceptance-local", "dist"}
SECRET = re.compile(rb"(?:sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9]{20,})")


def members() -> list[Path]:
    paths = [ROOT / name for name in ALLOW_FILES]
    for directory in ALLOW_DIRS:
        paths.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    return sorted(path for path in paths if path.is_file() and not path.is_symlink() and path.name != "verify_installation.py"
                  and not set(path.relative_to(ROOT).parts) & DENY_PARTS
                  and path.suffix not in {".pyc", ".sqlite3", ".db"})


def write_skill(version: str, files: list[Path], name: str) -> Path:
    skill = ROOT / "skills" / name
    output = ROOT / "dist" / f"{name}-{version}.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in files:
            if path.is_relative_to(skill):
                add_to_zip(archive, f"{name}/{path.relative_to(skill).as_posix()}", path.read_bytes())
    return output


def add_to_zip(archive: ZipFile, name: str, payload: bytes) -> None:
    info = ZipInfo(name)
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload, compress_type=ZIP_DEFLATED)


def main() -> None:
    parser = argparse.ArgumentParser()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    parser.add_argument("--version", default=version.replace("rc", "-rc"))
    parser.add_argument("--skill", action="store_true", help="构建可通过在线包源首次安装的 Skill")
    parser.add_argument("--adapter-skill", action="store_true", help="构建本机来源适配 Skill")
    args = parser.parse_args()
    files = members()
    for path in files:
        if SECRET.search(path.read_bytes()):
            raise SystemExit(f"疑似凭证，已中止打包：{path.relative_to(ROOT)}")
    if args.skill or args.adapter_skill:
        output = write_skill(args.version, files, "smm-source-adapter" if args.adapter_skill else "smm-search")
        print(f"{output}\nsha256 {hashlib.sha256(output.read_bytes()).hexdigest()}")
        return
    output = ROOT / "dist" / f"smm-local-{args.version}.tar.gz"
    output.parent.mkdir(exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in files:
                    info = archive.gettarinfo(path, arcname=f"smm-local-{args.version}/{path.relative_to(ROOT)}")
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as stream:
                        archive.addfile(info, stream)
    print(f"{output}\nsha256 {hashlib.sha256(output.read_bytes()).hexdigest()}\nfiles {len(files)}")


if __name__ == "__main__":
    main()

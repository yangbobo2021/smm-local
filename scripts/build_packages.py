# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Build independent SMM Local and SMM Hub wheels from the same checkout."""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "src/smm_local"
IGNORE_GENERATED = shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info")
SECRET = re.compile(rb"(?:sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:api[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9]{20,})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist/packages")
    parser.add_argument("--uv", default="uv")
    args = parser.parse_args()
    output = args.out_dir.resolve()
    with tempfile.TemporaryDirectory(prefix="smm-package-") as directory:
        stage = Path(directory)
        local, hub = stage / "local", stage / "hub"
        for project, metadata in ((local, ROOT / "pyproject.toml"),
                                  (hub, ROOT / "packaging/hub/pyproject.toml")):
            project.mkdir()
            shutil.copyfile(metadata, project / "pyproject.toml")
            shutil.copyfile(ROOT / "LICENSE", project / "LICENSE")
        shutil.copytree(ARCHIVE, local / "src/smm_local", ignore=IGNORE_GENERATED)
        hub_code = hub / "src/smm_hub"
        shutil.copytree(ROOT / "src/smm_hub", hub_code,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_archive.py"))
        # Vendor the shared storage code under the hub's own namespace.
        shared = hub_code / "_archive"
        shared.mkdir()
        shim = (ROOT / "src/smm_hub/_archive.py").read_text(encoding="utf-8")
        (shared / "__init__.py").write_text(shim.replace("from smm_local.", "from ."), encoding="utf-8", newline="\n")
        for name in ("core.py", "support.py", "archive_protocol.py", "references.py", "documents.py", "managed_documents.py", "managed_document_uploads.py", "document_protocol.py", "document_results.py", "document_snapshots.py", "document_transfers.py", "document_processing.py", "document_supervisor.py", "document_worker.py"):
            shutil.copyfile(ARCHIVE / name, shared / name)
        shutil.copytree(ARCHIVE / "document_formats", shared / "document_formats", ignore=IGNORE_GENERATED)
        shutil.copytree(ARCHIVE / "importers", shared / "importers", ignore=IGNORE_GENERATED)
        for project in (local, hub):
            for path in (project / "src").rglob("*"):
                if path.is_file() and (path.suffix in {".db", ".sqlite", ".sqlite3", ".jsonl", ".pem", ".key"}
                                       or SECRET.search(path.read_bytes())):
                    raise SystemExit(f"Unexpected data in package source: {path.relative_to(project)}")
            subprocess.run([args.uv, "build", "--wheel", "--out-dir", str(output)],
                           cwd=project, check=True)


if __name__ == "__main__":
    main()

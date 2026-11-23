"""Lossless packaging for native acceptance evidence, after all tests finish.

No business fixtures, inputs, assertions, exit status or stdout are changed.
Native acceptance has a 25MiB per-attempt artifact budget; full 2MiB boundary
reads legitimately exceed it when retained as repeated JSON envelopes.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest


def pytest_sessionfinish(session, exitstatus):
    directory = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
    if not directory:
        return
    root = Path(directory)
    files = sorted(p for p in root.rglob('*.json') if p.is_file())
    if sum(p.stat().st_size for p in files) <= 8 * 1024 * 1024:
        return
    manifest = []
    for path in files:
        raw = path.read_bytes()
        compressed = gzip.compress(raw, mtime=0)
        target = path.with_suffix(path.suffix + '.gz')
        if target.exists():
            raise RuntimeError('refuse to overwrite existing acceptance evidence')
        target.write_bytes(compressed)
        assert gzip.decompress(target.read_bytes()) == raw
        manifest.append({
            'original_path': path.relative_to(root).as_posix(),
            'original_bytes': len(raw),
            'original_sha256': hashlib.sha256(raw).hexdigest(),
            'gzip_path': target.relative_to(root).as_posix(),
            'gzip_bytes': len(compressed),
            'gzip_sha256': hashlib.sha256(compressed).hexdigest(),
        })
        path.unlink()
    (root / 'lossless-evidence.json').write_text(
        json.dumps({'format': 'gzip-original-json-v1', 'files': manifest}, indent=2) + '\n',
        encoding='utf-8',
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # Preserve originals before pytest's temporary-directory retention expires.
    # Collect only the package probe's detailed command receipts, never its
    # wheels, environments, source archives, credentials or database files.
    try:
        yield
    finally:
        directory = os.environ.get('ACCEPTANCE_EVIDENCE_DIR')
        temporary = item.funcargs.get('tmp_path')
        if directory and temporary is not None:
            source = temporary / 'packages'
            if source.is_dir():
                target = Path(directory) / 'package-probe-originals'
                target.mkdir(parents=True, exist_ok=False)
                for path in sorted(source.iterdir()):
                    if path.is_file() and (path.suffix in {'.stdout', '.stderr'}
                            or path.name in {'commands.json', 'result.json',
                                             'local-expected.json', 'hub-expected.json'}):
                        shutil.copyfile(path, target / path.name)

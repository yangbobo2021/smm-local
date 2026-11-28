"""Read-only, byte-verified receiver cache inventory before synchronization."""
from __future__ import annotations
import hashlib
from pathlib import Path
import re


def inventory(root):
    result = {}
    for kind in ('raw', 'results'):
        result[kind] = {}
        directory = Path(root) / '.document-snapshots' / kind
        for path in directory.iterdir():
            if not re.fullmatch('[0-9a-f]{64}', path.name):continue
            assert path.is_file() and not path.is_symlink()
            before = path.stat()
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = path.stat()
            assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) == (
                after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
            assert digest == path.name
            result[kind][digest] = {'bytes': before.st_size, 'sha256': digest}
    return result

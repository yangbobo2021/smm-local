# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Read source JSONL without expanding compressed histories on disk."""

import io
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator

try:
    from compression import zstd
except ImportError:  # Python 3.11–3.13
    import zstandard as zstd

    @contextmanager
    def _open_compressed(path: Path) -> Iterator[BinaryIO]:
        with path.open("rb") as compressed:
            reader = zstd.ZstdDecompressor().stream_reader(compressed, read_across_frames=True)
            with io.BufferedReader(reader) as stream:
                yield stream
else:
    @contextmanager
    def _open_compressed(path: Path) -> Iterator[BinaryIO]:
        with zstd.open(path, "rb") as stream:
            yield stream


@contextmanager
def open_source(path: Path) -> Iterator[BinaryIO]:
    try:
        if path.name.endswith(".jsonl.zst"):
            with _open_compressed(path) as stream:
                yield stream
        else:
            with path.open("rb") as stream:
                yield stream
    except (zstd.ZstdError, EOFError) as exc:
        raise OSError(f"无法解压来源文件 {path}: {exc}") from exc

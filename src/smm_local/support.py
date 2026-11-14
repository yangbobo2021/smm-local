# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Network and file primitives shared by the local and aggregation packages."""

import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@contextmanager
def _service_lock(path: Path):
    with path.open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("此档案已有同步服务正在启动或运行") from exc
        yield


def hub_url(address: str) -> str:
    address = address.strip().rstrip("/")
    if "://" not in address:
        address = "https://" + address
    url = urlsplit(address)
    if (not url.hostname or url.username is not None or url.query or url.fragment
            or url.path or any(char.isspace() for char in address)
            or url.scheme not in {"http", "https"}):
        raise ValueError("请输入汇总服务的地址，例如 https://smm.example.net")
    if url.scheme == "http" and url.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("跨电脑连接需要 HTTPS")
    _ = url.port
    return address

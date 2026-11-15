# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>

import os
import socket
import subprocess
import sys
import time

import pytest

from smm_local import service
from smm_local.core import Archive


@pytest.mark.skipif(os.name != "nt", reason="Windows background startup deadline")
def test_windows_waits_for_a_slow_background_service(tmp_path, monkeypatch):
    db = Archive(tmp_path / "archive.sqlite3")
    db.set_settings(sync_paused=True)
    monkeypatch.setenv("SMM_SERVICE_PORT", "0")
    launch = service._windows_start_service

    def delay_service(command, log):
        time.sleep(9)
        launch(command, log)

    monkeypatch.setattr(service, "_windows_start_service", delay_service)
    try:
        endpoint = service.ensure_service(db, sync_on_start=False)
        assert service.running_service(db) == endpoint
    finally:
        service.stop_on_demand(db)


def test_service_start_cannot_use_an_unrelated_listener(tmp_path, monkeypatch):
    db = Archive(tmp_path / "archive.sqlite3")
    db.set_settings(sync_paused=True)
    with socket.socket() as unrelated:
        unrelated.bind(("127.0.0.1", 0))
        unrelated.listen()
        monkeypatch.setenv("SMM_SERVICE_PORT", str(unrelated.getsockname()[1]))
        result = subprocess.run(
            [sys.executable, "-m", "smm_local.cli", "--db", str(db.db_path), "maintenance", "status"],
            capture_output=True, encoding="utf-8", timeout=service.STARTUP_TIMEOUT + 10,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        assert result.returncode != 0
        assert "本地同步服务" in result.stderr
        assert service.running_service(db) is None

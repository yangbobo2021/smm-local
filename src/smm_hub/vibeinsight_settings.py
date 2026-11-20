# SPDX-License-Identifier: Apache-2.0
"""Persist the VibeInsight connection and run sync for a managed Hub."""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ._archive import Archive
from .vibeinsight import PostgresSource, VibeInsightSync, record_failure


@dataclass(frozen=True)
class Connection:
    host: str
    port: int
    database: str
    user: str
    interval: int
    psql: str

    def __post_init__(self):
        if not self.host.strip() or not self.user.strip() or not self.database.strip():
            raise ValueError("VibeInsight 连接需要主机、数据库和用户名")
        if "=" in self.database or "://" in self.database:
            raise ValueError("数据库参数应为数据库名")
        if not 1 <= self.port <= 65535 or self.interval < 1:
            raise ValueError("数据库端口或同步周期无效")


class VibeInsightSettings:
    def __init__(self, root: Path, archive: Archive, *, source_factory=PostgresSource):
        self.root = root
        self.archive = archive
        self.profile = root / "vibeinsight.json"
        self.source_factory = source_factory

    def load(self) -> dict:
        try:
            return json.loads(self.profile.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}

    def configure(self, connection: Connection, password: str) -> dict:
        from .hub_admin import write_file

        binary = shutil.which(connection.psql)
        if binary is None and self.source_factory is PostgresSource:
            raise ValueError("找不到 psql，请安装 PostgreSQL 客户端或指定 --psql")
        if not password:
            raise ValueError("VibeInsight 数据库密码不能为空")
        prior = self.load()
        config = {**vars(connection), "psql": str(Path(binary).resolve()) if binary else connection.psql}
        self.source_factory(config, password).validate()
        config["credential_file"] = f"vibeinsight-credential-{uuid4().hex}"
        credential = self.root / config["credential_file"]
        write_file(credential, password.encode("utf-8"))
        try:
            write_file(self.profile, json.dumps(config, ensure_ascii=False).encode("utf-8"))
        except OSError:
            credential.unlink(missing_ok=True)
            raise
        if prior:
            old_file = self.root / Path(prior["credential_file"]).name
            old_file.unlink(missing_ok=True)
        return self.status()

    def status(self) -> dict:
        config = self.load()
        with self.archive.connect() as con:
            results = {row[0]: json.loads(row[1]) for row in con.execute("""
                SELECT key,value FROM settings WHERE key IN ('vibeinsight_last_success','vibeinsight_error','vibeinsight_last_failure')
            """)}
        return {
            "enabled": bool(config),
            **{key: config[key] for key in ("host", "port", "database", "user", "interval") if key in config},
            "credential_saved": bool(config and (self.root / Path(config["credential_file"]).name).is_file()),
            "last_success": results.get("vibeinsight_last_success"),
            "last_error": results.get("vibeinsight_error"),
            "last_failure": results.get("vibeinsight_last_failure"),
        }

    def sync(self, config: dict, stopped) -> None:
        path = self.root / Path(config["credential_file"]).name
        try:
            password = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError("无法读取已保存的 VibeInsight 凭据") from exc
        source_id = json.dumps([config["host"], config["port"], config["database"]])
        VibeInsightSync(self.archive, source_id).run(self.source_factory(config, password), stopped=stopped)

    def _serve(self, stopped: threading.Event) -> None:
        previous = {}
        due = 0.0
        while not stopped.is_set():
            try:
                config = self.load()
                if config and (config != previous or time.monotonic() >= due):
                    previous = config
                    due = time.monotonic() + config["interval"]
                    self.sync(config, stopped.is_set)
                    due = time.monotonic() + config["interval"]
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                record_failure(self.archive, exc)
            stopped.wait(0.25)

    @asynccontextmanager
    async def lifespan(self, app):
        stopped = threading.Event()
        task = asyncio.create_task(asyncio.to_thread(self._serve, stopped))
        try:
            yield
        finally:
            stopped.set()
            await task

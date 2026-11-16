# SPDX-License-Identifier: Apache-2.0
"""Read-only VibeInsight ingestion with durable archive checkpoints."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Protocol

from ._archive import Archive
from .projects import HubProjects

Position = tuple[str, str]
SOURCE = "vibeinsight"
OVERLAP = timedelta(hours=24)
BATCH_SIZE = 500


class Source(Protocol):
    def projects(self, through: Position | None = None) -> list[str]: ...
    def upper(self) -> Position | None: ...
    def page(self, project: str, after: Position | None, through: Position, limit: int) -> list[dict]: ...


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _position_sql(position: Position) -> str:
    timestamp, identifier = position
    return f"({_literal(timestamp)}::timestamp, {_literal(identifier)})"


def event_position(row: dict) -> Position:
    return row["created_at"], row["id"]


class PostgresSource:
    # VibeInsight populates repo_hostname/repo_path from the Git remote when it is known.
    REPO = """CASE WHEN NULLIF(btrim(repo_path), '') IS NULL THEN '(无仓库)'
                   ELSE COALESCE(NULLIF(lower(btrim(repo_hostname)), ''), '(本机)')
                      || COALESCE(':' || repo_port::text,'')
                      || '/' || trim(both '/' from btrim(repo_path)) END"""
    PROMPT = "event_type='trace.started' AND NULLIF(btrim(message),'') IS NOT NULL"

    def __init__(self, config: dict, password: str):
        self.config = config
        self.password = password

    def _query(self, sql: str) -> list:
        config = self.config
        env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
        env.update(PGPASSWORD=self.password, PGCONNECT_TIMEOUT="5")
        args = [config["psql"], "--no-psqlrc", "--no-password", "--quiet", "--tuples-only",
                "--no-align", "--set=ON_ERROR_STOP=1", f"--host={config['host']}",
                f"--port={config['port']}", f"--dbname={config['database']}", f"--username={config['user']}"]
        transaction = ("BEGIN READ ONLY; SET LOCAL statement_timeout='25s'; "
                       "SET LOCAL standard_conforming_strings=on; " + sql + "; COMMIT;")
        try:
            result = subprocess.run(args, input=transaction, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", env=env, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("VibeInsight 查询超时") from exc
        except OSError as exc:
            raise RuntimeError("无法启动 PostgreSQL 客户端 psql") from exc
        if result.returncode:
            lines = [line for line in result.stderr.splitlines() if line.strip()]
            reason = lines[0] if lines else f"退出码 {result.returncode}"
            if self.password:
                reason = reason.replace(self.password, "***")
            raise RuntimeError(f"VibeInsight 查询失败：{reason[:400]}")
        return [json.loads(line) for line in result.stdout.split("\n") if line.strip()]

    def projects(self, through: Position | None = None) -> list[str]:
        bound = "" if through is None else f" AND (created_at,id)<={_position_sql(through)}"
        return self._query(f"SELECT to_json(project) FROM (SELECT DISTINCT {self.REPO} AS project "
                           f"FROM fact_events WHERE {self.PROMPT}{bound}) projects ORDER BY project")

    def upper(self) -> Position | None:
        bounds = self._query("""
            SELECT json_build_array(created_at,id) FROM fact_events ORDER BY created_at DESC,id DESC LIMIT 1
        """)
        return tuple(bounds[0]) if bounds else None

    def page(self, project: str, after: Position | None, through: Position, limit: int) -> list[dict]:
        lower = "" if after is None else f"AND (e.created_at,e.id)>{_position_sql(after)}"
        upper = _position_sql(through)
        # Assistant events may lack repo metadata. Resolve the project via a user prompt in the same session.
        return self._query(f"""
            WITH candidates AS MATERIALIZED (
                SELECT DISTINCT user_id,platform_code,session_id FROM fact_events
                WHERE {self.PROMPT} AND (created_at,id)<={upper} AND ({self.REPO})={_literal(project)}
            ), sessions AS MATERIALIZED (
                SELECT c.* FROM candidates c
                JOIN LATERAL (
                    SELECT {self.REPO} AS project FROM fact_events
                    WHERE session_id=c.session_id AND user_id IS NOT DISTINCT FROM c.user_id
                      AND platform_code=c.platform_code AND {self.PROMPT} AND (created_at,id)<={upper}
                    ORDER BY (NULLIF(btrim(repo_path),'') IS NULL),event_timestamp,id LIMIT 1
                ) chosen ON chosen.project={_literal(project)}
            )
            SELECT row_to_json(page) FROM (
                SELECT e.id,e.created_at,e.user_id,e.platform_code,e.session_id,e.trace_id,
                       e.event_type,e.event_timestamp,e.message
                FROM fact_events e JOIN sessions s
                    ON e.session_id=s.session_id AND e.platform_code=s.platform_code
                       AND e.user_id IS NOT DISTINCT FROM s.user_id
                WHERE (e.created_at,e.id)<={upper} {lower}
                  AND e.event_type IN ('trace.started','trace.completed')
                  AND NULLIF(btrim(e.message),'') IS NOT NULL
                ORDER BY e.created_at,e.id LIMIT {int(limit)}
            ) page
        """)


class VibeInsightSync:
    def __init__(self, db: Archive, source_id: str, *, batch_size: int = BATCH_SIZE):
        self.db = db
        self.source_id = source_id
        self.batch_size = batch_size
        self.projects = HubProjects(db)
        with db.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS hub_vibeinsight_cursors (
                    source_id TEXT NOT NULL, project TEXT NOT NULL, timestamp TEXT NOT NULL,
                    event_id TEXT NOT NULL, PRIMARY KEY(source_id,project)
                );
                CREATE TABLE IF NOT EXISTS hub_vibeinsight_messages (
                    id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL, trace_key TEXT NOT NULL
                );
            """)

    def run(self, source: Source, *, stopped=lambda: False) -> None:
        try:
            end = source.upper()
            if end is not None:
                for project in source.projects(end):
                    if stopped():
                        return
                    self._sync_project(source, project, end, stopped)
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            record_failure(self.db, exc)
            raise
        if not stopped():
            self.db._save_settings({"vibeinsight_last_success": datetime.now(UTC).isoformat(),
                                    "vibeinsight_error": None})

    def _sync_project(self, source: Source, project: str, end: Position, stopped) -> None:
        with self.db.connect() as con:
            saved = con.execute("""
                SELECT timestamp,event_id FROM hub_vibeinsight_cursors WHERE source_id=? AND project=?
            """, (self.source_id, project)).fetchone()
        committed = tuple(saved) if saved else None
        after = ((datetime.fromisoformat(committed[0]) - OVERLAP).isoformat(), "") if committed else None
        while not stopped():
            rows = source.page(project, after, end, self.batch_size)
            if stopped():
                return
            next_position = event_position(rows[-1]) if rows else end
            if next_position > end or (rows and after is not None and next_position <= after):
                raise RuntimeError("VibeInsight 返回了无效的分页位置")
            complete = len(rows) < self.batch_size or next_position == end
            processed = end if complete else next_position
            checkpoint = max(committed, processed) if committed else processed
            self._commit(project, rows, checkpoint)
            if complete:
                return
            committed, after = checkpoint, next_position

    def _commit(self, project: str, rows: list[dict], cursor: Position) -> None:
        with self.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            project_id = self.projects.upsert(con, SOURCE, self.source_id, project, project)
            changed: set[int] = set()
            for row in rows:
                conversation = self._archive(con, row, project_id)
                if conversation is not None:
                    changed.add(conversation)
            for conversation in changed:
                ordering = con.execute("""
                    SELECT id FROM (
                        SELECT m.id,m.role,m.timestamp,v.trace_key,v.event_id,
                          MIN(CASE WHEN m.role='user' THEN m.timestamp END)
                            OVER (PARTITION BY v.trace_key) AS prompt_time,
                          MIN(m.timestamp) OVER (PARTITION BY v.trace_key) AS first_event
                        FROM messages m JOIN hub_vibeinsight_messages v ON m.id=v.id
                        WHERE m.conversation_id=?
                    )
                    ORDER BY COALESCE(prompt_time,first_event),trace_key,
                             CASE role WHEN 'user' THEN 0 ELSE 1 END,timestamp,event_id
                """, (conversation,)).fetchall()
                con.executemany("UPDATE messages SET position=? WHERE id=?",
                                ((number, row[0]) for number, row in enumerate(ordering, 1)))
                self.db._reindex(con, conversation)
            con.execute("""
                INSERT INTO hub_vibeinsight_cursors(source_id,project,timestamp,event_id)
                VALUES(?,?,?,?) ON CONFLICT(source_id,project) DO UPDATE
                SET timestamp=excluded.timestamp,event_id=excluded.event_id
                WHERE (excluded.timestamp,excluded.event_id)>(timestamp,event_id)
            """, (self.source_id, project, *cursor))

    def _archive(self, con, row: dict, project_id: int) -> int | None:
        role = {"trace.started": "user", "trace.completed": "assistant"}.get(row["event_type"])
        if role is None or not (row["message"] or "").strip():
            return None
        identifier = json.dumps([self.source_id, row["user_id"], row["platform_code"], row["session_id"]],
                                ensure_ascii=False, separators=(",", ":"))
        timestamp = row["event_timestamp"]
        con.execute("""
            INSERT OR IGNORE INTO conversations(source,source_session_id,source_path,started_at,updated_at)
            VALUES(?,?,?,?,?)
        """, (SOURCE, identifier, "", timestamp, timestamp))
        conversation = con.execute("SELECT id FROM conversations WHERE source=? AND source_session_id=?",
                                   (SOURCE, identifier)).fetchone()[0]
        trace_key = row["trace_id"] or row["id"]
        source_key = json.dumps([trace_key, role], ensure_ascii=False)
        saved = con.execute("""
            INSERT INTO messages(conversation_id,source_key,position,role,text,timestamp) VALUES(?,?,0,?,?,?)
            ON CONFLICT(conversation_id,source_key) DO NOTHING RETURNING id
        """, (conversation, source_key, role, row["message"], timestamp)).fetchone()
        self.projects.assign(con, conversation, SOURCE, self.source_id, project_id)
        if saved is None:
            return None
        con.execute("INSERT INTO hub_vibeinsight_messages(id,event_id,trace_key) VALUES(?,?,?)",
                    (saved[0], row["id"], trace_key))
        con.execute("""
            UPDATE conversations SET started_at=MIN(started_at,?),updated_at=MAX(updated_at,?) WHERE id=?
        """, (timestamp, timestamp, conversation))
        return conversation

def record_failure(archive: Archive, error: Exception) -> None:
    reason = str(error)[:500]
    archive._save_settings({
        "vibeinsight_error": reason,
        "vibeinsight_last_failure": {"at": datetime.now(UTC).isoformat(), "reason": reason},
    })

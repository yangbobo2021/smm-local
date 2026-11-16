# SPDX-License-Identifier: Apache-2.0
"""Read-only VibeInsight ingestion with durable archive checkpoints."""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import subprocess
import tempfile
import time
from collections import defaultdict
from contextlib import closing
from datetime import UTC, datetime, timedelta
from threading import Event, Thread
from typing import Protocol

from ._archive import Archive
from .projects import HubProjects

Position = tuple[str, str]
SOURCE = "vibeinsight"
OVERLAP = timedelta(hours=24)
BATCH_SIZE = 500


class Source(Protocol):
    def validate(self) -> None: ...
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
    UNASSIGNED = "(无仓库)"
    PROMPT = "event_type='trace.started' AND NULLIF(btrim(message),'') IS NOT NULL"

    @classmethod
    def _repo(cls, alias: str = "") -> str:
        return f"""CASE WHEN NULLIF(btrim({alias}repo_path), '') IS NULL THEN '{cls.UNASSIGNED}'
                   ELSE COALESCE(NULLIF(lower(btrim({alias}repo_hostname)), ''), '(本机)')
                      || COALESCE(':' || {alias}repo_port::text,'')
                      || '/' || trim(both '/' from btrim({alias}repo_path)) END"""

    def __init__(self, config: dict, password: str):
        self.config = config
        self.password = password

    def _command(self) -> tuple[list[str], dict[str, str]]:
        config = self.config
        env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
        env.update(PGPASSWORD=self.password, PGCONNECT_TIMEOUT="5")
        args = [config["psql"], "--no-psqlrc", "--no-password", "--quiet", "--tuples-only",
                "--no-align", "--set=ON_ERROR_STOP=1", f"--host={config['host']}",
                f"--port={config['port']}", f"--dbname={config['database']}", f"--username={config['user']}"]
        return args, env

    @staticmethod
    def _transaction(sql: str, timeout: str) -> str:
        return (f"BEGIN READ ONLY; SET LOCAL statement_timeout='{timeout}'; "
                "SET LOCAL standard_conforming_strings=on; " + sql + "; COMMIT;")

    def _error(self, code: int, stderr: str) -> RuntimeError:
        lines = [line for line in stderr.splitlines() if line.strip()]
        reason = lines[0] if lines else f"退出码 {code}"
        if self.password:
            reason = reason.replace(self.password, "***")
        return RuntimeError(f"VibeInsight 查询失败：{reason[:400]}")

    def _query(self, sql: str) -> list:
        args, env = self._command()
        transaction = self._transaction(sql, "25s")
        try:
            result = subprocess.run(args, input=transaction, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", env=env, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("VibeInsight 查询超时") from exc
        except OSError as exc:
            raise RuntimeError("无法启动 PostgreSQL 客户端 psql") from exc
        if result.returncode:
            raise self._error(result.returncode, result.stderr)
        return [json.loads(line) for line in result.stdout.split("\n") if line.strip()]

    def validate(self) -> None:
        # PostgreSQL checks privileges on every referenced column even with LIMIT 0.
        self._query("""
            SELECT row_to_json(probe) FROM (
                SELECT id,created_at,user_id,platform_code,session_id,trace_id,event_type,
                       event_timestamp,message,repo_hostname,repo_port,repo_path FROM fact_events LIMIT 0
            ) probe
        """)

    def projects(self, through: Position | None = None) -> list[str]:
        bound = "" if through is None else f" AND (created_at,id)<={_position_sql(through)}"
        return self._query(f"""
            SELECT to_json(project) FROM (
                SELECT DISTINCT {self._repo()} AS project FROM fact_events
                WHERE event_type IN ('trace.started','trace.completed')
                  AND NULLIF(btrim(message),'') IS NOT NULL {bound}
                UNION SELECT '{self.UNASSIGNED}'
            ) projects ORDER BY project
        """)

    def upper(self) -> Position | None:
        bounds = self._query("""
            SELECT json_build_array(created_at,id) FROM fact_events ORDER BY created_at DESC,id DESC LIMIT 1
        """)
        return tuple(bounds[0]) if bounds else None

    def _events_sql(self, after: Position | None, through: Position) -> tuple[str, str]:
        lower = "" if after is None else f"AND (e.created_at,e.id)>{_position_sql(after)}"
        upper = _position_sql(through)
        # A trace's prompt supplies its project. If no matching prompt has
        # usable project metadata, retain the known reply or session project.
        common = f"""
            WITH prompts AS MATERIALIZED (
                SELECT user_id,platform_code,session_id,{self._repo()} AS project
                FROM fact_events WHERE {self.PROMPT} AND (created_at,id)<={upper}
            ), sessions AS (
                SELECT user_id,platform_code,session_id,
                    CASE WHEN COUNT(DISTINCT project)=1 THEN MIN(project) END AS sole_project
                FROM prompts GROUP BY user_id,platform_code,session_id
            ), trace_projects AS (
                SELECT DISTINCT ON (user_id,platform_code,session_id,COALESCE(trace_id,id))
                       user_id,platform_code,session_id,COALESCE(trace_id,id) AS trace_key,
                       {self._repo()} AS project
                FROM fact_events
                WHERE (created_at,id)<={upper} AND NULLIF(btrim(repo_path),'') IS NOT NULL
                  AND event_type IN ('trace.started','trace.completed')
                ORDER BY user_id,platform_code,session_id,COALESCE(trace_id,id),
                         (event_type<>'trace.started'),event_timestamp,id
            ), events AS (
                SELECT e.id,e.created_at,e.user_id,e.platform_code,e.session_id,e.trace_id,
                       e.event_type,e.event_timestamp,e.message,
                       COALESCE(t.project,NULLIF({self._repo("e.")},'{self.UNASSIGNED}'),
                                s.sole_project,'{self.UNASSIGNED}') AS project
                FROM fact_events e JOIN sessions s
                    ON e.session_id=s.session_id AND e.platform_code=s.platform_code
                       AND e.user_id IS NOT DISTINCT FROM s.user_id
                LEFT JOIN trace_projects t ON t.session_id=e.session_id AND t.platform_code=e.platform_code
                    AND t.user_id IS NOT DISTINCT FROM e.user_id AND t.trace_key=COALESCE(e.trace_id,e.id)
                WHERE (e.created_at,e.id)<={upper} {lower}
                  AND e.event_type IN ('trace.started','trace.completed')
                  AND NULLIF(btrim(e.message),'') IS NOT NULL
            )
        """
        return common, "ORDER BY created_at,id"

    def page(self, project: str, after: Position | None, through: Position, limit: int) -> list[dict]:
        common, order = self._events_sql(after, through)
        return self._query(f"""
            {common}
            SELECT to_jsonb(events)-'project' FROM events WHERE project={_literal(project)}
            {order} LIMIT {int(limit)}
        """)

    def stream(self, after: Position | None, through: Position, *, stopped=lambda: False):
        common, order = self._events_sql(after, through)
        sql = f"""
            COPY (
                {common}
                SELECT replace(encode(convert_to(row_to_json(events)::text,'UTF8'),'base64'),
                               E'\\n','') FROM events {order}
            ) TO STDOUT
        """
        args, env = self._command()
        transaction = self._transaction(sql, "0").encode("utf-8")
        with tempfile.TemporaryFile() as contents, tempfile.TemporaryFile() as errors:
            contents.write(transaction)
            contents.seek(0)
            with subprocess.Popen(args, stdin=contents, stdout=subprocess.PIPE, stderr=errors, env=env) as process:
                assert process.stdout is not None
                finished = Event()
                last_output = time.monotonic()

                def interrupt():
                    while not finished.wait(0.25):
                        if stopped() or time.monotonic() - last_output >= 300:
                            if process.poll() is None:
                                process.kill()
                            return

                watcher = Thread(target=interrupt, daemon=True)
                watcher.start()
                try:
                    for line in process.stdout:
                        last_output = time.monotonic()
                        if stopped():
                            return
                        if line.strip():
                            yield json.loads(base64.b64decode(line))
                    code = process.wait()
                    if code != 0 and not stopped():
                        errors.seek(0)
                        raise self._error(code, errors.read().decode("utf-8", errors="replace"))
                finally:
                    finished.set()
                    watcher.join()
                    if process.poll() is None:
                        process.kill()



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
            """)

    def run(self, source: Source, *, stopped=lambda: False) -> None:
        try:
            end = source.upper()
            if end is not None:
                projects = source.projects(end)
                if callable(stream := getattr(source, "stream", None)):
                    self._sync_stream(stream, projects, end, stopped)
                else:
                    for project in projects:
                        if stopped():
                            return
                        self._sync_project(source, project, end, stopped)
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            record_failure(self.db, exc)
            raise
        if not stopped():
            self.db._save_settings({"vibeinsight_last_success": datetime.now(UTC).isoformat(),
                                    "vibeinsight_error": None})

    def _sync_stream(self, stream, projects: list[str], end: Position, stopped) -> None:
        with self.db.connect() as con:
            checkpoints = {row[0]: (row[1], row[2]) for row in con.execute("""
                SELECT project,timestamp,event_id FROM hub_vibeinsight_cursors WHERE source_id=?
            """, (self.source_id,))}
        lower_bounds = {
            project: ((datetime.fromisoformat(checkpoints[project][0]) - OVERLAP).isoformat(), "")
            for project in projects if project in checkpoints
        }
        after = min(lower_bounds.values()) if lower_bounds and len(lower_bounds) == len(projects) else None
        known_projects = set(projects)
        queued: dict[str, list[dict]] = defaultdict(list)
        size = 0

        def flush():
            for project, rows in queued.items():
                self._commit(project, rows, event_position(rows[-1]))
            queued.clear()

        if not projects or stopped():
            return
        previous = after
        with closing(stream(after, end, stopped=stopped)) as rows:
            for row in rows:
                if stopped():
                    return
                position = event_position(row)
                if position > end or (previous is not None and position <= previous):
                    raise RuntimeError("VibeInsight 返回了无效的流式同步位置")
                previous = position
                project = row["project"]
                # Discovery and COPY are separate snapshots. A later-visible
                # project needs its history before it can have a checkpoint.
                if project not in known_projects:
                    continue
                if project in lower_bounds and position <= lower_bounds[project]:
                    continue
                queued[project].append(row)
                size += 1
                if size == self.batch_size:
                    flush()
                    size = 0
        if not stopped():
            flush()
            for project in projects:
                self._commit(project, [], end)

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
            changed: set[int] = set()
            if rows:
                project_id = self.projects.upsert(con, SOURCE, self.source_id, project, project)
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
                self.projects.reindex(con, conversation)
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
        if saved is None:
            return self._reassign_provenance(con, conversation, source_key, row["id"], project_id)
        self.projects.assign(con, conversation, SOURCE, self.source_id, project_id)
        con.execute("""
            INSERT INTO hub_vibeinsight_messages(id,project_id,event_id,trace_key) VALUES(?,?,?,?)
        """, (saved[0], project_id, row["id"], trace_key))
        con.execute("""
            UPDATE conversations SET started_at=MIN(started_at,?),updated_at=MAX(updated_at,?) WHERE id=?
        """, (timestamp, timestamp, conversation))
        return conversation

    def _reassign_provenance(self, con, conversation: int, key: str, event: str, project: int) -> int | None:
        previous = con.execute("""
            SELECT v.id,v.project_id FROM messages m JOIN hub_vibeinsight_messages v ON v.id=m.id
            WHERE m.conversation_id=? AND m.source_key=? AND v.event_id=? AND v.project_id<>?
        """, (conversation, key, event, project)).fetchone()
        if previous is None:
            return None
        con.execute("UPDATE hub_vibeinsight_messages SET project_id=? WHERE id=?", (project, previous[0]))
        self.projects.assign(con, conversation, SOURCE, self.source_id, project)
        con.execute("""
            DELETE FROM hub_project_memberships
            WHERE conversation_id=? AND kind=? AND owner=? AND project_id=?
              AND NOT EXISTS(SELECT 1 FROM hub_project_messages existing
                             WHERE existing.conversation_id=hub_project_memberships.conversation_id
                               AND existing.project_id=hub_project_memberships.project_id)
        """, (conversation, SOURCE, self.source_id, previous[1]))
        return conversation


def record_failure(archive: Archive, error: Exception) -> None:
    reason = str(error)[:500]
    archive._save_settings({
        "vibeinsight_error": reason,
        "vibeinsight_last_failure": {"at": datetime.now(UTC).isoformat(), "reason": reason},
    })

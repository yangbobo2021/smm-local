"""Durable archive, Codex import adapter, project graph, and lexical search."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .importers.base import SourceAdapter
from .importers.codex import CodexAdapter
from .importers.claude_code import ClaudeCodeAdapter
from .importers.source_io import open_source


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_db_path() -> Path:
    return Path(os.environ.get("SMM_DB", "~/.local/share/smm-local/smm.sqlite3")).expanduser()


def shared_db_path() -> Path:
    manifest = Path.home() / ".local/share/smm-local/install.json"
    default_path = manifest.with_name("smm.sqlite3")
    if manifest.is_file():
        installation = json.loads(manifest.read_text(encoding="utf-8"))
        return Path(installation.get("db_path") or default_path).expanduser().resolve()
    return default_path.resolve()


def default_codex_root() -> Path:
    return Path(os.environ.get("SMM_CODEX_ROOT", "~/.codex/sessions")).expanduser()


def default_claude_root() -> Path:
    if override := os.environ.get("SMM_CLAUDE_ROOT"):
        return Path(override).expanduser()
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser() / "projects"


def project_path_for(cwd: str) -> str:
    """Use the nearest existing Git root, falling back to the recorded cwd."""
    path = Path(cwd).expanduser().absolute()
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return str(candidate)
    return str(path)


_PARTS = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*|[\u3400-\u9fff]+")


def tokens(text: str) -> list[str]:
    """Simple deterministic lexical terms; Chinese runs get 1/2-character terms."""
    out: list[str] = []
    for m in _PARTS.finditer(text.lower()):
        word = m.group()
        if "\u3400" <= word[0] <= "\u9fff":
            out.extend(word)
            out.extend(word[i : i + 2] for i in range(len(word) - 1))
        else:
            out.append(word)
    return out


def select_matched_messages(messages: list[sqlite3.Row], query_terms: list[str]) -> list[dict[str, Any]]:
    """Show relevant turns across a conversation, including the original question/reply."""
    if not messages:
        return []
    wanted = set(query_terms)
    term_counts = [Counter(tokens(message["text"])) for message in messages]
    lengths = [sum(counts.values()) for counts in term_counts]
    document_frequency = Counter(term for counts in term_counts for term in counts.keys() & wanted)
    average_length = max(1.0, sum(lengths) / len(lengths))
    scores = []
    for counts, length in zip(term_counts, lengths):
        score = 0.0
        for term in counts.keys() & wanted:
            frequency = counts[term]
            idf = math.log1p((len(messages) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average_length))
        scores.append(score)
    ranked = sorted((i for i, score in enumerate(scores) if score > 0), key=lambda i: (-scores[i], -i))
    if not ranked:
        return []
    if len(messages) <= 100:
        anchors = ranked[:3]
    else:
        # A long discussion can revisit the same subject years later. Reserve
        # places for both halves and the latest fifth, rather than allowing
        # earlier high-frequency messages to occupy every preview slot.
        halfway = len(messages) // 2
        recent_start = len(messages) * 4 // 5
        older = [i for i in ranked if i < halfway]
        newer = [i for i in ranked if i >= halfway]
        recent = [i for i in ranked if i >= recent_start]
        anchors = [ranked[0], *(part[0] for part in (older, newer) if part), *recent[:2]]
        anchors = list(dict.fromkeys(anchors))
    turn_starts = []
    current_start = 0
    for i, message in enumerate(messages):
        if message["role"] == "user":
            current_start = i
        turn_starts.append(current_start)
    selected = set(anchors)
    for anchor in anchors:
        start = turn_starts[anchor]
        end = next((i for i in range(anchor + 1, len(messages)) if messages[i]["role"] == "user"), len(messages))
        if messages[anchor]["role"] == "assistant" and messages[start]["role"] == "user":
            selected.add(start)
            replies = [i for i in range(start + 1, end) if messages[i]["role"] == "assistant"]
            if replies:
                selected.add(replies[-1])
        elif messages[anchor]["role"] == "user":
            replies = [i for i in range(anchor + 1, end) if messages[i]["role"] == "assistant"]
            if replies:
                selected.add(max(replies, key=lambda i: (scores[i], i)))
                selected.add(replies[-1])
    return [dict(messages[i]) for i in sorted(selected)]


def compact_message(message: dict[str, Any], query_terms: list[str], limit: int) -> dict[str, Any]:
    """Bound a search card while retaining source offsets for a full read."""
    body = message["text"]
    card = {key: value for key, value in message.items() if key != "text"}
    card["preview_truncated"] = len(body) > limit
    if len(body) <= limit:
        card["preview"] = body
        return card

    card["text_chars"] = len(body)

    terms = [term for term in query_terms if len(term) > 1]
    lowered = body.lower()
    hits: list[tuple[int, int, str]] = []
    for term in terms:
        start = 0
        while len(hits) < 1000:
            index = lowered.find(term, start)
            if index < 0:
                break
            hits.append((index, index + len(term), term))
            start = index + len(term)
    if not hits:
        ranges = [(0, limit)]
    else:
        # Choose two disjoint windows. Distinct query terms matter more than
        # repetition, and a late tie is useful for evolving conversations.
        width = (limit - 3) // 2
        candidates = {max(0, min(len(body) - width, start - width // 3)) for start, _, _ in hits}
        def score(start: int) -> tuple[int, int, int]:
            inside = [term for a, b, term in hits if a < start + width and b > start]
            return (len(set(inside)), len(inside), start)
        first = max(candidates, key=score)
        other = [start for start in candidates if start >= first + width or start + width <= first]
        ranges = [(first, first + width)]
        if other:
            second = max(other, key=score)
            ranges.append((second, second + width))
        else:
            start = max(0, min(len(body) - limit, first - width // 2))
            ranges = [(start, start + limit)]
    ranges.sort()
    card["preview_ranges"] = [[start, end] for start, end in ranges]
    card["preview"] = " … ".join(body[start:end] for start, end in ranges)
    return card


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class Archive:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or default_db_path()).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self._init()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path, timeout=30, factory=_ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
        return con

    def _init(self) -> None:
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                  id INTEGER PRIMARY KEY, name TEXT NOT NULL, confirmed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS project_paths (
                  path TEXT PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id)
                );
                CREATE TABLE IF NOT EXISTS project_links (
                  a INTEGER NOT NULL REFERENCES projects(id),
                  b INTEGER NOT NULL REFERENCES projects(id),
                  PRIMARY KEY(a,b), CHECK(a < b)
                );
                CREATE TABLE IF NOT EXISTS conversations (
                  id INTEGER PRIMARY KEY, source TEXT NOT NULL,
                  source_session_id TEXT NOT NULL, source_path TEXT NOT NULL,
                  cwd TEXT, project_path TEXT, project_id INTEGER REFERENCES projects(id),
                  started_at TEXT, updated_at TEXT, title TEXT NOT NULL DEFAULT '',
                  search_text TEXT NOT NULL DEFAULT '',
                  UNIQUE(source,source_session_id)
                );
                CREATE TABLE IF NOT EXISTS messages (
                  id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                  source_key TEXT NOT NULL, position INTEGER NOT NULL,
                  role TEXT NOT NULL, text TEXT NOT NULL, timestamp TEXT,
                  UNIQUE(conversation_id,source_key)
                );
                CREATE INDEX IF NOT EXISTS messages_conversation_order ON messages(conversation_id,position);
                CREATE INDEX IF NOT EXISTS conversations_project ON conversations(project_id);
                CREATE TABLE IF NOT EXISTS source_files (
                  path TEXT PRIMARY KEY, source TEXT NOT NULL DEFAULT 'codex', source_session_id TEXT,
                  byte_offset INTEGER NOT NULL DEFAULT 0,
                  size INTEGER NOT NULL DEFAULT 0, mtime_ns INTEGER NOT NULL DEFAULT 0,
                  inode INTEGER NOT NULL DEFAULT 0, head_hash TEXT,
                  last_synced_at TEXT, error TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS conversation_fts USING fts5(terms, tokenize='unicode61');
            """)
            columns = {row[1] for row in con.execute("PRAGMA table_info(conversations)")}
            if "project_path" not in columns:
                con.execute("ALTER TABLE conversations ADD COLUMN project_path TEXT")
            source_columns = {row[1] for row in con.execute("PRAGMA table_info(source_files)")}
            if "source" not in source_columns:
                con.execute("ALTER TABLE source_files ADD COLUMN source TEXT NOT NULL DEFAULT 'codex'")
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('message_sequence','0')")
            con.execute("""
                UPDATE settings SET value=MAX(CAST(value AS INTEGER),
                    COALESCE((SELECT MAX(id) FROM messages),0))
                WHERE key='message_sequence'
            """)
            con.execute("""
                CREATE TRIGGER IF NOT EXISTS advance_message_sequence AFTER INSERT ON messages
                BEGIN
                    UPDATE settings SET value=MAX(CAST(value AS INTEGER),new.id)
                    WHERE key='message_sequence';
                END
            """)
            if not con.execute("SELECT 1 FROM schema_migrations WHERE name='codex-injected-context-v1'").fetchone():
                predicate = "m.text LIKE '# AGENTS.md instructions for %' OR m.text LIKE '<environment_context>%' OR m.text LIKE '<external_codex_apps_open_page>%'"
                affected = [r[0] for r in con.execute(
                    f"SELECT DISTINCT m.conversation_id FROM messages m JOIN conversations c ON c.id=m.conversation_id WHERE c.source='codex' AND m.role='user' AND ({predicate})")]
                con.execute(f"DELETE FROM messages WHERE role='user' AND conversation_id IN (SELECT id FROM conversations WHERE source='codex') AND ({predicate.replace('m.text', 'text')})")
                for conversation_id in affected:
                    self._reindex(con, conversation_id)
                con.execute("INSERT INTO schema_migrations(name,applied_at) VALUES(?,?)", ("codex-injected-context-v1", utcnow()))
            if not con.execute("SELECT 1 FROM schema_migrations WHERE name='codex-injected-context-v2'").fetchone():
                predicate = "text LIKE '<recommended_plugins>%' OR text LIKE '<skill>%'"
                affected = [r[0] for r in con.execute(
                    f"SELECT DISTINCT conversation_id FROM messages WHERE role='user' AND ({predicate})")]
                con.execute(f"DELETE FROM messages WHERE role='user' AND ({predicate})")
                for conversation_id in affected:
                    self._reindex(con, conversation_id)
                con.execute("INSERT INTO schema_migrations(name,applied_at) VALUES(?,?)", ("codex-injected-context-v2", utcnow()))

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as con:
            rows = con.execute("SELECT key,value FROM settings WHERE key NOT IN ('last_sync_result', 'hub_identity', 'message_sequence') AND key NOT LIKE 'hub_cursor:%'").fetchall()
        result: dict[str, Any] = {r["key"]: json.loads(r["value"]) for r in rows}
        result.setdefault("codex_root", str(default_codex_root()))
        result.setdefault("claude_root", str(default_claude_root()))
        result.setdefault("sync_interval_seconds", 60)
        result.setdefault("sync_paused", False)
        return result

    def set_settings(self, *, codex_root: str | None = None, claude_root: str | None = None,
                     sync_interval_seconds: int | None = None, sync_paused: bool | None = None) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if codex_root is not None:
            p = Path(codex_root).expanduser().resolve()
            if not p.is_dir():
                raise ValueError("Codex 会话目录不存在")
            updates["codex_root"] = str(p)
        if claude_root is not None:
            p = Path(claude_root).expanduser().resolve()
            if not p.is_dir():
                raise ValueError("Claude Code 会话目录不存在")
            updates["claude_root"] = str(p)
        if sync_interval_seconds is not None:
            if not 10 <= sync_interval_seconds <= 3600:
                raise ValueError("同步间隔必须在 10 到 3600 秒之间")
            updates["sync_interval_seconds"] = sync_interval_seconds
        if sync_paused is not None:
            updates["sync_paused"] = sync_paused
        self._save_settings(updates)
        return self.get_settings()

    def _save_settings(self, updates: dict[str, Any]) -> None:
        with self.connect() as con:
            for key, value in updates.items():
                con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    def record_sync_result(self, result: dict[str, Any]) -> None:
        self._save_settings({"last_sync_result": result})

    def last_sync_result(self) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute("SELECT value FROM settings WHERE key='last_sync_result'").fetchone()
        return json.loads(row[0]) if row else None

    def _project_for_path(self, con: sqlite3.Connection, cwd: str | None) -> int | None:
        if not cwd:
            return None
        path = project_path_for(cwd)
        for candidate in (Path(path), *Path(path).parents):
            existing = con.execute("SELECT project_id FROM project_paths WHERE path=?", (str(candidate),)).fetchone()
            if existing:
                return int(existing[0])
        name = Path(path).name or path
        cur = con.execute("INSERT INTO projects(name) VALUES(?)", (name,))
        project_id = int(cur.lastrowid)
        con.execute("INSERT INTO project_paths(path,project_id) VALUES(?,?)", (path, project_id))
        return project_id

    def sync_codex(self, root: Path | str | None = None) -> dict[str, Any]:
        root_path = Path(root or self.get_settings()["codex_root"]).expanduser()
        return self.sync_source(CodexAdapter(), root_path)

    def sync_claude(self, root: Path | str | None = None) -> dict[str, Any]:
        root_path = Path(root or self.get_settings()["claude_root"]).expanduser()
        return self.sync_source(ClaudeCodeAdapter(), root_path)

    def sync_all(self) -> dict[str, Any]:
        settings = self.get_settings()
        sources = {"codex": (CodexAdapter(), Path(settings["codex_root"]).expanduser()),
                   "claude-code": (ClaudeCodeAdapter(), Path(settings["claude_root"]).expanduser())}
        result: dict[str, Any] = {"sources": {}, "files_seen": 0, "files_changed": 0,
                                  "conversations_new": 0, "messages_new": 0, "errors": [], "finished_at": None}
        for name, (adapter, root) in sources.items():
            if not root.is_dir():
                result["sources"][name] = {"available": False, "root": str(root), "reason": "目录不存在"}
                continue
            one = self.sync_source(adapter, root)
            result["sources"][name] = {**one, "available": True}
            for field in ("files_seen", "files_changed", "conversations_new", "messages_new"):
                result[field] += one[field]
            result["errors"].extend(one["errors"])
        result["finished_at"] = utcnow()
        return result

    def sync_source(self, adapter: SourceAdapter, root_path: Path) -> dict[str, Any]:
        if not root_path.is_dir():
            raise ValueError(f"会话目录不存在: {root_path}")
        result = {"root": str(root_path), "files_seen": 0, "files_changed": 0, "conversations_new": 0, "messages_new": 0, "errors": [], "finished_at": None}
        with self._write_lock:
            for path in adapter.discover(root_path):
                result["files_seen"] += 1
                try:
                    outcome = self._sync_file(path, adapter)
                    if outcome["changed"]:
                        result["files_changed"] += 1
                    result["conversations_new"] += outcome["conversations_new"]
                    result["messages_new"] += outcome["messages_new"]
                    if outcome["error"]:
                        result["errors"].append({"path": str(path), "error": outcome["error"]})
                except (OSError, sqlite3.Error, ValueError) as exc:
                    result["errors"].append({"path": str(path), "error": str(exc)})
            result["finished_at"] = utcnow()
        return result

    def _sync_file(self, path: Path, adapter: SourceAdapter) -> dict[str, Any]:
        stat = path.stat()
        with self.connect() as con:
            previous = con.execute("SELECT * FROM source_files WHERE path=?", (str(path),)).fetchone()
            if previous and previous["size"] == stat.st_size and previous["mtime_ns"] == stat.st_mtime_ns and not previous["error"]:
                return {"changed": False, "conversations_new": 0, "messages_new": 0, "error": None}
            with open_source(path) as stream:
                head_hash = hashlib.sha256(stream.readline()).hexdigest()
            # Positions and fallback message keys always use decompressed byte
            # offsets, so compression/relocation preserves their identities.
            # Changed compressed files are replayed: physical size is unrelated
            # to the saved logical offset, and a rewrite may change earlier data.
            reset = path.name.endswith(".jsonl.zst") or not previous or previous["source"] != adapter.name or stat.st_size < previous["byte_offset"] or previous["inode"] != stat.st_ino or previous["head_hash"] != head_hash
            offset = 0 if reset else int(previous["byte_offset"])
            source_session_id = None if reset else previous["source_session_id"]
            created = 0
            messages_new = 0
            changed_conversations: set[int] = set()
            error: str | None = None
            fallback_session_id = path.name.removesuffix(".zst").removesuffix(".jsonl")
            with open_source(path) as stream:
                if offset:
                    stream.seek(offset)
                while True:
                    line_start = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    if not line.endswith(b"\n"):
                        error = "末尾 JSONL 尚未写完，等待下次同步"
                        offset = line_start
                        break
                    try:
                        item = json.loads(line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        error = f"JSONL 第 {line_start} 字节解析失败"
                        offset = line_start
                        break
                    normalized = adapter.normalize(item, line_start)
                    if normalized and normalized["kind"] == "session":
                        source_session_id = str(normalized.get("session_id") or fallback_session_id)
                        cwd = normalized.get("cwd") if isinstance(normalized.get("cwd"), str) else None
                        project_path = project_path_for(cwd) if cwd else None
                        project_id = self._project_for_path(con, cwd)
                        existing = con.execute("SELECT id FROM conversations WHERE source=? AND source_session_id=?", (adapter.name,source_session_id)).fetchone()
                        if existing is None:
                            con.execute("INSERT INTO conversations(source,source_session_id,source_path,cwd,project_path,project_id,started_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (adapter.name, source_session_id, str(path), cwd, project_path, project_id, normalized.get("timestamp"), normalized.get("timestamp")))
                            created += 1
                        else:
                            con.execute("UPDATE conversations SET source_path=?,cwd=?,project_path=?,project_id=? WHERE id=?", (str(path), cwd, project_path, project_id, existing["id"]))
                    elif normalized and normalized["kind"] == "message":
                        if not source_session_id:
                            source_session_id = str(normalized.get("session_id") or fallback_session_id)
                            cwd = normalized.get("cwd") if isinstance(normalized.get("cwd"), str) else None
                            project_path = project_path_for(cwd) if cwd else None
                            project_id = self._project_for_path(con, cwd)
                            existing = con.execute("SELECT id FROM conversations WHERE source=? AND source_session_id=?", (adapter.name,source_session_id)).fetchone()
                            if existing is None:
                                con.execute("INSERT INTO conversations(source,source_session_id,source_path,cwd,project_path,project_id,started_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (adapter.name, source_session_id, str(path), cwd, project_path, project_id, normalized.get("timestamp"), normalized.get("timestamp")))
                                created += 1
                        conversation_id = int(con.execute("SELECT id FROM conversations WHERE source=? AND source_session_id=?", (adapter.name,source_session_id)).fetchone()[0])
                        cur = con.execute("""
                            INSERT INTO messages(id,conversation_id,source_key,position,role,text,timestamp)
                            VALUES((SELECT CAST(value AS INTEGER)+1 FROM settings WHERE key='message_sequence'),?,?,?,?,?,?)
                            ON CONFLICT(conversation_id,source_key) DO NOTHING
                        """, (conversation_id, normalized["key"], normalized["position"], normalized["role"],
                              normalized["text"], normalized.get("timestamp")))
                        if cur.rowcount:
                            messages_new += 1
                            changed_conversations.add(conversation_id)
                        con.execute("UPDATE conversations SET updated_at=? WHERE id=?", (normalized.get("timestamp"), conversation_id))
                if not error:
                    offset = stream.tell()
            for conversation_id in changed_conversations:
                self._reindex(con, conversation_id)
            con.execute("INSERT INTO source_files(path,source,source_session_id,byte_offset,size,mtime_ns,inode,head_hash,last_synced_at,error) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET source=excluded.source,source_session_id=excluded.source_session_id,byte_offset=excluded.byte_offset,size=excluded.size,mtime_ns=excluded.mtime_ns,inode=excluded.inode,head_hash=excluded.head_hash,last_synced_at=excluded.last_synced_at,error=excluded.error", (str(path), adapter.name, source_session_id, offset, stat.st_size, stat.st_mtime_ns, stat.st_ino, head_hash, utcnow(), error))
        return {"changed": True, "conversations_new": created, "messages_new": messages_new, "error": error}

    def _reindex(self, con: sqlite3.Connection, conversation_id: int) -> None:
        messages = con.execute("SELECT role,text FROM messages WHERE conversation_id=? ORDER BY position,id", (conversation_id,)).fetchall()
        text = "\n".join(row["text"] for row in messages)
        title = next((row["text"].strip().splitlines()[0][:120] for row in messages if row["role"] == "user"), "(无用户消息)")
        con.execute("UPDATE conversations SET search_text=?,title=? WHERE id=?", (text, title, conversation_id))
        con.execute("DELETE FROM conversation_fts WHERE rowid=?", (conversation_id,))
        con.execute("INSERT INTO conversation_fts(rowid,terms) VALUES(?,?)", (conversation_id, " ".join(tokens(text))))

    def status(self) -> dict[str, Any]:
        with self.connect() as con:
            counts = {"projects": con.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
                      "source_files": con.execute("SELECT COUNT(*) FROM source_files").fetchone()[0]}
            errors = [dict(r) for r in con.execute("SELECT path,error,last_synced_at FROM source_files WHERE error IS NOT NULL ORDER BY last_synced_at DESC LIMIT 20")]
            last_sync = con.execute("SELECT MAX(last_synced_at) FROM source_files").fetchone()[0]
            by_source = {r["source"]: {"conversations": r["conversations"], "messages": r["messages"]}
                         for r in con.execute("""
                SELECT c.source, COUNT(*) AS conversations, SUM(
                    (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id)
                ) AS messages
                FROM conversations c GROUP BY c.source
            """)}
            for key in ("conversations", "messages"):
                counts[key] = sum(source[key] for source in by_source.values())
        return {**counts, "by_source": by_source, "last_sync": last_sync, "errors": errors, "settings": self.get_settings()}

    def projects(self) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT p.*,COUNT(DISTINCT c.id) AS conversations FROM projects p LEFT JOIN conversations c ON c.project_id=p.id GROUP BY p.id ORDER BY conversations DESC,p.name,p.id").fetchall()
            out = []
            for row in rows:
                project = dict(row)
                project["paths"] = [r[0] for r in con.execute("SELECT path FROM project_paths WHERE project_id=? ORDER BY path", (row["id"],))]
                project["linked_ids"] = [r[0] for r in con.execute("SELECT CASE WHEN a=? THEN b ELSE a END FROM project_links WHERE a=? OR b=? ORDER BY 1", (row["id"],row["id"],row["id"]))]
                out.append(project)
        return out

    def rename_project(self, project_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("项目名不能为空")
        with self.connect() as con:
            cur = con.execute("UPDATE projects SET name=?,confirmed=1 WHERE id=?", (name.strip(), project_id))
            if not cur.rowcount:
                raise ValueError("项目不存在")

    def map_path(self, path: str, project_id: int) -> None:
        canonical = str(Path(path).expanduser().absolute())
        with self.connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("项目不存在")
            con.execute("INSERT INTO project_paths(path,project_id) VALUES(?,?) ON CONFLICT(path) DO UPDATE SET project_id=excluded.project_id", (canonical, project_id))
            for row in con.execute("SELECT path FROM project_paths"):
                if row["path"] != canonical and Path(row["path"]).is_relative_to(canonical):
                    con.execute("UPDATE project_paths SET project_id=? WHERE path=?", (project_id, row["path"]))
            for row in con.execute("SELECT id,project_path,cwd FROM conversations"):
                source_path = row["project_path"] or row["cwd"]
                if source_path and Path(source_path).is_relative_to(canonical):
                    con.execute("UPDATE conversations SET project_id=? WHERE id=?", (project_id, row["id"]))

    def link_projects(self, one: int, other: int, linked: bool = True) -> None:
        if one == other:
            raise ValueError("不能关联项目自身")
        a,b = sorted((one,other))
        with self.connect() as con:
            if con.execute("SELECT COUNT(*) FROM projects WHERE id IN (?,?)", (a,b)).fetchone()[0] != 2:
                raise ValueError("项目不存在")
            if linked:
                con.execute("INSERT OR IGNORE INTO project_links(a,b) VALUES(?,?)", (a,b))
            else:
                con.execute("DELETE FROM project_links WHERE a=? AND b=?", (a,b))

    def merge_projects(self, source_id: int, target_id: int) -> None:
        if source_id == target_id:
            raise ValueError("不能合并项目自身")
        with self.connect() as con:
            if con.execute("SELECT COUNT(*) FROM projects WHERE id IN (?,?)", (source_id,target_id)).fetchone()[0] != 2:
                raise ValueError("项目不存在")
            peers = [r[0] for r in con.execute("SELECT CASE WHEN a=? THEN b ELSE a END FROM project_links WHERE a=? OR b=?", (source_id,source_id,source_id))]
            con.execute("UPDATE project_paths SET project_id=? WHERE project_id=?", (target_id,source_id))
            con.execute("UPDATE conversations SET project_id=? WHERE project_id=?", (target_id,source_id))
            con.execute("DELETE FROM project_links WHERE a=? OR b=?", (source_id,source_id))
            for peer in peers:
                if peer != target_id:
                    a,b = sorted((peer,target_id))
                    con.execute("INSERT OR IGNORE INTO project_links(a,b) VALUES(?,?)", (a,b))
            con.execute("DELETE FROM projects WHERE id=?", (source_id,))

    def effective_projects(self, project_id: int) -> list[int]:
        with self.connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("项目不存在")
            linked = [r[0] for r in con.execute("SELECT CASE WHEN a=? THEN b ELSE a END FROM project_links WHERE a=? OR b=?", (project_id,project_id,project_id))]
        return [project_id] + sorted(linked)

    def resolve_project(self, cwd: str) -> dict[str, Any] | None:
        """Resolve the closest configured ancestor path without creating a project."""
        path = Path(cwd).expanduser().absolute()
        with self.connect() as con:
            for candidate in (path, *path.parents):
                row = con.execute("SELECT p.id,p.name,pp.path FROM project_paths pp JOIN projects p ON p.id=pp.project_id WHERE pp.path=?", (str(candidate),)).fetchone()
                if row:
                    return dict(row)
        return None

    def search(self, query: str, *, scope: str = "all", project_id: int | None = None, limit: int = 5, current_session_id: str | None = None, current_source: str | None = None, include_current: bool = False, preview_chars: int = 0, include_message_ids: bool = False) -> dict[str, Any]:
        query_terms = list(dict.fromkeys(tokens(query)))
        if not query_terms:
            raise ValueError("查询词不能为空")
        if scope not in {"all", "project"}:
            raise ValueError("范围必须是 all 或 project")
        if not 1 <= limit <= 50:
            raise ValueError("limit 必须在 1 到 50 之间")
        if preview_chars != 0 and not 100 <= preview_chars <= 2000:
            raise ValueError("preview_chars 必须为 0 或 100 到 2000")
        project_ids = None
        if scope == "project":
            if project_id is None:
                raise ValueError("项目范围必须指定 project_id")
            project_ids = self.effective_projects(project_id)
        match = " OR ".join('"'+term.replace('"','')+'"' for term in query_terms)
        sql = "SELECT c.id,c.source,c.source_session_id,c.title,c.started_at,c.updated_at,c.project_id,p.name AS project_name,bm25(conversation_fts) AS rank_score FROM conversation_fts JOIN conversations c ON c.id=conversation_fts.rowid LEFT JOIN projects p ON p.id=c.project_id WHERE conversation_fts MATCH ?"
        args: list[Any] = [match]
        if project_ids is not None:
            sql += " AND c.project_id IN (" + ",".join("?" for _ in project_ids) + ")"
            args.extend(project_ids)
        if current_session_id and not include_current:
            if current_source:
                sql += " AND NOT (c.source=? AND c.source_session_id=?)"
                args.extend((current_source, current_session_id))
            else:
                sql += " AND c.source_session_id<>?"
                args.append(current_session_id)
        sql += " ORDER BY rank_score ASC,c.updated_at DESC,c.id ASC LIMIT ?"
        args.append(limit)
        with self.connect() as con:
            rows = con.execute(sql, args).fetchall()
            results = []
            for index,row in enumerate(rows, 1):
                fields = "id AS _message_id,position,role,text" if include_message_ids else "position,role,text"
                messages = con.execute(f"SELECT {fields} FROM messages WHERE conversation_id=? ORDER BY position,id", (row["id"],)).fetchall()
                item = dict(row)
                item["rank"] = index
                item["bm25_score"] = -item.pop("rank_score")
                matched = select_matched_messages(messages, query_terms)
                item["matched_messages"] = [compact_message(m, query_terms, preview_chars) for m in matched] if preview_chars else matched
                results.append(item)
            effective = [] if project_ids is None else [dict(r) for r in con.execute("SELECT id,name FROM projects WHERE id IN ("+",".join("?" for _ in project_ids)+") ORDER BY id", project_ids)]
        return {"query": query, "scope": scope, "effective_projects": effective if scope == "project" else "all", "excluded_current_session_id": current_session_id if current_session_id and not include_current else None, "results": results}

    def read(self, conversation_id: int, *, start: int | None = None, end: int | None = None,
             include_message_ids: bool = False, message_id: int | None = None) -> dict[str, Any]:
        with self.connect() as con:
            row = con.execute("SELECT c.id,c.source,c.source_session_id,c.source_path,c.cwd,c.started_at,c.updated_at,c.title,c.project_id,p.name AS project_name FROM conversations c LEFT JOIN projects p ON p.id=c.project_id WHERE c.id=?", (conversation_id,)).fetchone()
            if row is None:
                raise ValueError("对话不存在")
            fields = "id AS _message_id,position,role,text,timestamp" if include_message_ids else "position,role,text,timestamp"
            sql = f"SELECT {fields} FROM messages WHERE conversation_id=?"
            args: list[Any] = [conversation_id]
            if message_id is not None:
                sql += " AND id=?"
                args.append(message_id)
            if start is not None:
                sql += " AND position>=?"
                args.append(start)
            if end is not None:
                sql += " AND position<=?"
                args.append(end)
            sql += " ORDER BY position,id"
            messages = [dict(m) for m in con.execute(sql,args)]
        return {**dict(row), "messages": messages}

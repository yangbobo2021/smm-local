# SPDX-License-Identifier: Apache-2.0
"""Project identity and membership in the aggregation archive."""

from __future__ import annotations

from collections import defaultdict

from ._archive import Archive, tokens


class HubProjects:
    def __init__(self, db: Archive):
        self.db = db
        with db.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS hub_devices (id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS hub_origins (
                    message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                    device_id TEXT NOT NULL REFERENCES hub_devices(id),
                    source_position INTEGER NOT NULL,
                    source_order INTEGER NOT NULL,
                    PRIMARY KEY (message_id,device_id,source_position)
                );
                CREATE TABLE IF NOT EXISTS hub_projects (
                    id INTEGER PRIMARY KEY REFERENCES projects(id),
                    kind TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    source_key TEXT NOT NULL,
                    UNIQUE(kind,owner,source_key)
                );
                CREATE TABLE IF NOT EXISTS hub_project_memberships (
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
                    PRIMARY KEY(conversation_id,kind,owner,project_id)
                );
                CREATE INDEX IF NOT EXISTS hub_membership_by_project
                  ON hub_project_memberships(project_id,conversation_id);
                CREATE TABLE IF NOT EXISTS hub_vibeinsight_messages (
                    id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
                    event_id TEXT NOT NULL, trace_key TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hub_project_documents (
                    id INTEGER PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    project_id INTEGER NOT NULL REFERENCES hub_projects(id),
                    UNIQUE(conversation_id,project_id)
                );
                CREATE INDEX IF NOT EXISTS hub_documents_by_project ON hub_project_documents(project_id,id);
                CREATE VIRTUAL TABLE IF NOT EXISTS hub_project_fts USING fts5(terms, tokenize='unicode61');
                CREATE VIEW IF NOT EXISTS hub_project_messages AS
                    SELECT DISTINCT m.id AS message_id, m.conversation_id, pm.project_id
                    FROM hub_project_memberships pm JOIN messages m ON m.conversation_id=pm.conversation_id
                    JOIN hub_origins o ON o.message_id=m.id AND o.device_id=pm.owner
                    WHERE pm.kind='device'
                    UNION ALL
                    SELECT m.id,m.conversation_id,v.project_id FROM hub_vibeinsight_messages v
                    JOIN messages m ON m.id=v.id;
            """)

    @staticmethod
    def upsert(con, kind: str, owner: str, key: str, name: str) -> int:
        row = con.execute(
            "SELECT id FROM hub_projects WHERE kind=? AND owner=? AND source_key=?",
            (kind, owner, key),
        ).fetchone()
        if row is not None:
            con.execute("UPDATE projects SET name=? WHERE id=? AND name<>?", (name, row[0], name))
            return row[0]
        project = con.execute("INSERT INTO projects(name) VALUES(?) RETURNING id", (name,)).fetchone()[0]
        con.execute("INSERT INTO hub_projects(id,kind,owner,source_key) VALUES(?,?,?,?)",
                    (project, kind, owner, key))
        return project

    @staticmethod
    def assign(con, conversation: int, kind: str, owner: str, project: int | None) -> None:
        if kind == "device":
            con.execute("""
                DELETE FROM hub_project_memberships WHERE conversation_id=? AND kind=? AND owner=?
                  AND project_id IS NOT ?
            """, (conversation, kind, owner, project))
        if project is not None:
            con.execute("""
                INSERT OR IGNORE INTO hub_project_memberships(conversation_id,kind,owner,project_id)
                VALUES(?,?,?,?)
            """, (conversation, kind, owner, project))

    @staticmethod
    def reindex(con, conversation: int) -> None:
        con.execute("""
            DELETE FROM hub_project_fts WHERE rowid IN (
              SELECT id FROM hub_project_documents WHERE conversation_id=?
            )
        """, (conversation,))
        con.execute("DELETE FROM hub_project_documents WHERE conversation_id=?", (conversation,))
        by_project = defaultdict(list)
        for project, body in con.execute("""
            SELECT pm.project_id,m.text FROM hub_project_messages pm JOIN messages m ON m.id=pm.message_id
            WHERE pm.conversation_id=? ORDER BY m.position,m.id
        """, (conversation,)):
            by_project[project].append(body)
        for project, bodies in by_project.items():
            document = con.execute("""
                INSERT INTO hub_project_documents(conversation_id,project_id) VALUES(?,?) RETURNING id
            """, (conversation, project)).fetchone()[0]
            terms = " ".join(tokens("\n".join(bodies)))
            con.execute("INSERT INTO hub_project_fts(rowid,terms) VALUES(?,?)", (document, terms))

    def list(self) -> list[dict]:
        with self.db.connect() as con:
            return self._list(con)

    @staticmethod
    def _list(con, ids: tuple[int, ...] | None = None) -> list[dict]:
        query = """
            SELECT p.id,p.name,h.kind AS source,h.owner,h.source_key,d.name AS device_name
            FROM hub_projects h JOIN projects p ON p.id=h.id
            LEFT JOIN hub_devices d ON h.kind='device' AND h.owner=d.id
        """
        if ids is not None:
            query += " WHERE h.id IN (" + ",".join("?" for _ in ids) + ")"
        return [dict(row) for row in con.execute(query + " ORDER BY p.id", ids or ())]

    def memberships(self, conversation: int, within: tuple[int, ...] | None = None,
                    messages: tuple[int, ...] | None = None) -> list[dict]:
        with self.db.connect() as con:
            if messages:
                placeholders = ",".join("?" for _ in messages)
                query = (f"SELECT DISTINCT project_id FROM hub_project_messages "
                         f"WHERE conversation_id=? AND message_id IN ({placeholders})")
                args = (conversation, *messages)
            else:
                query = "SELECT DISTINCT project_id FROM hub_project_memberships WHERE conversation_id=?"
                args = (conversation,)
            ids = tuple(row[0] for row in con.execute(query, args) if within is None or row[0] in within)
            return self._list(con, ids) if ids else []

    def effective(self, device: str, key: str) -> list[dict]:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT id FROM hub_projects WHERE kind='device' AND owner=? AND source_key=?",
                (device, key),
            ).fetchone()
        if row is None:
            return []
        ids = tuple(self.db.effective_projects(row[0]))
        with self.db.connect() as con:
            return self._list(con, ids)

    def links(self) -> list[dict]:
        with self.db.connect() as con:
            return [dict(row) for row in con.execute("SELECT a,b FROM project_links ORDER BY a,b")]

    def link(self, one: int, other: int, *, linked: bool = True) -> None:
        with self.db.connect() as con:
            kinds = [row[0] for row in con.execute(
                "SELECT kind FROM hub_projects WHERE id IN (?,?)", (one, other)
            )]
        if len(kinds) != 2:
            raise ValueError("请选择两个不同的汇总项目")
        if "device" not in kinds:
            raise ValueError("关联至少需要一个设备项目")
        self.db.link_projects(one, other, linked)

# SPDX-License-Identifier: Apache-2.0
"""Project identity and membership in the aggregation archive."""

from ._archive import Archive


class HubProjects:
    def __init__(self, db: Archive):
        self.db = db
        with db.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS hub_devices (id TEXT PRIMARY KEY, name TEXT NOT NULL);
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
                    PRIMARY KEY(conversation_id,kind,owner)
                );
                CREATE INDEX IF NOT EXISTS hub_membership_by_project
                  ON hub_project_memberships(project_id,conversation_id);
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
        if project is None:
            con.execute("DELETE FROM hub_project_memberships WHERE conversation_id=? AND kind=? AND owner=?",
                        (conversation, kind, owner))
        else:
            con.execute("""
                INSERT INTO hub_project_memberships(conversation_id,kind,owner,project_id)
                VALUES(?,?,?,?) ON CONFLICT(conversation_id,kind,owner)
                DO UPDATE SET project_id=excluded.project_id
            """, (conversation, kind, owner, project))

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

    def memberships(self, conversation: int, within: tuple[int, ...] | None = None) -> list[dict]:
        with self.db.connect() as con:
            ids = tuple(row[0] for row in con.execute(
                "SELECT project_id FROM hub_project_memberships WHERE conversation_id=?", (conversation,)
            ) if within is None or row[0] in within)
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

# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 SubLang International <https://sublang.ai>
"""Generate portable, synthetic ZCode SQLite snapshots for adapter admission."""

import json
import shutil
import sqlite3
from contextlib import closing

SCOPE = {"kind": "zcode", "session_ids": ["smm-fixed-seed"], "first_user_prefix": "SMM-FIXED-AUTH "}
SCHEMA = """
CREATE TABLE session (id TEXT PRIMARY KEY, data TEXT);
CREATE TABLE message (
    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, time_created INTEGER,
    time_updated INTEGER, data TEXT NOT NULL, sequence INTEGER NOT NULL
);
CREATE INDEX message_session ON message(session_id);
CREATE TABLE part (
    id TEXT PRIMARY KEY, message_id TEXT NOT NULL, session_id TEXT NOT NULL,
    time_created INTEGER, time_updated INTEGER, data TEXT NOT NULL, sequence INTEGER NOT NULL
);
CREATE INDEX part_message ON part(message_id);
"""


def _add(db, sid, mid, sequence, role, text=None, **attributes):
    when = 1763200000000 + sequence * 1000
    meta = {"id": mid, "sessionID": sid, "role": role, "time": {"created": when}, **attributes}
    db.execute("INSERT OR IGNORE INTO session VALUES(?,?)", (sid, "{}"))
    db.execute("INSERT INTO message VALUES(?,?,?,?,?,?)",
               (mid, sid, when, when, json.dumps(meta), sequence))
    if text is not None:
        _part(db, sid, mid, when, text)


def _part(db, sid, mid, when, text):
    db.execute("INSERT INTO part VALUES(?,?,?,?,?,?,?)",
               (mid + "-p", mid, sid, when, when, json.dumps({"type": "text", "text": text}), 0))


def create(directory):
    paths = {}
    for stage in ("before", "pending", "after"):
        path = directory / stage / "db.sqlite"
        path.parent.mkdir(parents=True)
        paths[stage] = path
    seed, other, live = "smm-fixed-seed", "smm-fixed-denied", "smm-fixed-stream"
    done = {"finish": "stop", "time": {"created": 1763200001000, "completed": 1763200002500}}
    with closing(sqlite3.connect(paths["before"])) as db, db:
        db.executescript(SCHEMA)
        _add(db, other, "denied-hidden", 0, "user", "SMM-FIXED-AUTH hidden", hidden=True)
        _add(db, other, "denied-hidden-part", 0, "user", "SMM-FIXED-AUTH hidden part")
        db.execute("""
            UPDATE part SET data=json_set(data,'$.metadata.visibility','model-only')
            WHERE message_id='denied-hidden-part'
        """)
        _add(db, other, "denied-user", 1, "user", "Out of scope")
        _add(db, other, "denied-later", 2, "user", "SMM-FIXED-AUTH later prompt")
        _add(db, seed, "seed-user", 0, "user", "Repeated visible text")
        _add(db, seed, "seed-assistant", 7, "assistant", "Repeated visible text", **done)
    shutil.copyfile(paths["before"], paths["pending"])
    with closing(sqlite3.connect(paths["pending"])) as db, db:
        _add(db, live, "stream-timeline", 0, "assistant",
             semantics={"origin": "system", "kind": "timeline_event"}, **done)
        _add(db, live, "stream-internal-text", 1, "assistant", "Internal event",
             semantics={"origin": "system", "kind": "timeline_event"}, **done)
        _add(db, live, "stream-hidden", 2, "assistant", "Model-only text", visibility="model-only")
        _add(db, live, "stream-user", 3, "user", "SMM-FIXED-AUTH New prompt",
             semantics={"kind": "user_prompt"})
        _add(db, live, "stream-assistant", 7, "assistant", semantics={"kind": "assistant_response"})
    shutil.copyfile(paths["pending"], paths["after"])
    with closing(sqlite3.connect(paths["after"])) as db, db:
        db.execute("""
            UPDATE message SET data=json_set(data,'$.finish','stop','$.time.completed',?),time_updated=?
            WHERE id='stream-assistant'
        """, (1763200009000, 1763200009000))
        _part(db, live, "stream-assistant", 1763200009000, "Completed on the same row")

    def expected(sid, mid, position, role, text):
        return dict(session_id=sid, message_id=mid, position=position, role=role,
                    text=text, origin="db.sqlite")

    return paths, {
        "before": [
            expected(seed, "seed-user", 0, "user", "Repeated visible text"),
            expected(seed, "seed-assistant", 7, "assistant", "Repeated visible text"),
        ],
        "pending": [expected(live, "stream-user", 3, "user", "SMM-FIXED-AUTH New prompt")],
        "after": [expected(live, "stream-assistant", 7, "assistant", "Completed on the same row")],
    }

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Sequence


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    source TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    summary TEXT,
    mood TEXT,
    word_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (entry_id, tag_id),
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL UNIQUE,
    raw_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        init_db(connection)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def word_count(text: str) -> int:
    return len(text.split())


def list_tags(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT name FROM tags ORDER BY name").fetchall()
    return [row[0] for row in rows]


def _entry_tags_clause() -> str:
    return """
        SELECT t.name
        FROM tags t
        JOIN entry_tags et ON et.tag_id = t.id
        WHERE et.entry_id = e.id
        ORDER BY t.name
    """


def list_entries(
    connection: sqlite3.Connection,
    *,
    tag: str | None = None,
    mood: str | None = None,
    last_days: int | None = None,
    source: str | None = None,
) -> list[sqlite3.Row]:
    conditions: list[str] = []
    params: list[object] = []

    if tag:
        conditions.append(
            "EXISTS (SELECT 1 FROM entry_tags et JOIN tags t ON t.id = et.tag_id WHERE et.entry_id = e.id AND t.name = ?)"
        )
        params.append(_normalize_tag(tag))
    if mood:
        conditions.append("e.mood = ?")
        params.append(mood)
    if source:
        conditions.append("e.source = ?")
        params.append(source)
    if last_days is not None:
        threshold = datetime.now(timezone.utc) - timedelta(days=int(last_days))
        conditions.append("e.created_at >= ?")
        params.append(threshold.replace(microsecond=0).isoformat())

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT
            e.id,
            e.created_at,
            e.updated_at,
            e.source,
            e.raw_text,
            e.summary,
            e.mood,
            e.word_count,
            COALESCE((
                SELECT group_concat(name, ', ')
                FROM (
                    SELECT t.name AS name
                    FROM tags t
                    JOIN entry_tags et ON et.tag_id = t.id
                    WHERE et.entry_id = e.id
                    ORDER BY t.name
                )
            ), '') AS tags
        FROM entries e
        {where_clause}
        ORDER BY e.created_at DESC, e.id DESC
    """
    return connection.execute(query, params).fetchall()


def get_entry(connection: sqlite3.Connection, entry_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, created_at, updated_at, source, raw_text, summary, mood, word_count
        FROM entries
        WHERE id = ?
        """,
        (entry_id,),
    ).fetchone()


def get_entry_tags(connection: sqlite3.Connection, entry_id: int) -> list[str]:
    rows = connection.execute(
        """
        SELECT t.name
        FROM tags t
        JOIN entry_tags et ON et.tag_id = t.id
        WHERE et.entry_id = ?
        ORDER BY t.name
        """,
        (entry_id,),
    ).fetchall()
    return [row[0] for row in rows]


def get_transcript(connection: sqlite3.Connection, entry_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, entry_id, raw_json, created_at
        FROM transcripts
        WHERE entry_id = ?
        """,
        (entry_id,),
    ).fetchone()


def get_recent_entries(connection: sqlite3.Connection, limit: int = 3) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, created_at, summary, raw_text
        FROM entries
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _normalize_tag(name: str) -> str:
    return name.strip().lower()


def _get_or_create_tag_id(connection: sqlite3.Connection, name: str) -> int:
    normalized = _normalize_tag(name)
    row = connection.execute("SELECT id FROM tags WHERE name = ?", (normalized,)).fetchone()
    if row is not None:
        return int(row[0])

    cursor = connection.execute("INSERT INTO tags (name) VALUES (?)", (normalized,))
    return int(cursor.lastrowid)


def save_entry(
    connection: sqlite3.Connection,
    *,
    created_at: str | None = None,
    updated_at: str | None = None,
    source: str,
    raw_text: str,
    summary: str | None = None,
    mood: str | None = None,
    tags: Sequence[str] = (),
) -> int:
    normalized_tags: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = _normalize_tag(tag)
        if not normalized or normalized in seen:
            continue
        normalized_tags.append(normalized)
        seen.add(normalized)

    with connection:
        cursor = connection.execute(
            """
            INSERT INTO entries (created_at, updated_at, source, raw_text, summary, mood, word_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at or utc_now_iso(),
                updated_at,
                source,
                raw_text,
                summary,
                mood,
                word_count(raw_text),
            ),
        )
        entry_id = int(cursor.lastrowid)

        for tag in normalized_tags:
            tag_id = _get_or_create_tag_id(connection, tag)
            connection.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_id),
            )

    return entry_id


def update_entry(
    connection: sqlite3.Connection,
    *,
    entry_id: int,
    raw_text: str,
    summary: str | None,
    mood: str | None,
    tags: Sequence[str],
    updated_at: str | None = None,
) -> None:
    normalized_tags: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = _normalize_tag(tag)
        if not normalized or normalized in seen:
            continue
        normalized_tags.append(normalized)
        seen.add(normalized)

    with connection:
        connection.execute(
            """
            UPDATE entries
            SET raw_text = ?, summary = ?, mood = ?, updated_at = ?, word_count = ?
            WHERE id = ?
            """,
            (
                raw_text,
                summary,
                mood,
                updated_at or utc_now_iso(),
                word_count(raw_text),
                entry_id,
            ),
        )
        connection.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
        for tag in normalized_tags:
            tag_id = _get_or_create_tag_id(connection, tag)
            connection.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_id),
            )


def save_transcript(
    connection: sqlite3.Connection,
    *,
    entry_id: int,
    raw_json: str,
    created_at: str | None = None,
) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO transcripts (entry_id, raw_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(entry_id) DO UPDATE SET
                raw_json = excluded.raw_json,
                created_at = excluded.created_at
            """,
            (entry_id, raw_json, created_at or utc_now_iso()),
        )


def delete_entry(connection: sqlite3.Connection, entry_id: int) -> bool:
    with connection:
        cursor = connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    return cursor.rowcount > 0

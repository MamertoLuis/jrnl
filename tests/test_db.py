from __future__ import annotations

import sqlite3

from jrnl.db import init_db, word_count


def test_init_db_creates_tables(tmp_path) -> None:
    db_path = tmp_path / "journal.db"
    connection = sqlite3.connect(db_path)

    try:
        init_db(connection)
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()

    assert {"entries", "tags", "entry_tags", "transcripts"}.issubset(tables)


def test_word_count_counts_words() -> None:
    assert word_count("one two three") == 3

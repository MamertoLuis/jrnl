from __future__ import annotations

from importlib import import_module
from pathlib import Path

from click.testing import CliRunner

from jrnl.cli import cli
from jrnl.config import Config, EditorConfig, OllamaConfig, StorageConfig
from jrnl.db import connect, initialize_database, save_entry
from jrnl.enrichment import EnrichmentResult


edit_command = import_module("jrnl.commands.edit")
reprocess_command = import_module("jrnl.commands.reprocess")


def _config_for(db_path: Path) -> Config:
    return Config(
        ollama=OllamaConfig(model="test-model", host="http://localhost:11434", timeout_seconds=1),
        editor=EditorConfig(command="notepad"),
        storage=StorageConfig(db_path=db_path),
    )


def test_edit_command_updates_entry_when_text_changes(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        entry_id = save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="write",
            raw_text="Old text.",
            summary="Old summary",
            mood="neutral",
            tags=["old"],
        )

    monkeypatch.setattr(edit_command, "ensure_config", lambda: _config_for(db_path))
    monkeypatch.setattr(edit_command, "edit_text", lambda initial_text, configured_command="", env=None: "New text with more detail.")
    monkeypatch.setattr(
        edit_command,
        "enrich_entry",
        lambda client, *, model, entry_text, existing_tags: EnrichmentResult(
            summary="New text with more detail",
            mood="calm",
            tags=["new", "detail"],
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["edit", str(entry_id)])

    assert result.exit_code == 0
    assert f"Updated entry #{entry_id}." in result.output

    with connect(db_path) as connection:
        entry = connection.execute(
            "SELECT raw_text, summary, mood, word_count, updated_at FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        tags = connection.execute(
            """
            SELECT t.name
            FROM tags t
            JOIN entry_tags et ON et.tag_id = t.id
            WHERE et.entry_id = ?
            ORDER BY t.name
            """,
            (entry_id,),
        ).fetchall()

    assert entry["raw_text"] == "New text with more detail."
    assert entry["summary"] == "New text with more detail"
    assert entry["mood"] == "calm"
    assert entry["word_count"] == 5
    assert entry["updated_at"] is not None
    assert [row[0] for row in tags] == ["detail", "new"]


def test_reprocess_command_rewrites_enrichment(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        entry_id = save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="write",
            raw_text="Something happened.",
            summary=None,
            mood=None,
            tags=[],
        )

    monkeypatch.setattr(reprocess_command, "ensure_config", lambda: _config_for(db_path))
    monkeypatch.setattr(
        reprocess_command,
        "enrich_entry",
        lambda client, *, model, entry_text, existing_tags: EnrichmentResult(
            summary="Something happened",
            mood="mixed",
            tags=["life"],
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["reprocess", str(entry_id)])

    assert result.exit_code == 0
    assert f"Reprocessed entry #{entry_id}." in result.output

    with connect(db_path) as connection:
        entry = connection.execute(
            "SELECT summary, mood FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
        tags = connection.execute(
            "SELECT name FROM tags ORDER BY name",
        ).fetchall()

    assert entry["summary"] == "Something happened"
    assert entry["mood"] == "mixed"
    assert [row[0] for row in tags] == ["life"]

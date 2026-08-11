from __future__ import annotations

import sqlite3
from importlib import import_module
from pathlib import Path

from click.testing import CliRunner

from jrnl.cli import cli
from jrnl.config import Config, EditorConfig, OllamaConfig, StorageConfig
from jrnl.enrichment import EnrichmentResult


new_command = import_module("jrnl.commands.new")


def test_new_command_saves_entry(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    config = Config(
        ollama=OllamaConfig(model="test-model", host="http://localhost:11434", timeout_seconds=1),
        editor=EditorConfig(command="notepad"),
        storage=StorageConfig(db_path=db_path),
    )

    monkeypatch.setattr(new_command, "ensure_config", lambda: config)
    monkeypatch.setattr(new_command, "edit_text", lambda initial_text, configured_command="", env=None: "A calm day with coffee and a walk.")
    monkeypatch.setattr(
        new_command,
        "enrich_entry",
        lambda client, *, model, entry_text, existing_tags: EnrichmentResult(
            summary="A calm day with coffee",
            mood="calm",
            tags=["life", "coffee"],
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["new"])

    assert result.exit_code == 0
    assert "Saved entry #" in result.output

    with sqlite3.connect(db_path) as connection:
        entry = connection.execute("SELECT raw_text, summary, mood, word_count FROM entries").fetchone()
        tags = connection.execute("SELECT name FROM tags ORDER BY name").fetchall()

    assert entry == ("A calm day with coffee and a walk.", "A calm day with coffee", "calm", 8)
    assert [row[0] for row in tags] == ["coffee", "life"]

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from click.testing import CliRunner

from jrnl.cli import cli
from jrnl.config import Config, EditorConfig, OllamaConfig, StorageConfig
from jrnl.db import connect, initialize_database, save_entry, save_transcript


delete_command = import_module("jrnl.commands.delete")


def _config_for(db_path: Path) -> Config:
    return Config(
        ollama=OllamaConfig(),
        editor=EditorConfig(command="notepad"),
        storage=StorageConfig(db_path=db_path),
    )


def test_delete_command_removes_entry_and_related_rows(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        entry_id = save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="talk",
            raw_text="Delete me.",
            summary="Delete me",
            mood="neutral",
            tags=["temp"],
        )
        save_transcript(
            connection,
            entry_id=entry_id,
            raw_json='[{"role": "user", "text": "Delete me."}]',
            created_at="2026-08-10T10:05:00+00:00",
        )

    monkeypatch.setattr(delete_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["delete", str(entry_id)], input="y\n")

    assert result.exit_code == 0
    assert f"Deleted entry #{entry_id}." in result.output

    with connect(db_path) as connection:
        entry_count = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        transcript_count = connection.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        join_count = connection.execute("SELECT COUNT(*) FROM entry_tags").fetchone()[0]

    assert entry_count == 0
    assert transcript_count == 0
    assert join_count == 0

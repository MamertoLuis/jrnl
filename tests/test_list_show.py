from __future__ import annotations

from importlib import import_module
from datetime import datetime, timedelta, timezone
from pathlib import Path

from click.testing import CliRunner

from jrnl.cli import cli
from jrnl.config import Config, EditorConfig, OllamaConfig, StorageConfig
from jrnl.db import connect, initialize_database, save_entry, save_transcript


list_command = import_module("jrnl.commands.list")
show_command = import_module("jrnl.commands.show")


def _config_for(db_path: Path) -> Config:
    return Config(
        ollama=OllamaConfig(),
        editor=EditorConfig(command="notepad"),
        storage=StorageConfig(db_path=db_path),
    )


def test_list_command_filters_by_tag_and_mood(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="write",
            raw_text="A calm morning walk.",
            summary="Calm morning walk",
            mood="calm",
            tags=["walk", "health"],
        )
        save_entry(
            connection,
            created_at="2026-08-09T10:00:00+00:00",
            source="talk",
            raw_text="A stressful meeting.",
            summary="Stressful meeting",
            mood="anxious",
            tags=["work"],
        )

    monkeypatch.setattr(list_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--tag", "walk", "--mood", "calm"])

    assert result.exit_code == 0
    assert "Calm morning walk" in result.output
    assert "Stressful meeting" not in result.output


def test_list_command_filters_by_last_days(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with connect(db_path) as connection:
        save_entry(
            connection,
            created_at=now.isoformat(),
            source="write",
            raw_text="Recent entry.",
            summary="Recent entry",
            mood="calm",
            tags=[],
        )
        save_entry(
            connection,
            created_at=(now - timedelta(days=3)).isoformat(),
            source="write",
            raw_text="Old entry.",
            summary="Old entry",
            mood="sad",
            tags=[],
        )

    monkeypatch.setattr(list_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--last", "1"])

    assert result.exit_code == 0
    assert "Recent entry" in result.output
    assert "Old entry" not in result.output


def test_show_command_displays_entry_and_transcript(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        entry_id = save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="talk",
            raw_text="I had coffee and read a book.",
            summary="Coffee and reading",
            mood="calm",
            tags=["coffee", "reading"],
        )
        save_transcript(
            connection,
            entry_id=entry_id,
            raw_json='[{"role": "user", "text": "I had coffee."}]',
            created_at="2026-08-10T10:05:00+00:00",
        )

    monkeypatch.setattr(show_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["show", str(entry_id), "--transcript"])

    assert result.exit_code == 0
    assert "Coffee and reading" in result.output
    assert "Transcript" in result.output
    assert "I had coffee." in result.output

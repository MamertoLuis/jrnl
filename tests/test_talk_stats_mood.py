from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from click.testing import CliRunner

from jrnl.cli import cli
from jrnl.config import Config, EditorConfig, OllamaConfig, StorageConfig
from jrnl.db import connect, initialize_database, save_entry


talk_command = import_module("jrnl.commands.talk")
stats_command = import_module("jrnl.commands.stats")
mood_command = import_module("jrnl.commands.mood")


def _config_for(db_path: Path) -> Config:
    return Config(
        ollama=OllamaConfig(model="test-model", host="http://localhost:11434", timeout_seconds=1),
        editor=EditorConfig(command="notepad"),
        storage=StorageConfig(db_path=db_path),
    )


@dataclass
class DummyClient:
    host: str
    timeout_seconds: int = 1

    def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        return "What else stood out?"

    def generate(self, model: str, prompt: str, format: str | None = None) -> str:
        if "Conversation:" in prompt:
            return "I drank coffee and felt calm."
        return json.dumps({"summary": "I drank coffee and felt calm", "mood": "calm", "tags": ["coffee"]})


def test_talk_command_saves_transcript_and_compiled_entry(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    config = _config_for(db_path)

    monkeypatch.setattr(talk_command, "ensure_config", lambda: config)
    monkeypatch.setattr(talk_command.random, "choice", lambda items: items[0])
    monkeypatch.setattr(talk_command, "OllamaClient", DummyClient)
    monkeypatch.setattr(talk_command.click, "prompt", lambda *args, **kwargs: next(responses))

    responses = iter(["I drank coffee.", "/done"])

    runner = CliRunner()
    result = runner.invoke(cli, ["talk"])

    assert result.exit_code == 0
    assert "Saved entry #" in result.output

    with connect(db_path) as connection:
        entry = connection.execute(
            "SELECT source, raw_text, summary, mood FROM entries",
        ).fetchone()
        transcript = connection.execute(
            "SELECT raw_json FROM transcripts",
        ).fetchone()

    assert entry["source"] == "talk"
    assert entry["raw_text"] == "I drank coffee and felt calm."
    assert entry["summary"] == "I drank coffee and felt calm"
    assert entry["mood"] == "calm"
    assert transcript is not None
    assert len(json.loads(transcript["raw_json"])) == 3


def test_stats_command_reports_counts(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        save_entry(
            connection,
            created_at="2026-08-08T10:00:00+00:00",
            source="write",
            raw_text="First entry.",
            summary="First entry",
            mood="calm",
            tags=["coffee"],
        )
        save_entry(
            connection,
            created_at="2026-08-09T10:00:00+00:00",
            source="talk",
            raw_text="Second entry.",
            summary="Second entry",
            mood="happy",
            tags=["coffee", "walk"],
        )
        save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="write",
            raw_text="Third entry.",
            summary="Third entry",
            mood="calm",
            tags=["walk"],
        )

    monkeypatch.setattr(stats_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["stats"])

    assert result.exit_code == 0
    assert "Entries: 3" in result.output
    assert "Current streak: 3" in result.output
    assert "Longest streak: 3" in result.output
    assert "coffee" in result.output
    assert "calm" in result.output


def test_mood_command_reports_distribution(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "journal.db"
    initialize_database(db_path)
    with connect(db_path) as connection:
        save_entry(
            connection,
            created_at="2026-08-10T10:00:00+00:00",
            source="write",
            raw_text="One.",
            summary="One",
            mood="calm",
            tags=[],
        )
        save_entry(
            connection,
            created_at="2026-08-10T11:00:00+00:00",
            source="write",
            raw_text="Two.",
            summary="Two",
            mood="calm",
            tags=[],
        )
        save_entry(
            connection,
            created_at="2026-08-10T12:00:00+00:00",
            source="talk",
            raw_text="Three.",
            summary="Three",
            mood="anxious",
            tags=[],
        )

    monkeypatch.setattr(mood_command, "ensure_config", lambda: _config_for(db_path))

    runner = CliRunner()
    result = runner.invoke(cli, ["mood"])

    assert result.exit_code == 0
    assert "Mood Trend" in result.output
    assert "calm" in result.output
    assert "anxious" in result.output

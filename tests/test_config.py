from __future__ import annotations

from pathlib import Path

from jrnl.config import default_config, ensure_config, save_config


def test_default_config_has_expected_paths() -> None:
    config = default_config()

    assert config.ollama.model == "llama3.2:3b"
    assert config.storage.db_path == Path.home() / ".jrnl" / "journal.db"


def test_save_and_load_config_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    config = default_config()

    save_config(config, path)

    loaded = ensure_config(path)
    assert loaded.ollama.host == config.ollama.host

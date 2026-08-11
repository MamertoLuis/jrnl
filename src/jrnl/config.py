from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


@dataclass(slots=True)
class OllamaConfig:
    model: str = "llama3.2:3b"
    host: str = "http://localhost:11434"
    timeout_seconds: int = 30


@dataclass(slots=True)
class EditorConfig:
    command: str = ""


@dataclass(slots=True)
class StorageConfig:
    db_path: Path = Path.home() / ".jrnl" / "journal.db"


@dataclass(slots=True)
class Config:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    editor: EditorConfig = field(default_factory=EditorConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


def config_dir() -> Path:
    return Path.home() / ".jrnl"


def config_path() -> Path:
    return config_dir() / "config.toml"


def default_config() -> Config:
    return Config()


def load_config(path: Path | None = None) -> Config:
    target = path or config_path()
    if not target.exists():
        return default_config()

    data = tomllib.loads(target.read_text(encoding="utf-8"))
    ollama = data.get("ollama", {})
    editor = data.get("editor", {})
    storage = data.get("storage", {})
    return Config(
        ollama=OllamaConfig(
            model=ollama.get("model", "llama3.2:3b"),
            host=ollama.get("host", "http://localhost:11434"),
            timeout_seconds=int(ollama.get("timeout_seconds", 30)),
        ),
        editor=EditorConfig(command=editor.get("command", "")),
        storage=StorageConfig(db_path=Path(storage.get("db_path", Path.home() / ".jrnl" / "journal.db"))),
    )


def save_config(config: Config, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(
            [
                "[ollama]",
                f'model = "{config.ollama.model}"',
                f'host = "{config.ollama.host}"',
                f"timeout_seconds = {config.ollama.timeout_seconds}",
                "",
                "[editor]",
                f'command = "{config.editor.command}"',
                "",
                "[storage]",
                f'db_path = "{config.storage.db_path.as_posix()}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return target


def ensure_config(path: Path | None = None) -> Config:
    target = path or config_path()
    if target.exists():
        return load_config(target)

    config = default_config()
    save_config(config, target)
    return config

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path


def _split_command(command: str, *, windows: bool) -> list[str]:
    return shlex.split(command, posix=not windows)


def resolve_editor_command(
    configured_command: str = "",
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
) -> list[str]:
    values = env or os.environ
    windows = (platform or os.name) == "nt"
    candidates = [configured_command, values.get("EDITOR", ""), "vim", "notepad" if windows else "nano"]
    for candidate in candidates:
        if not candidate.strip():
            continue
        parts = _split_command(candidate, windows=windows)
        if not parts:
            continue
        if parts[0].lower() == "notepad" or shutil.which(parts[0]) is not None:
            return parts
    return ["notepad"] if windows else ["nano"]


def edit_text(
    initial_text: str,
    *,
    configured_command: str = "",
    env: Mapping[str, str] | None = None,
) -> str:
    editor_command = resolve_editor_command(configured_command, env)
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            delete=False,
            suffix=".txt",
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(initial_text)

        subprocess.run([*editor_command, str(temp_path)], check=True)
        return temp_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

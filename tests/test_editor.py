from __future__ import annotations

from jrnl.editor import resolve_editor_command


def test_resolve_editor_command_prefers_editor_env() -> None:
    from jrnl import editor as editor_module

    original_which = editor_module.shutil.which
    editor_module.shutil.which = lambda name: "/usr/bin/vim" if name == "vim" else None
    try:
        result = resolve_editor_command(env={"EDITOR": "vim -u NONE"}, platform="posix")

        assert result == ["vim", "-u", "NONE"]
    finally:
        editor_module.shutil.which = original_which


def test_resolve_editor_command_uses_nano_on_linux_when_vim_missing(monkeypatch) -> None:
    monkeypatch.setattr("jrnl.editor.shutil.which", lambda name: None)

    result = resolve_editor_command(platform="posix")

    assert result == ["nano"]


def test_resolve_editor_command_uses_notepad_on_windows_when_vim_missing(monkeypatch) -> None:
    def fake_which(name: str) -> str | None:
        return None if name == "vim" else None

    monkeypatch.setattr("jrnl.editor.shutil.which", fake_which)

    result = resolve_editor_command(platform="nt")

    assert result == ["notepad"]

# AGENTS.md

This file gives AI coding agents (Claude Code, etc.) the context needed to work on this project correctly. Read this before making changes.

---

## Project Summary

**jrnl** is a local-first, terminal-based journaling CLI written in Python. It uses a locally-run LLM via **Ollama** to auto-tag, summarize, and mood-classify journal entries on save, and supports a conversational entry mode (`jrnl talk`) for low-effort days. Full product spec: see `jrnl-spec.md` in this repo — treat it as the source of truth for behavior, schema, and prompt design. If code and spec disagree, flag it rather than silently picking one.

**Platform target: Windows 11.** This is the only platform in scope right now — see Platform Notes below before touching anything involving editors, paths, or subprocesses.

---

## Environment & Tooling

This project uses **uv** for dependency management, virtual environments, and running the project. Do not use `pip install` directly, `poetry`, `pipenv`, or manually manage a `venv/` — everything goes through `uv`.

### Setup commands
```powershell
# Initialize (already done once, but for reference):
uv init

# Install dependencies from pyproject.toml:
uv sync

# Add a new dependency:
uv add <package>

# Add a dev-only dependency:
uv add --dev <package>

# Run the CLI during development:
uv run jrnl <command>

# Run tests:
uv run pytest

# Run any ad-hoc script inside the project's venv:
uv run python <script.py>
```

### Project structure conventions
- `pyproject.toml` is the single source of truth for dependencies and the `jrnl` entry point (`[project.scripts]`)
- `uv.lock` should be committed — do not add it to `.gitignore`
- Do not create a `requirements.txt` — dependencies live only in `pyproject.toml`
- Do not manually create/activate a virtualenv — `uv run` handles this implicitly

### Expected `pyproject.toml` entry point
```toml
[project.scripts]
jrnl = "jrnl.cli:main"
```
This means after `uv sync`, `uv run jrnl new` should work without any extra steps.

---

## Project Structure

```
jrnl/
├── pyproject.toml
├── uv.lock
├── AGENTS.md
├── jrnl-spec.md
├── src/
│   └── jrnl/
│       ├── __init__.py
│       ├── cli.py               # command routing (click)
│       ├── config.py             # load/save config, defaults
│       ├── db.py                 # schema init, queries
│       ├── ollama_client.py     # wraps Ollama API calls
│       ├── prompts.py             # prompt templates
│       └── commands/
│           ├── __init__.py
│           ├── new.py
│           ├── talk.py
│           ├── list.py
│           ├── show.py
│           ├── edit.py
│           ├── delete.py
│           ├── stats.py
│           ├── mood.py
│           └── reprocess.py
└── tests/
    ├── test_config.py
    ├── test_db.py
    └── test_enrichment_validation.py
```

Use the `src/` layout (not a flat top-level package) — this avoids accidental imports of the working directory instead of the installed package, which `uv` handles cleanly.

---

## Platform Notes — Windows 11 First, Linux/macOS Copy-Over Supported

This app is being built on Windows 11 first, but should also run when copied to Linux or macOS. Several defaults that are safe assumptions on Linux/macOS are **not** safe here:

### Editor invocation
- Do **not** default the fallback editor to `nano` on Windows. Fallback chain should be: `$EDITOR` env var → `vim` → `notepad`.
- On Linux/macOS copy-over, fallback should be: `$EDITOR` env var → `vim` → `nano`.
- When shelling out via `subprocess`, pass the command as a list (`[editor, str(temp_path)]`), not a shell string — avoids quoting issues with paths containing spaces.
- Do not set `shell=True` unless there's a specific reason — unnecessary shell invocation is a Windows-specific footgun (cmd.exe quoting rules differ from POSIX shells).

### Paths
- Always build paths with `pathlib.Path`, never manual string concatenation with `/`.
- `Path.home()` resolves correctly on Windows (`C:\Users\<username>`) — safe to use for `~/.jrnl/`.
- Watch for max path length issues in edge cases; not a concern at this project's scale, but avoid deeply nested temp file structures.

### Terminal output
- `rich` handles Windows Terminal / cmd.exe color support automatically — no extra configuration needed, but avoid assuming ANSI escape codes work in *all* Windows terminal contexts (older `cmd.exe` without VT100 support). `rich` degrades gracefully; don't bypass it with raw ANSI codes.

### SQLite file locking
- Windows file locking semantics differ slightly from POSIX (stricter about files being open elsewhere). Ensure DB connections are properly closed after each command invocation rather than held open — avoid "database is locked" errors if a previous process didn't clean up.

### Line endings
- Be mindful of `\r\n` vs `\n` when reading text back from `notepad`-edited temp files. Normalize line endings (`splitlines()` or explicit `.replace('\r\n', '\n')`) before storing entry text, so `word_count` and downstream text processing aren't thrown off by stray `\r` characters.

### Ollama on Windows
- Ollama runs as a native Windows service/app and exposes the same local API (`http://localhost:11434`) — no WSL required, but confirm the user has it running as a standalone Windows install, not inside WSL2 with networking quirks (WSL2's `localhost` forwarding can be inconsistent depending on configuration). If connectivity issues come up, this is the first thing to check.

---

## Coding Conventions

- **Python 3.10+** syntax is fine to use (match statements, etc.) — confirm `requires-python` in `pyproject.toml` reflects this.
- Type hints on all function signatures — this is a small enough codebase that full typing is cheap and pays off.
- Keep `commands/*.py` thin — each command module should parse its args, call into `db.py` / `ollama_client.py`, and format output via `rich`. Business logic (enrichment validation, JSON fallback handling) belongs in shared modules, not duplicated per command.
- All Ollama-facing prompt strings live in `prompts.py` — do not inline prompt text inside command files. Keeps prompt iteration centralized and testable.
- Follow the **hard rule from the spec**: entry text must always persist even if AI enrichment fails. Any code path that saves an entry must not raise/abort *after* the point where `raw_text` is captured, based on an Ollama failure. Enrichment failures degrade gracefully (`mood=NULL`, `summary=NULL`, no tags) — they never block the save.

---

## Testing

- Run `uv run pytest` before considering any change complete.
- Priority test coverage: JSON parsing/validation/fallback logic for AI responses (`prompts.py` consumers) — this is the most likely place for silent breakage since it depends on LLM output that won't always match the schema.
- Ollama calls should be mockable in tests — do not require a running Ollama instance for the test suite to pass. Tests that need real model output should be marked separately (e.g. `@pytest.mark.integration`) and skipped by default.

---

## What Not to Do

- Don't introduce cloud calls, telemetry, or any network dependency other than the local Ollama API — this is a privacy-first local tool by design.
- Don't add a `requirements.txt`, `Pipfile`, or `poetry.lock` — `uv` + `pyproject.toml` + `uv.lock` only.
- Don't default any subprocess or path logic to POSIX assumptions — this project targets Windows 11 first.
- Don't let phase 2 (semantic search / embeddings) scope creep into current work — the schema reserves space for it (see `jrnl-spec.md` §5.5), but `commands/ask.py` and `phase2/` should stay unbuilt until explicitly requested.
- Don't silently change the mood enum, tag behavior, or command names from what's defined in `jrnl-spec.md` — if a change seems warranted, surface it rather than deciding unilaterally.

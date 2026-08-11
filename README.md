# jrnl

Terminal-first AI journaling CLI.

## Packaging

Use PyInstaller to build a standalone bundle on each target OS.

```powershell
uv run pyinstaller --onefile --name jrnl src/jrnl/cli.py
```

Build on Windows for Windows, Linux for Linux, and macOS for macOS.

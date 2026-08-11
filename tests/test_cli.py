from __future__ import annotations

from click.testing import CliRunner

from jrnl.cli import cli


def test_cli_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, [])

    assert result.exit_code == 0
    assert "new" in result.output
    assert "mood" in result.output

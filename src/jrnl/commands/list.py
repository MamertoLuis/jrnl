from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from jrnl.config import ensure_config
from jrnl.db import connect, initialize_database, list_entries as fetch_entries


@click.command(name="list")
@click.option("--tag", type=str, default=None)
@click.option("--mood", type=str, default=None)
@click.option("--last", "last_days", type=int, default=None)
@click.option("--source", type=click.Choice(["write", "talk"], case_sensitive=False), default=None)
def list_entries(tag: str | None, mood: str | None, last_days: int | None, source: str | None) -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    with connect(config.storage.db_path) as connection:
        entries = fetch_entries(
            connection,
            tag=tag,
            mood=mood,
            last_days=last_days,
            source=source.lower() if source else None,
        )

    table = Table(title="Journal Entries")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Date", style="green")
    table.add_column("Summary")
    table.add_column("Mood")
    table.add_column("Tags")

    for entry in entries:
        table.add_row(
            str(entry["id"]),
            str(entry["created_at"]),
            entry["summary"] or "",
            entry["mood"] or "",
            entry["tags"] or "",
        )

    Console().print(table)

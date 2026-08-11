from __future__ import annotations

from collections import Counter

import click
from rich.console import Console
from rich.table import Table

from jrnl.config import ensure_config
from jrnl.db import connect, initialize_database, list_entries


@click.command()
@click.option("--last", "last_days", type=int, default=None)
def mood(last_days: int | None) -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    with connect(config.storage.db_path) as connection:
        entries = list_entries(connection, last_days=last_days)

    console = Console()
    if not entries:
        console.print("No entries found.")
        return

    counts = Counter(entry["mood"] or "unknown" for entry in entries)
    title = "Mood Trend"
    if last_days is not None:
        title = f"Mood Trend (last {last_days} days)"

    table = Table(title=title)
    table.add_column("Mood")
    table.add_column("Count", justify="right")
    table.add_column("Bar")

    max_count = max(counts.values())
    for mood_name, count in counts.most_common():
        width = max(1, round((count / max_count) * 20))
        table.add_row(mood_name, str(count), "█" * width)

    console.print(table)

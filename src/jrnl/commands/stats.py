from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

import click
from rich.console import Console
from rich.table import Table

from jrnl.config import ensure_config
from jrnl.db import connect, initialize_database, list_entries


def _parse_date(created_at: str) -> date:
    return datetime.fromisoformat(created_at).date()


def _streaks(dates: list[date]) -> tuple[int, int]:
    if not dates:
        return 0, 0

    ordered = sorted(set(dates))
    longest = 1
    run = 1
    for previous, current in zip(ordered, ordered[1:]):
        if current - previous == timedelta(days=1):
            run += 1
        else:
            longest = max(longest, run)
            run = 1
    longest = max(longest, run)

    current = 1
    for previous, current_date in zip(reversed(ordered[:-1]), reversed(ordered[1:])):
        if current_date - previous == timedelta(days=1):
            current += 1
        else:
            break

    return current, longest


@click.command()
def stats() -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    with connect(config.storage.db_path) as connection:
        entries = list_entries(connection)

    console = Console()
    if not entries:
        console.print("No entries yet.")
        return

    source_counts = Counter(entry["source"] for entry in entries)
    mood_counts = Counter((entry["mood"] or "unknown") for entry in entries)
    tag_counts = Counter(
        tag
        for entry in entries
        for tag in (entry["tags"].split(", ") if entry["tags"] else [])
        if tag
    )
    dates = [_parse_date(entry["created_at"]) for entry in entries]
    current_streak, longest_streak = _streaks(dates)

    console.print(f"Entries: {len(entries)}")
    console.print(f"Current streak: {current_streak}")
    console.print(f"Longest streak: {longest_streak}")

    source_table = Table(title="Source Split")
    source_table.add_column("Source")
    source_table.add_column("Count", justify="right")
    for source in ("write", "talk"):
        source_table.add_row(source, str(source_counts.get(source, 0)))
    console.print(source_table)

    tag_table = Table(title="Top Tags")
    tag_table.add_column("Tag")
    tag_table.add_column("Count", justify="right")
    for tag, count in tag_counts.most_common(5):
        tag_table.add_row(tag, str(count))
    console.print(tag_table)

    mood_table = Table(title="Mood Distribution")
    mood_table.add_column("Mood")
    mood_table.add_column("Count", justify="right")
    for mood, count in mood_counts.most_common():
        mood_table.add_row(mood, str(count))
    console.print(mood_table)

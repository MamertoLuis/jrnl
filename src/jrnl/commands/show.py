from __future__ import annotations

import json

import click
from rich.console import Console

from jrnl.config import ensure_config
from jrnl.db import connect, get_entry, get_entry_tags, get_transcript, initialize_database


@click.command()
@click.argument("entry_id", type=int)
@click.option("--transcript", is_flag=True, default=False)
def show(entry_id: int, transcript: bool) -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    with connect(config.storage.db_path) as connection:
        entry = get_entry(connection, entry_id)
        if entry is None:
            raise click.ClickException(f"Entry {entry_id} not found")

        tags = get_entry_tags(connection, entry_id)
        transcript_row = get_transcript(connection, entry_id) if transcript else None

    console = Console()
    console.print(f"[bold]Entry {entry['id']}[/bold]")
    console.print(f"Date: {entry['created_at']}")
    console.print(f"Source: {entry['source']}")
    console.print(f"Mood: {entry['mood'] or ''}")
    console.print(f"Tags: {', '.join(tags)}")
    if entry["summary"]:
        console.print(f"Summary: {entry['summary']}")
    console.print("")
    console.print(entry["raw_text"])

    if transcript and transcript_row is not None:
        console.print("")
        console.print("[bold]Transcript[/bold]")
        try:
            console.print(json.dumps(json.loads(transcript_row["raw_json"]), indent=2))
        except json.JSONDecodeError:
            console.print(transcript_row["raw_json"])

from __future__ import annotations

import click

from jrnl.config import ensure_config
from jrnl.db import connect, get_entry, get_entry_tags, initialize_database, update_entry
from jrnl.enrichment import enrich_entry
from jrnl.ollama_client import OllamaClient


@click.command()
@click.argument("entry_id", type=int)
def reprocess(entry_id: int) -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    with connect(config.storage.db_path) as connection:
        entry = get_entry(connection, entry_id)
        if entry is None:
            raise click.ClickException(f"Entry {entry_id} not found")
        existing_tags = get_entry_tags(connection, entry_id)

    client = OllamaClient(config.ollama.host, config.ollama.timeout_seconds)
    enrichment = enrich_entry(
        client,
        model=config.ollama.model,
        entry_text=entry["raw_text"],
        existing_tags=existing_tags,
    )

    with connect(config.storage.db_path) as connection:
        update_entry(
            connection,
            entry_id=entry_id,
            raw_text=entry["raw_text"],
            summary=enrichment.summary,
            mood=enrichment.mood,
            tags=enrichment.tags,
        )

    click.echo(f"Reprocessed entry #{entry_id}.")

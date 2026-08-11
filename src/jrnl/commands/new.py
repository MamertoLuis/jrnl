from __future__ import annotations

import click
from rich.console import Console

from jrnl.config import ensure_config
from jrnl.db import connect, initialize_database, list_tags, save_entry
from jrnl.editor import edit_text
from jrnl.enrichment import enrich_entry
from jrnl.ollama_client import OllamaClient


@click.command()
def new() -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    try:
        raw_text = edit_text(initial_text="", configured_command=config.editor.command)
    except OSError as exc:
        raise click.ClickException(f"Could not open editor: {exc}") from exc

    entry_text = "\n".join(raw_text.replace("\r\n", "\n").splitlines()).strip()
    if not entry_text:
        click.echo("Blank entry discarded.")
        return

    client = OllamaClient(config.ollama.host, config.ollama.timeout_seconds)
    console = Console()
    with connect(config.storage.db_path) as connection:
        existing_tags = list_tags(connection)
        with console.status("Enriching entry...", spinner="dots"):
            enrichment = enrich_entry(
                client,
                model=config.ollama.model,
                entry_text=entry_text,
                existing_tags=existing_tags,
            )

        with console.status("Saving entry...", spinner="dots"):
            entry_id = save_entry(
                connection,
                source="write",
                raw_text=entry_text,
                summary=enrichment.summary,
                mood=enrichment.mood,
                tags=enrichment.tags,
            )

    click.echo(f"Saved entry #{entry_id}.")

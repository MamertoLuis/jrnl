from __future__ import annotations

import click

from jrnl.config import ensure_config
from jrnl.db import connect, delete_entry, initialize_database


@click.command()
@click.argument("entry_id", type=int)
def delete(entry_id: int) -> None:
    config = ensure_config()
    initialize_database(config.storage.db_path)

    if not click.confirm(f"Delete entry #{entry_id}?", default=False):
        click.echo("Cancelled.")
        return

    with connect(config.storage.db_path) as connection:
        deleted = delete_entry(connection, entry_id)

    if not deleted:
        raise click.ClickException(f"Entry {entry_id} not found")

    click.echo(f"Deleted entry #{entry_id}.")

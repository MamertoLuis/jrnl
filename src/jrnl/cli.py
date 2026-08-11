from __future__ import annotations

import click

from jrnl.commands.delete import delete
from jrnl.commands.edit import edit
from jrnl.commands.list import list_entries
from jrnl.commands.mood import mood
from jrnl.commands.new import new
from jrnl.commands.reprocess import reprocess
from jrnl.commands.show import show
from jrnl.commands.stats import stats
from jrnl.commands.talk import talk


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(new)
cli.add_command(talk)
cli.add_command(list_entries, name="list")
cli.add_command(show)
cli.add_command(edit)
cli.add_command(delete)
cli.add_command(stats)
cli.add_command(mood)
cli.add_command(reprocess)


def main() -> None:
    cli()

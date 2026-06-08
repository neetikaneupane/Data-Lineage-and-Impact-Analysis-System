import json
import click
from lineage.analysis.traversal import upstream, downstream, impact


@click.group()
def cli():
    """Data Lineage & Impact Analysis CLI"""
    pass


@cli.command()
@click.argument("table_column")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def up(table_column, fmt):
    """Show what feeds into TABLE.COLUMN (upstream)"""
    table, column = _parse_arg(table_column)
    rows = upstream(table, column)

    if not rows:
        click.echo(f"No upstream found for {table_column}")
        return

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    click.echo(f"\nUpstream of {table_column}:\n")
    for row in rows:
        depth = row["depth"]
        src   = f"{row['source_table']}.{row['source_column']}"
        files = " -> ".join(row["sql_files"])
        click.echo(f"  [depth {depth}] {src}")
        click.echo(f"           via: {files}\n")


@cli.command()
@click.argument("table_column")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def down(table_column, fmt):
    """Show what TABLE.COLUMN feeds into (downstream)"""
    table, column = _parse_arg(table_column)
    rows = downstream(table, column)

    if not rows:
        click.echo(f"No downstream found for {table_column}")
        return

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    click.echo(f"\nDownstream of {table_column}:\n")
    for row in rows:
        depth = row["depth"]
        tgt   = f"{row['target_table']}.{row['target_column']}"
        files = " -> ".join(row["sql_files"])
        click.echo(f"  [depth {depth}] {tgt}")
        click.echo(f"           via: {files}\n")


@cli.command()
@click.argument("table_column")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def impact(table_column, fmt):
    """Show all downstream columns and scripts affected by a change to TABLE.COLUMN"""
    from lineage.analysis.traversal import impact as impact_fn
    table, column = _parse_arg(table_column)
    rows = impact_fn(table, column)

    if not rows:
        click.echo(f"No impact found for {table_column}")
        return

    if fmt == "json":
        click.echo(json.dumps(rows, indent=2))
        return

    click.echo(f"\nImpact analysis for change to {table_column}:\n")
    for row in rows:
        depth    = row["depth"]
        affected = f"{row['affected_table']}.{row['affected_column']}"
        scripts  = " -> ".join(row["via_scripts"])
        click.echo(f"  [depth {depth}] {affected}")
        click.echo(f"           via: {scripts}\n")


def _parse_arg(table_column: str):
    parts = table_column.split(".")
    if len(parts) != 2:
        raise click.BadParameter("Format must be table.column e.g. raw_customers.email")
    return parts[0], parts[1]


if __name__ == "__main__":
    cli()
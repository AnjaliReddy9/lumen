import click

from lumen import __version__
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse
from lumen.warehouse.postgres_warehouse import PostgresWarehouse


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(f"lumen {__version__}")


@main.group("schema")
def schema_group() -> None:
    pass


@schema_group.command("describe")
@click.option("--warehouse", type=click.Choice(["duckdb", "postgres"]), required=True)
@click.option("--path", type=str, default=None, help="DuckDB database file or SQLite file path")
@click.option("--url", type=str, default=None, help="SQLAlchemy URL for Postgres")
def schema_describe(warehouse: str, path: str | None, url: str | None) -> None:
    if warehouse == "duckdb":
        if path is None:
            raise click.UsageError("--path is required for duckdb")
        wh: DuckDBWarehouse | PostgresWarehouse = DuckDBWarehouse(path)
    else:
        if url is None:
            raise click.UsageError("--url is required for postgres")
        wh = PostgresWarehouse(url)
    try:
        schema = wh.introspect()
        click.echo(f"tables: {len(schema.tables)}")
        for table in sorted(schema.tables, key=lambda t: t.name):
            click.echo(
                f"{table.name}: columns={len(table.columns)} foreign_keys={len(table.foreign_keys)}"
            )
    finally:
        wh.close()

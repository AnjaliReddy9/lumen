from pathlib import Path

import click

from lumen import __version__
from lumen.semantic.loader import load_semantic_model
from lumen.semantic.validator import validate_semantic_model
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


@main.group("semantic")
def semantic_group() -> None:
    pass


@semantic_group.command("validate")
@click.option(
    "--semantic-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory containing entities/, metrics/, and relationships.yaml",
)
@click.option("--warehouse", type=click.Choice(["duckdb", "postgres"]), required=True)
@click.option("--path", type=str, default=None, help="DuckDB database file or SQLite file path")
@click.option("--url", type=str, default=None, help="SQLAlchemy URL for Postgres")
def semantic_validate(
    semantic_dir: Path,
    warehouse: str,
    path: str | None,
    url: str | None,
) -> None:
    model = load_semantic_model(semantic_dir)
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
        validate_semantic_model(model, schema)
    except ValueError as err:
        raise click.ClickException(str(err)) from err
    finally:
        wh.close()
    n_ent = len(model.entities)
    n_met = len(model.metrics)
    n_rel = len(model.relationships)
    click.echo(
        "semantic model is valid "
        f"({n_ent} entities, {n_met} metrics, {n_rel} relationships)"
    )

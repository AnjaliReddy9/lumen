from pathlib import Path

import click

from lumen import __version__
from lumen.generation.generator import GeneratedSQL, SQLGenerator
from lumen.generation.runner import QueryResult, run_generated_sql
from lumen.interpretation.models import Interpretation
from lumen.llm.anthropic_provider import AnthropicProvider
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


def _open_warehouse(
    warehouse: str,
    path: str | None,
    url: str | None,
) -> DuckDBWarehouse | PostgresWarehouse:
    if warehouse == "duckdb":
        if path is None:
            raise click.UsageError("--path is required for duckdb")
        return DuckDBWarehouse(path)
    if url is None:
        raise click.UsageError("--url is required for postgres")
    return PostgresWarehouse(url)


def _print_query_result(result: QueryResult) -> None:
    if result.error:
        click.echo(f"execution error: {result.error}")
        return
    if not result.rows:
        click.echo("(no rows)")
        return
    cols = list(result.rows[0].keys())
    click.echo("\t".join(str(c) for c in cols))
    for row in result.rows:
        click.echo("\t".join(str(row.get(c, "")) for c in cols))


def _print_validation_summary(generated: GeneratedSQL) -> None:
    vr = generated.validation
    click.echo("--- validation ---")
    click.echo(f"valid: {'yes' if vr.valid else 'no'}")
    click.echo(f"attempts: {generated.attempts}")
    if vr.parsed_sql and vr.valid:
        click.echo("canonical_sql:")
        click.echo(vr.parsed_sql)
    if vr.issues:
        click.echo("issues:")
        for issue in vr.issues:
            click.echo(f"  [{issue.severity}] {issue.code}: {issue.message}")


def _print_interpretation(interp: Interpretation) -> None:
    click.echo("--- interpretation ---")
    summary = interp.intent.intent_summary.strip() or "(not stated)"
    click.echo(f"I understand this as: {summary}")
    click.echo(f"Entities: {', '.join(interp.intent.entities_referenced) or '(none)'}")
    click.echo(f"Metrics: {', '.join(interp.intent.metrics_referenced) or '(none)'}")
    click.echo(f"Dimensions: {', '.join(interp.intent.dimensions_referenced) or '(none)'}")
    click.echo(f"Time grain: {interp.intent.time_grain or '(none)'}")
    if interp.intent.filters:
        click.echo("Filters:")
        for f in interp.intent.filters:
            click.echo(
                f"  - {f.column_or_dimension} {f.operator} {f.value!r} ({f.confidence})"
            )
    else:
        click.echo("Filters: (none)")
    if interp.intent.sort:
        click.echo(
            f"Sort: {interp.intent.sort.column_or_dimension} "
            f"{interp.intent.sort.direction.upper()}"
        )
    else:
        click.echo("Sort: (none)")
    lim = interp.intent.limit if interp.intent.limit is not None else "(none)"
    click.echo(f"Limit: {lim}")
    click.echo(f"Interpreter confidence: {interp.confidence}")
    if interp.ambiguities:
        click.echo("")
        click.echo("Ambiguities (resolve in a follow-up run or use --auto-resolve):")
        for i, amb in enumerate(interp.ambiguities, start=1):
            opts = "; ".join(amb.options)
            d = amb.suggested_default or "(no default)"
            click.echo(f"  {i}. {amb.description}")
            click.echo(f"     Options: {opts}")
            click.echo(f"     Default: {d}")


def _collect_resolutions(interp: Interpretation, auto_resolve: bool) -> dict[str, str]:
    resolutions: dict[str, str] = {}
    if not interp.ambiguities:
        return resolutions
    if auto_resolve:
        click.echo("")
        click.echo("--- auto-resolve ---")
        for amb in interp.ambiguities:
            pick = amb.suggested_default if amb.suggested_default else amb.options[0]
            resolutions[amb.description] = pick
            click.echo(f"{amb.description!r} -> {pick!r}")
        return resolutions

    click.echo("")
    click.echo("--- ambiguities ---")
    for i, amb in enumerate(interp.ambiguities, start=1):
        click.echo(f"{i}. {amb.description}")
        letters = [chr(ord("a") + j) for j in range(len(amb.options))]
        for j, opt in enumerate(amb.options):
            click.echo(f"   {letters[j]}) {opt}")
        default_label = amb.suggested_default if amb.suggested_default else "(first option)"
        click.echo(f"   Default: {default_label}")
        while True:
            hint = "/".join(letters)
            raw = click.prompt(
                f"Choose [{hint}, or Enter for default]",
                default="",
                show_default=False,
            )
            raw_st = raw.strip()
            if not raw_st:
                chosen = amb.suggested_default if amb.suggested_default else amb.options[0]
                break
            if len(raw_st) == 1 and raw_st.lower() in letters:
                idx = ord(raw_st.lower()) - ord("a")
                chosen = amb.options[idx]
                break
            click.echo("Invalid choice; type a letter or press Enter for the default.")
        resolutions[amb.description] = chosen
    return resolutions


@main.group("query")
def query_group() -> None:
    pass


@query_group.command("ask")
@click.argument("question", nargs=-1, required=True)
@click.option(
    "--semantic-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
)
@click.option("--warehouse", type=click.Choice(["duckdb", "postgres"]), required=True)
@click.option("--path", type=str, default=None, help="DuckDB database file or SQLite file path")
@click.option("--url", type=str, default=None, help="SQLAlchemy URL for Postgres")
@click.option(
    "--dialect",
    default="sqlite",
    show_default=True,
    help="SQL dialect name for the prompt and parser",
)
@click.option("--dry-run", is_flag=True, help="Generate SQL only; do not execute")
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Skip schema-aware SQL validation (debug only; execution may still fail)",
)
@click.option(
    "--no-interpret",
    is_flag=True,
    help="Skip explain-back and interpretation; generate SQL directly (session 4 path)",
)
@click.option(
    "--explain-only",
    is_flag=True,
    help="Run interpretation only; do not generate or execute SQL",
)
@click.option(
    "--auto-resolve",
    is_flag=True,
    help="Pick default or first ambiguity option without prompting (non-interactive)",
)
@click.pass_context
def query_ask(
    ctx: click.Context,
    question: tuple[str, ...],
    semantic_dir: Path,
    warehouse: str,
    path: str | None,
    url: str | None,
    dialect: str,
    dry_run: bool,
    skip_validation: bool,
    no_interpret: bool,
    explain_only: bool,
    auto_resolve: bool,
) -> None:
    question_text = " ".join(question).strip()
    if not question_text:
        raise click.UsageError("question is empty")
    if no_interpret and explain_only:
        raise click.UsageError("--no-interpret and --explain-only cannot be used together")
    if no_interpret and auto_resolve:
        raise click.UsageError("--no-interpret and --auto-resolve cannot be used together")

    model = load_semantic_model(semantic_dir)
    wh = _open_warehouse(warehouse, path, url)
    try:
        schema = wh.introspect()
        validate_semantic_model(model, schema)
        provider = AnthropicProvider()
        gen = SQLGenerator(provider)

        if no_interpret:
            generated = gen.generate(
                question_text, model, schema, dialect, skip_validation=skip_validation
            )
            click.echo("--- generated sql ---")
            click.echo(generated.sql)
            _print_validation_summary(generated)
            if not skip_validation and not generated.validation.valid:
                click.echo("validation failed; not executing SQL.")
                ctx.exit(1)
            if dry_run:
                return
            result = run_generated_sql(generated, wh)
            click.echo("--- result ---")
            _print_query_result(result)
            return

        try:
            interp, sql_gen = gen.generate_with_interpretation(
                question_text, model, schema, dialect, skip_validation=skip_validation
            )
        except TypeError as err:
            raise click.ClickException(str(err)) from err

        _print_interpretation(interp)
        if explain_only:
            return

        resolutions: dict[str, str] = {}
        if sql_gen is None:
            resolutions = _collect_resolutions(interp, auto_resolve)
            interp, sql_gen = gen.generate_with_resolutions(
                question_text,
                model,
                schema,
                dialect,
                resolutions,
                skip_validation=skip_validation,
            )

        if sql_gen is None:
            raise RuntimeError("SQL generation failed after ambiguity resolution")
        generated = sql_gen
        click.echo("")
        click.echo("--- generated sql ---")
        click.echo(generated.sql)
        _print_validation_summary(generated)
        if not skip_validation and not generated.validation.valid:
            click.echo("validation failed; not executing SQL.")
            ctx.exit(1)
        if dry_run:
            return
        result = run_generated_sql(generated, wh)
        click.echo("--- result ---")
        _print_query_result(result)
    except ValueError as err:
        raise click.ClickException(str(err)) from err
    finally:
        wh.close()

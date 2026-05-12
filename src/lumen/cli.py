import json
import os
import uuid
from pathlib import Path

import click

from lumen import __version__
from lumen.eval.fake_provider import EvalGroundTruthFakeProvider
from lumen.eval.load_cases import load_cases_for_benchmark
from lumen.eval.models import EvalConfig
from lumen.eval.runner import EvalRunner
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


@main.group("eval")
def eval_group() -> None:
    pass


@eval_group.command("run")
@click.option(
    "--benchmark",
    type=click.Choice(["chinook", "spider", "bird", "nyc_open_data"]),
    required=True,
)
@click.option(
    "--semantic-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
)
@click.option("--warehouse", type=click.Choice(["duckdb", "postgres"]), required=True)
@click.option("--path", type=str, default=None, help="DuckDB file, SQLite file, or Postgres URL")
@click.option("--url", type=str, default=None, help="Postgres URL (alternative to --path)")
@click.option(
    "--dialect",
    default="sqlite",
    show_default=True,
    help="SQL dialect for validation and prompts",
)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--sample", type=int, default=None, help="Run only the first N cases")
@click.option("--no-interpret", is_flag=True, help="Skip interpretation / explain-back")
@click.option("--skip-validation", is_flag=True, help="Pass skip_validation to generator")
@click.option("--spider-path", type=click.Path(path_type=Path), default=None)
@click.option("--bird-path", type=click.Path(path_type=Path), default=None)
@click.option("--spider-db-id", type=str, default=None)
@click.option("--bird-db-id", type=str, default=None)
@click.option("--seed", type=int, default=42)
@click.option("--max-retries", type=int, default=2)
@click.option("--max-concurrency", type=int, default=4)
@click.option("--max-cost-usd", type=float, default=10.0)
@click.option(
    "--fake-llm",
    is_flag=True,
    help="Deterministic fake keyed on questions with expected_sql (no Anthropic)",
)
@click.option("--run-id", type=str, default=None, help="Optional run id (default: random UUID)")
def eval_run(
    benchmark: str,
    semantic_dir: Path,
    warehouse: str,
    path: str | None,
    url: str | None,
    dialect: str,
    output: Path,
    sample: int | None,
    no_interpret: bool,
    skip_validation: bool,
    spider_path: Path | None,
    bird_path: Path | None,
    spider_db_id: str | None,
    bird_db_id: str | None,
    seed: int,
    max_retries: int,
    max_concurrency: int,
    max_cost_usd: float,
    fake_llm: bool,
    run_id: str | None,
) -> None:
    from lumen.interpretation.interpreter import QueryInterpreter

    cases = load_cases_for_benchmark(
        benchmark,
        spider_path=spider_path,
        bird_path=bird_path,
        spider_db_id=spider_db_id,
        bird_db_id=bird_db_id,
        n_cases=100,
        seed=seed,
    )
    model = load_semantic_model(semantic_dir)
    if warehouse == "postgres" and url is None and path:
        url = path
    if warehouse == "duckdb" and path is None:
        raise click.UsageError("--path is required for duckdb")
    if warehouse == "postgres" and url is None:
        raise click.UsageError("--url (or --path with URL) is required for postgres")
    wh = _open_warehouse(warehouse, path, url)
    try:
        schema = wh.introspect()
        validate_semantic_model(model, schema)
        if fake_llm or os.environ.get("LUMEN_FAKE_LLM"):
            mapping = {c.question.strip(): c.expected_sql for c in cases if c.expected_sql}
            fake = EvalGroundTruthFakeProvider(mapping)
            model_name = fake.model_name
            gen = SQLGenerator(
                fake,
                max_retries=max_retries,
                interpreter=QueryInterpreter(fake),
            )
        else:
            anthropic = AnthropicProvider()
            model_name = anthropic.model_name
            gen = SQLGenerator(anthropic, max_retries=max_retries)
        cfg = EvalConfig(
            use_interpretation=not no_interpret,
            max_retries=max_retries,
            max_concurrency=max_concurrency,
            max_cost_usd=max_cost_usd,
            sample_size=sample,
            skip_validation=skip_validation,
        )
        rid = run_id or str(uuid.uuid4())
        runner = EvalRunner(gen, wh)
        run = runner.run(
            cases,
            cfg,
            semantic_model=model,
            schema=schema,
            dialect=dialect,
            benchmark=benchmark,
            model_name=model_name,
            run_id=rid,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        click.echo(f"wrote {output}")
        click.echo(
            f"summary: accuracy={run.summary.execution_accuracy:.3f} "
            f"validation={run.summary.validation_pass_rate:.3f} "
            f"gen_ok={run.summary.generation_success_rate:.3f} "
            f"cost_usd={run.summary.total_cost_usd:.4f}"
        )
    except ValueError as err:
        raise click.ClickException(str(err)) from err
    finally:
        wh.close()


@eval_group.command("list")
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("benchmarks/runs"),
)
def eval_list(runs_dir: Path) -> None:
    if not runs_dir.is_dir():
        click.echo("(no runs directory)")
        return
    rows = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not rows:
        click.echo("(no eval run json files)")
        return
    for p in rows:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            rid = data.get("run_id", p.stem)
            bench = data.get("benchmark", "")
            done = data.get("cases_completed", "")
            click.echo(f"{rid}\t{bench}\t{done}")
        except Exception:
            click.echo(f"{p.name}\t(unreadable)")


@eval_group.command("show")
@click.argument("run_id")
@click.option(
    "--runs-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("benchmarks/runs"),
)
def eval_show(run_id: str, runs_dir: Path) -> None:
    from lumen.eval.models import EvalRun

    for p in runs_dir.glob("*.json"):
        try:
            run = EvalRun.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if run.run_id == run_id or p.stem == run_id:
            click.echo(f"run_id: {run.run_id}")
            click.echo(f"benchmark: {run.benchmark}")
            click.echo(f"model: {run.model}")
            click.echo(f"cases: {run.cases_completed}/{run.cases_total}")
            click.echo("summary:")
            s = run.summary
            click.echo(f"  execution_accuracy: {s.execution_accuracy}")
            click.echo(f"  validation_pass_rate: {s.validation_pass_rate}")
            click.echo(f"  generation_success_rate: {s.generation_success_rate}")
            click.echo(f"  avg_latency_ms: {s.avg_latency_ms}")
            click.echo(f"  total_cost_usd: {s.total_cost_usd}")
            return
    raise click.ClickException(f"run not found: {run_id}")


@main.group("api")
def api_group() -> None:
    pass


@api_group.command("serve")
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, help="Dev auto-reload (local only)")
def api_serve(host: str, port: int, reload: bool) -> None:
    import uvicorn

    uvicorn.run("lumen.api.app:app", host=host, port=port, reload=reload)

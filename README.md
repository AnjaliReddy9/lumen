# Lumen

Natural-language questions over a real warehouse, grounded in a YAML semantic layer and Claude-generated SQL.

### Schema-aware validation

Lumen parses generated SQL and validates every table and column reference against the live warehouse schema before execution. Hallucinated identifiers are collected into a structured result, and the model may be asked to correct them in a follow-up turn, with available column names surfaced in the retry prompt. Today this works for `SELECT` queries including joins, common table expressions, and subqueries, with up to two correction rounds after the initial generation. `INSERT`, `UPDATE`, `DELETE`, and DDL are rejected by the validator because Lumen is read-only by design.

### What's interesting about it

**Explain-back.** Before SQL is generated, the default `lumen query ask` path calls an interpreter model that returns structured JSON describing the question: a one-line summary, referenced semantic entities and metrics, inferred filters, sort, and limit. That interpretation is printed under `--- interpretation ---` every time so you can catch misunderstandings early.

**Ambiguity resolution.** When the interpreter spots underspecified phrasing (for example a bare geography or "top customers" without a metric), it emits discrete options with a suggested default. The CLI walks you through each item with lettered choices; scripts can pass `--auto-resolve` to take defaults without prompts. Chosen answers are fed back into a second interpretation call before SQL generation.

## Status

Lumen is in active development. Today you can introspect Postgres or DuckDB-backed SQLite, validate a YAML semantic directory against the live catalog, and run `lumen query ask` with explain-back, optional ambiguity prompts, schema-aware SQL validation, and captured execution results. Flags cover dry runs, skipping validation for debugging, skipping interpretation for benchmarks (`--no-interpret`), interpretation-only previews (`--explain-only`), and non-interactive ambiguity defaults (`--auto-resolve`). What is not here yet includes a web UI, offline benchmark tables, and prompt caching. Those are planned as the pipeline hardens.

## Quickstart

Clone the repository, create a virtual environment with uv, and install the package in editable mode with dev dependencies:

```bash
git clone https://github.com/AnjaliReddy9/lumen.git
cd lumen
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Set an Anthropic API key in your shell. Both interpretation and SQL generation use the official `anthropic` SDK:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Build a local Chinook database from the bundled SQL fixture (SQLite file on disk; DuckDB opens it via `--path`):

```bash
sqlite3 /tmp/chinook.sqlite < tests/fixtures/chinook.sql
```

Confirm the warehouse and semantic layer line up:

```bash
lumen schema describe --warehouse duckdb --path /tmp/chinook.sqlite
lumen semantic validate --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite
```

Ask a question. By default the CLI prints interpretation, prompts for any ambiguities, then prints generated SQL, validation, and a tab-separated result table. Use `--explain-only` to stop after interpretation, `--auto-resolve` for scripted runs, or `--no-interpret` to match the older single-step SQL flow.

```bash
lumen query ask "What is the total revenue by country?" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite
```

CLI flags are documented in [docs/usage.md](docs/usage.md). Validation internals are in [docs/validation.md](docs/validation.md). Interpretation and explain-back are in [docs/interpretation.md](docs/interpretation.md).

## Project structure

```text
src/lumen/
  __init__.py           Package version exposed to the CLI.
  cli.py                Click entrypoint: schema, semantic, and query commands.
  generation/
    prompt.py           SQL and correction prompts; optional interpreted intent block.
    generator.py        SQL loop plus generate_with_interpretation / resolutions.
    runner.py           Executes generated SQL and captures rows or errors.
  interpretation/
    models.py           QueryIntent, ambiguities, Interpretation Pydantic types.
    prompt.py           Interpreter system/user prompts and schema context.
    tool_spec.py        Anthropic submit_interpretation tool JSON schema.
    interpreter.py      QueryInterpreter with tool call + JSON validation retries.
  llm/
    base.py             LLMProvider protocol (text in, text out).
    anthropic_provider.py  Claude text generation and tool-use helper.
  semantic/
    models.py           Pydantic types for entities, metrics, and relationships.
    loader.py           Loads YAML from a semantic directory.
    validator.py        Checks semantic definitions against introspected schema.
  validation/
    parser.py           sqlglot wrapper: parse SQL for a dialect or return None.
    models.py           ValidationIssue and ValidationResult types.
    validator.py        AST walk for tables, columns, CTEs, and subqueries.
  warehouse/
    base.py             Warehouse protocol and shared types.
    schema.py           Introspected table, column, and foreign-key records.
    duckdb_warehouse.py DuckDB-backed introspection and execution.
    postgres_warehouse.py Postgres via SQLAlchemy URL.
```

Tests and fixtures live under `tests/`, including `tests/fixtures/chinook.sql` and `tests/fixtures/chinook_semantic/` for local runs.

## License

MIT

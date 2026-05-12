# Lumen

Natural-language questions over a real warehouse, grounded in a YAML semantic layer and Claude-generated SQL.

### Schema-aware validation

Lumen parses generated SQL and validates every table and column reference against the live warehouse schema before execution. Hallucinated identifiers are collected into a structured result, and the model may be asked to correct them in a follow-up turn, with available column names surfaced in the retry prompt. Today this works for `SELECT` queries including joins, common table expressions, and subqueries, with up to two correction rounds after the initial generation. `INSERT`, `UPDATE`, `DELETE`, and DDL are rejected by the validator because Lumen is read-only by design.

## Status

Lumen is in active development. Today you can point the CLI at a DuckDB-attached SQLite file or Postgres, introspect table and column metadata, load a semantic model from a directory of YAML files, validate that model against the live schema, and ask an analytics question in plain English. The pipeline builds prompts from the question, semantic definitions, and physical schema, calls the Anthropic API for SQL, validates identifiers with sqlglot, optionally retries with a corrective prompt when validation fails, runs the statement only if validation succeeded (unless you opt out with a debug flag), and prints rows or a captured execution error. What is not here yet includes ambiguity resolution and explain-back to the user before running, a web UI, and benchmark numbers. Those are planned as the pipeline hardens.

## Quickstart

Clone the repository, create a virtual environment with uv, and install the package in editable mode with dev dependencies:

```bash
git clone https://github.com/AnjaliReddy9/lumen.git
cd lumen
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Set an Anthropic API key in your shell. SQL generation uses the official `anthropic` SDK and does not read a committed `.env` file:

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

Ask a question. The CLI prints the generated SQL, a short validation summary (including canonical SQL when validation passes), then a tab-separated result table. If validation still fails after retries, it prints the issues and exits without executing. Add `--dry-run` to skip execution while still calling the model; add `--skip-validation` only when debugging prompts or parser behavior.

```bash
lumen query ask "What is the total revenue by country?" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite
```

CLI flags and behavior for the three commands are documented in [docs/usage.md](docs/usage.md). How validation works under the hood is documented in [docs/validation.md](docs/validation.md).

## Project structure

```text
src/lumen/
  __init__.py           Package version exposed to the CLI.
  cli.py                Click entrypoint: schema, semantic, and query commands.
  generation/
    prompt.py           Builds initial and corrective prompts for SQL generation.
    generator.py        LLM loop, markdown cleanup, validation, and retries.
    runner.py           Executes generated SQL and captures rows or errors.
  llm/
    base.py             LLMProvider protocol (text in, text out).
    anthropic_provider.py  Claude client wrapper used by query ask.
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

# Lumen

Natural-language questions over a real warehouse, grounded in a YAML semantic layer and Claude-generated SQL.

## Status

Lumen is in active development. Today you can point the CLI at a DuckDB-attached SQLite file or Postgres, introspect table and column metadata, load a semantic model from a directory of YAML files, validate that model against the live schema, and ask an analytics question in plain English: the tool builds a prompt from the question, semantic definitions, and schema, calls the Anthropic API for a single SQL statement, optionally runs it, and prints the result or the database error. What is not here yet includes schema-aware validation of generated SQL, retry or ambiguity handling, explain-back to the user before execution, a web UI, and benchmark numbers. Those are planned as the pipeline hardens.

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

Ask a question. The CLI prints the generated SQL, then a tab-separated result table (or an execution error string if the model produced invalid SQL):

```bash
lumen query ask "What is the total revenue by country?" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite
```

To print SQL only without executing against the warehouse, add `--dry-run`. Generation still calls the API, so the key must remain set.

CLI flags and behavior for the three commands are documented in [docs/usage.md](docs/usage.md).

## Project structure

```text
src/lumen/
  __init__.py           Package version exposed to the CLI.
  cli.py                Click entrypoint: schema, semantic, and query commands.
  generation/
    prompt.py           Builds system and user prompts for SQL generation.
    generator.py        Calls an LLM provider and returns cleaned SQL plus raw text.
    runner.py           Executes generated SQL and captures rows or errors.
  llm/
    base.py             LLMProvider protocol (text in, text out).
    anthropic_provider.py  Claude client wrapper used by query ask.
  semantic/
    models.py           Pydantic types for entities, metrics, and relationships.
    loader.py           Loads YAML from a semantic directory.
    validator.py        Checks semantic definitions against introspected schema.
  warehouse/
    base.py             Warehouse protocol and shared types.
    schema.py           Introspected table, column, and foreign-key records.
    duckdb_warehouse.py DuckDB-backed introspection and execution.
    postgres_warehouse.py Postgres via SQLAlchemy URL.
```

Tests and fixtures live under `tests/`, including `tests/fixtures/chinook.sql` and `tests/fixtures/chinook_semantic/` for local runs.

## License

MIT

# CLI usage

This page describes the Lumen commands available today. Install the package and activate your environment as in the [project README](../README.md#quickstart).

## `lumen schema describe`

Prints a high-level summary of every table in the connected warehouse: column count and foreign-key count per table, after introspection.

**Usage**

```bash
lumen schema describe --warehouse duckdb --path /path/to/database.sqlite
lumen schema describe --warehouse postgres --url postgresql+psycopg2://user:pass@host:5432/dbname
```

**Flags**

- `--warehouse` (required): `duckdb` or `postgres`.
- `--path` (required for DuckDB): path to a DuckDB file or a SQLite file DuckDB can attach.
- `--url` (required for Postgres): SQLAlchemy database URL.

**Output**

The first line is `tables: N`. Each following line looks like `TableName: columns=C foreign_keys=F`, sorted by table name.

---

## `lumen semantic validate`

Loads a semantic model from a directory (`entities/`, `metrics/`, `relationships.yaml`), introspects the warehouse, and validates that declared tables, columns, and join paths exist. Exits non-zero with a message if validation fails.

**Usage**

```bash
lumen semantic validate --semantic-dir path/to/model \
  --warehouse duckdb --path /path/to/database.sqlite
lumen semantic validate --semantic-dir path/to/model \
  --warehouse postgres --url postgresql+psycopg2://user:pass@host:5432/dbname
```

**Flags**

- `--semantic-dir` (required): existing directory containing the semantic YAML layout.
- `--warehouse` (required): `duckdb` or `postgres`.
- `--path` or `--url`: same rules as `schema describe`.

**Output**

On success, one line such as: `semantic model is valid (E entities, M metrics, R relationships)`.

---

## `lumen query ask`

Loads and validates the semantic model, builds a prompt from the question plus semantic text plus warehouse schema, calls Claude to produce SQL, then runs **schema-aware validation** on the result. If validation passes, the CLI executes the statement against the same warehouse (unless `--dry-run`). If validation fails after the configured retries, the CLI prints the issues and exits with code 1 without executing.

**Usage**

```bash
lumen query ask "Your question in natural language" \
  --semantic-dir path/to/model \
  --warehouse duckdb --path /path/to/database.sqlite
```

Append `--dry-run` to skip execution after printing SQL and validation. Set `ANTHROPIC_API_KEY` in the environment; both normal and dry-run paths invoke the API for generation (and for correction rounds when validation fails).

**Flags**

- `QUESTION...` (required): one or more words forming the question (shell quoting applies).
- `--semantic-dir` (required): semantic YAML directory, same as validate.
- `--warehouse` (required): `duckdb` or `postgres`.
- `--path` or `--url`: same as above.
- `--dialect` (optional, default `sqlite`): dialect name for the LLM prompt and for sqlglot parsing (e.g. `sqlite`, `postgresql`, `duckdb`). The CLI does not infer this from the warehouse yet.
- `--dry-run` (optional): generate and print output only; do not execute against the warehouse.
- `--skip-validation` (optional): do not run sqlglot validation or block execution on validation failure. Intended for debugging prompts; generated SQL may reference non-existent tables or columns.

**Output**

1. A line `--- generated sql ---`, then the latest generated SQL text (possibly after retries).
2. A block `--- validation ---` with `valid: yes` or `valid: no`, `attempts: N`, optional `canonical_sql:` when validation succeeded, and an `issues:` list with one line per problem (`[error] code: message`) when there are issues.
3. Unless `--dry-run` or validation ultimately failed (and `--skip-validation` was not used), a line `--- result ---` followed by either a tab-separated header and rows, `(no rows)`, or `execution error: ...` from DuckDB or Postgres.

If validation fails and `--skip-validation` is not set, you will see `validation failed; not executing SQL.` and the process exits with status 1. For details on validation, see [docs/validation.md](validation.md).

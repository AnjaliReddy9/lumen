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

Loads and validates the semantic model, builds a prompt from the question plus semantic text plus warehouse schema, calls Claude to produce one SQL string, prints it, then runs it against the same warehouse unless `--dry-run` is set.

**Usage**

```bash
lumen query ask "Your question in natural language" \
  --semantic-dir path/to/model \
  --warehouse duckdb --path /path/to/database.sqlite
```

Append `--dry-run` to skip execution after printing SQL. Set `ANTHROPIC_API_KEY` in the environment; both normal and dry-run paths invoke the API for generation.

**Flags**

- `QUESTION...` (required): one or more words forming the question (shell quoting applies).
- `--semantic-dir` (required): semantic YAML directory, same as validate.
- `--warehouse` (required): `duckdb` or `postgres`.
- `--path` or `--url`: same as above.
- `--dialect` (optional, default `sqlite`): dialect name embedded in the system prompt (e.g. `sqlite`, `postgresql`, `duckdb`). The CLI does not infer this from the warehouse yet.
- `--dry-run` (optional): generate and print SQL only.

**Output**

A line `--- generated sql ---`, then the SQL text. Without `--dry-run`, a line `--- result ---` follows: either a tab-separated header and rows, `(no rows)`, or `execution error: ...` with the database message. The implementation does not validate SQL before execution; invalid SQL surfaces as an execution error.

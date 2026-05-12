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

By default this command runs **interpretation first** (explain-back), optionally collects **ambiguity resolutions** interactively, then runs **SQL generation**, **schema-aware validation**, and warehouse execution. Set `ANTHROPIC_API_KEY` in the environment; interpretation and SQL generation each use the Anthropic API (interpretation uses a forced `submit_interpretation` tool call).

**Usage**

```bash
lumen query ask "Your question in natural language" \
  --semantic-dir path/to/model \
  --warehouse duckdb --path /path/to/database.sqlite
```

**Flags**

- `QUESTION...` (required): one or more words forming the question (shell quoting applies).
- `--semantic-dir` (required): semantic YAML directory, same as validate.
- `--warehouse` (required): `duckdb` or `postgres`.
- `--path` or `--url`: same as above.
- `--dialect` (optional, default `sqlite`): dialect name for prompts and sqlglot parsing.
- `--dry-run` (optional): skip execution after printing SQL and validation.
- `--skip-validation` (optional): skip sqlglot validation and execution guardrails (debug only).
- `--no-interpret` (optional): skip interpretation entirely; go straight to SQL generation (session 4 behavior). Incompatible with `--explain-only` and `--auto-resolve`.
- `--explain-only` (optional): print interpretation (and ambiguities if any) then exit; no SQL API call.
- `--auto-resolve` (optional): for each ambiguity, pick `suggested_default` when present, otherwise the first option, without `click.prompt`. Useful for scripts. Incompatible with `--no-interpret`.

**Output (default path)**

1. `--- interpretation ---` with summary, entity/metric/dimension lists, time grain, filters, sort, limit, and overall interpreter confidence. If the model flagged issues, an extra block lists each ambiguity with options and defaults before prompting.
2. If there were ambiguities and you did not pass `--explain-only`, either `--- auto-resolve ---` with one line per chosen default or `--- ambiguities ---` with lettered `click.prompt` lines until each item is resolved.
3. `--- generated sql ---` then validation and, unless `--dry-run`, `--- result ---` with tab-separated rows or an execution error string.

If validation fails and `--skip-validation` is not set, you will see `validation failed; not executing SQL.` and exit code 1. For validation details see [docs/validation.md](validation.md). For interpretation design see [docs/interpretation.md](interpretation.md).

**Example: interactive transcript**

The lines below are illustrative; model wording changes, but the headings are stable.

```
$ lumen query ask "Top 10 customers by spending in California" \
    --semantic-dir tests/fixtures/chinook_semantic \
    --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite

--- interpretation ---
I understand this as: Show the ten customers with the highest total invoice spend,
restricted to people in California.
Entities: customer, invoice
Metrics: total_revenue
Dimensions: ...
Time grain: (none)
Filters: (none)
Sort: (none)
Limit: 10
Interpreter confidence: medium

Ambiguities (resolve in a follow-up run or use --auto-resolve):
  1. "California" could mean Customer.State = 'California', Customer.State = 'CA',
     or a broader US filter.
     Options: Customer.State = 'California'; Customer.State = 'CA'; ...
     Default: Customer.State = 'California'

--- ambiguities ---
1. "California" could mean Customer.State = 'California', ...
   a) Customer.State = 'California'
   b) Customer.State = 'CA'
   Default: a
Choose [a/b, or Enter for default]: b

--- generated sql ---
SELECT ...
--- validation ---
valid: yes
attempts: 1
canonical_sql:
SELECT ...
--- result ---
...
```

**Example: auto-resolve (non-interactive)**

```bash
lumen query ask "Top customers in California" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite \
  --auto-resolve
```

You should see `--- auto-resolve ---` with each ambiguity description mapped to the chosen option string before SQL generation.

**Example: explain-only**

```bash
lumen query ask "Top customers in California" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite \
  --explain-only
```

Prints interpretation (including ambiguity text when present) and exits without SQL.

**Example: benchmark fast path**

```bash
lumen query ask "How many tracks are in each genre?" \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite \
  --no-interpret
```

Skips the interpreter call; output starts at `--- generated sql ---` as in session 4.

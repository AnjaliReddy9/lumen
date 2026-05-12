# Schema-aware SQL validation

This page is the design reference for how Lumen treats generated SQL before it ever reaches the warehouse. The problem is familiar to anyone who has shipped an LLM against a database: the model invents plausible table and column names, repeats names that exist in a different product, or joins the wrong entities. The database then returns a generic syntax or catalog error, and the user is left guessing whether the question was wrong, the model was wrong, or the data was missing. Lumen’s answer is to treat the warehouse catalog as authoritative and to validate every identifier in the generated query against that catalog using a deterministic parser, not a second LLM call.

## Approach

After Claude returns a candidate statement, Lumen parses it with [sqlglot](https://github.com/tobymao/sqlglot), a pure-Python parser that understands many dialects and exposes a structured AST. The validator walks scopes produced by sqlglot’s scope analysis: each `SELECT` (including branches inside `UNION`, subqueries in `WHERE` or `FROM`, and each CTE body) is considered on its own. Within a scope, every physical table reference is checked against the introspected `Schema` object that DuckDB or Postgres produced earlier in the CLI flow. If the base table name is not in that schema, the validator records an `unknown_table` issue.

Column checks reuse the same scope machinery. A qualified reference such as `Customer.Country` is resolved through the visible alias map (`FROM Customer AS c` maps `c` back to the physical `Customer` table), then the column name is compared to the column list on that table. An unqualified reference such as `Country` is accepted only if exactly one source in the current `SELECT` exposes a column with that name; if more than one source could supply it, the validator emits `ambiguous_column`, which mirrors the database’s own ambiguity rules and pushes the model toward explicit qualifiers on retry. If no source exposes the name, the result is `unknown_column`. For those errors, the message includes the sorted list of real column names on the relevant physical table so that both logs and the correction prompt carry concrete hints.

Derived scopes—common table expressions and inline subqueries in the `FROM` clause—are modeled as nested scopes rather than physical tables. Their output column sets are inferred from their `SELECT` list: explicit aliases and column names are collected, and `SELECT *` expands against the physical tables referenced inside that inner query so that an outer reference like `SELECT country FROM x` can be checked when `x` is defined as `SELECT * FROM Customer`. The validator does not execute any part of the query; it only inspects the static tree, which keeps validation fast and side-effect free.

## What is validated

The current implementation focuses on identifier existence for read-only `SELECT` shapes, including `WITH`, `JOIN`, and correlated-style nesting as sqlglot represents it. Aliases on tables are honored because validation keys off the same `selected_sources` map the scope builder uses for real engines. CTE names are treated as first-class sources whose columns come from their inner query. Subqueries in `IN` lists and similar predicates are separate scopes, so a bad column inside a nested `SELECT` is reported there rather than being mis-attributed to the outer query.

When the parser cannot produce an AST at all, validation returns a single `syntax_error` issue and does not attempt column walks. When the AST is present but the top-level statement is not a `SELECT` or `UNION` of selects (for example `INSERT` or `UPDATE`), validation fails with a clear message that only read-only select shapes are supported. That matches the product direction: Lumen is not a general-purpose SQL mutator.

## What is intentionally out of scope

Type compatibility—adding strings, comparing dates to integers, or applying aggregates to the wrong shape—is not checked. The semantic YAML layer may later constrain which metrics and dimensions are legal, but this validator is warehouse-schema-only: it does not prove that a metric expression matches the semantic model’s definitions. Query performance, row-level security predicates, and dialect-specific builtins that introduce opaque identifiers are also not modeled. If sqlglot cannot parse the text, validation stops with a single `syntax_error` issue and no column-level follow-up; that is by design so we never pretend to understand a half-parsed tree.

There is no second “LLM judge” that scores the SQL for plausibility. Anything that is not provable from the AST plus the catalog is explicitly deferred. That keeps the interview story crisp: the guarantee is about identifiers and scopes, not about business correctness.

## Retry behavior

`SQLGenerator` runs validation after each generation. When issues remain and retries are still allowed, Lumen builds a second prompt that includes the original question, the rejected SQL, each validation issue line (including the “available columns” text for unknown columns), and the same semantic plus physical schema block as the first turn. The system message is short: fix the SQL and return only the corrected statement. The default is two retries after the first attempt (three generations total). If the model still returns SQL that fails validation, the last attempt is returned to the caller with `valid: false`; the CLI refuses to execute it and exits with status 1 unless `--skip-validation` is set for debugging.

Retries cost tokens, but they are cheaper than round-tripping a hallucinated column to production or burning an analyst’s time on a cryptic database error. The list-of-issues design means the first failed pass can report both a bad table and a bad column together, so the model is less likely to fix one problem at a time across many expensive turns.

## Known limitations and non-goals

Recursive CTEs receive only the level of analysis sqlglot’s scope metadata supports today. If the recursive member references columns that only appear after unfolding the recursion, we do not simulate fixpoint expansion; validating that class of query is left to the engine and to future work. Polymorphic table functions, `LATERAL` pipelines, and vendor-specific table sources may not appear in `selected_sources` the same way a plain `JOIN` does. Those shapes are uncommon in the analytics `SELECT` templates Lumen targets first.

Highly correlated subqueries can blur the line between inner and outer column ownership. The implementation filters columns by their nearest containing `SELECT` in the AST so that a predicate inside `IN (SELECT …)` is validated against the inner `FROM` clause, not the outer one. That heuristic matches the common Chinook-style patterns in the test suite. If a future dialect or sqlglot upgrade changes how “external” columns are classified, the unit tests under `tests/unit/test_validator.py` are the regression harness.

Multi-part identifiers with catalog or database prefixes (`main.Customer`) are accepted as long as the underlying table name matches an introspected table; Lumen’s current introspection does not model multi-catalog layouts, so validation is only as rich as the `Schema` object passed in. Finally, `SELECT *` on a join of two tables with overlapping column names produces a merged output set for validation purposes; SQLite and other engines have their own rules for duplicate names in result sets, and Lumen does not try to emulate every edge case there.

The goal of this layer is narrow and defensible: catch hallucinated identifiers before they hit the database, surface as many such problems in one pass as the AST walk allows, and give the model structured feedback when a second chance is warranted. Everything else remains the responsibility of the database, the semantic layer, or later sessions in the roadmap.

## Why sqlglot instead of sending SQL to the database for a dry run

A dry-run `PREPARE` or `EXPLAIN` against the warehouse would catch many of the same catalog errors, but it couples validation to a live connection, dialect-specific behavior, and side effects such as query logging or warehouse charges. It also tends to stop at the first error, whereas Lumen collects a list of issues so the model can repair several mistakes in one correction pass. sqlglot runs offline, works from the same dialect string the generator already uses for prompting, and keeps the validation path identical in CI and on a laptop without a warehouse socket.

Parsing also gives a canonical rendering of the statement (`parsed_sql` on success), which is useful when the model returns stylistically odd but valid SQL. The canonical form is not a prettification goal in itself; it is a stable string the rest of the pipeline can log or diff.

## Relationship to the semantic layer

Semantic validation (YAML entities and metrics against the warehouse) happens earlier in the CLI when the model is first loaded. Schema-aware SQL validation is orthogonal: it does not check whether a column corresponds to a declared dimension or whether a join respects a relationship card. Those checks belong to a semantic query compiler or to a later session. In practice the two layers complement each other. Semantic validation prevents the YAML from drifting from the database; SQL validation prevents the LLM from drifting from the database at generation time. A query could pass SQL validation and still be nonsense relative to the business definitions—that is acceptable for this milestone because the failure mode is wrong analytics, not a catalog exception.

## Operational notes for contributors

Dialect strings are normalized in one place (`sqlite`, `postgresql`/`postgres`, `duckdb`) so that both sqlglot and the Anthropic system prompt stay aligned. When adding a new warehouse backend, ensure introspection produces `Table` and `Column` names that match what the model is likely to emit; casing is compared case-insensitively for table lookup but column messages preserve the catalog spelling from introspection.

When extending the validator, prefer adding focused unit tests in `tests/unit/test_validator.py` over growing integration tests that call Anthropic. The generator retry tests use a fake `LLMProvider` so CI never spends tokens. If you change how issues are worded, update `tests/unit/test_correction_prompt.py` because the correction path embeds those strings verbatim for the model.

## Comparison to future “explain-back” work

Explain-back, when it lands, will describe the interpretation of the user’s question in business terms before execution. Validation here is silent and mechanical: it never paraphrases the user. The two features answer different questions. Validation answers “did the model stay inside the warehouse catalog for identifiers?” Explain-back will answer “did we understand revenue the same way finance does?” Keeping that separation explicit avoids the trap of asking an LLM to both judge and generate SQL in one breath.

## Closing

Schema-aware validation is deliberately boring engineering on top of a solid parser. That boredom is the point. Interviewers rarely ask for another demo of a chat bubble; they ask how you keep models from hurting production systems. Lumen’s answer in this repository is concrete: parse, scope-check, aggregate issues, optionally retry with grounded hints, and only then execute.

## Walk-through of a failing query

Imagine the model returns `SELECT Profit FROM Customer` against the Chinook sample. Parsing succeeds, so the AST is available and `parsed_sql` is populated. The validator opens the outer `SELECT` scope, finds a single physical source `Customer`, and examines the unqualified column `Profit`. No column with that name exists on `Customer`, so an `unknown_column` issue is appended with the sorted list of real columns attached to the message. There is no `unknown_table` because `Customer` is legitimate.

If the model instead returns `SELECT Country FROM t`, where `t` is an alias for a subquery defined in the `FROM` clause, the validator first validates the inner scope to infer which columns `t` exposes, then checks `Country` in the outer scope against that inferred set. If the inner query used `SELECT *` from a single physical table, expansion is straightforward. If the inner query projected expressions without aliases, those outputs are not advertised under predictable names, and the outer reference may fail validation until the model adds explicit aliases. That behavior nudges generated SQL toward explicitness, which is also what human reviewers tend to ask for.

## Error codes at a glance

The Pydantic models in `src/lumen/validation/models.py` define a small closed set of codes. `syntax_error` means sqlglot could not parse the string or the statement is not a supported read-only select. `unknown_table` means a physical base table in a `FROM` or `JOIN` does not appear in the introspected schema. `unknown_column` means a referenced column is missing on the resolved source, with hints when the source maps cleanly to one physical table. `ambiguous_column` means an unqualified name could come from more than one source in the same scope. The `unqualified_column` literal exists in the type for forward compatibility; today’s validator routes the common cases into `unknown_column` or `ambiguous_column` instead.

Warnings are reserved for future non-fatal findings; current issues that block execution use severity `error`, and `ValidationResult.valid` is false if any error is present.

## Performance expectations

Validation is linear in the size of the AST for typical analytics queries. The Chinook unit suite runs entirely in memory and finishes in well under a second on ordinary hardware. Retries multiply LLM latency, not validation latency, which is why the default retry cap stays small. If you embed Lumen in a service later, you may cache the `Schema` object per connection pool and reuse a single `SQLValidator` instance per request because the validator is stateless aside from holding that schema reference.

## Versioning and sqlglot upgrades

sqlglot releases occasionally refine scope rules. Pinning `sqlglot>=25.0` in `pyproject.toml` documents the minimum tested series; upgrading should always include running `pytest tests/unit/test_validator.py` and inspecting any changed error messages that feed the correction prompt. Because validation messages are user-visible in the CLI, treat them like API surface: change them deliberately and update tests when you do.

## Security posture

Validation reduces the class of attacks where a model accidentally emits destructive DDL, because non-select top-level statements are rejected before execution. It does not replace parameterized query design if you ever accept untrusted literal values, and it does not scan string literals for injection payloads. The read-only posture is a product choice: even valid `SELECT` statements can be expensive, so rate limits and warehouse-side query timeouts remain important in a hosted deployment. Think of validation as a correctness gate for identifiers, not a complete security boundary.

## How this document should evolve

When session six adds semantic checks on top of generated SQL, extend this file with a new section that states explicitly which predicates are semantic versus physical. When benchmarks exist, resist the urge to paste accuracy tables here; link to a benchmark document instead so this page stays about mechanism. The intent is that a candidate or reviewer can read from top to bottom once and understand the guarantee Lumen makes today, the machinery behind it, and the honest edges where the warehouse still has the final word.

## Glossary in one pass

Throughout this repository, “semantic model” refers to the YAML layer that describes entities and metrics for prompting. “Warehouse schema” refers to the introspected catalog of physical tables and columns. “Validation result” is the structured bundle of issues plus the optional canonical SQL string. “Correction round” is any LLM call after the first that uses `build_correction_prompt`. Keeping those terms stable in docs and in code comments reduces the amount of context switching when you move from this markdown file into `src/lumen/validation/validator.py` itself.

## Final note on user-visible output

The CLI prints `--- validation ---` with a yes or no flag, the attempt count, and either canonical SQL on success or a list of issues on failure. That mirrors what a service API would likely return as JSON fields in a later iteration. If you change the headings or keys, update `docs/usage.md` in the same pull request so operators are never surprised.

That is the full story for session five: deterministic validation, optional correction, and honest documentation of the boundary.

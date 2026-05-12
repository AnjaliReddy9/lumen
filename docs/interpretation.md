# Interpretation, explain-back, and ambiguity resolution

This page explains the second stage of Lumen's question pipeline: before any SQL is drafted, the system asks Claude to produce a structured interpretation of the question against the semantic model and the physical warehouse catalog. That design exists for a simple human reason. Large language models are persuasive even when they are wrong. Showing the user a one-line restatement, the entities and metrics the system believes are in play, and any places where the language is genuinely underspecified turns the interaction from a black box into a short negotiation. The user keeps agency; the model keeps the burden of proof.

## The problem explain-back solves

In a traditional NL-to-SQL demo, the user types a sentence and sees a query or an error. There is no middle ground where they can say "that is not what I meant" before the database runs. In production analytics, that gap matters. A wrong filter on geography or time can change revenue numbers without tripping schema validation, because every column referenced might still exist. Explain-back does not catch semantic mistakes on its own. It does make the first failure mode visible and cheap: misalignment between the user's mental model and the system's structured intent shows up in plain language before execution.

Ambiguity resolution complements explain-back. Some questions are legitimately incomplete. "Top customers in California" could rank by invoice totals, by track purchases, or by recency; "California" might mean the US state stored in `Customer.State` or a looser filter on country plus state. Rather than silently picking one path, Lumen lists discrete options with a suggested default, then waits for confirmation in the CLI (or applies defaults when `--auto-resolve` is set for scripts). The structured record of what was chosen travels with the second interpretation call so the SQL generator sees the same constraints the human confirmed.

## Two-step flow: interpret, then generate

By default, `lumen query ask` runs `QueryInterpreter` first. The interpreter uses the Anthropic Messages API with a single client tool named `submit_interpretation`. The tool input is validated with Pydantic's `model_validate_json` after `json.dumps` round-trips the dict returned by the SDK, so the same code path handles strict JSON parsing and retry on validation errors. If the first tool payload fails validation, the error text is appended to the user block and the model gets exactly one more attempt. If both attempts fail, Lumen returns a low-confidence fallback interpretation with a `join_path` ambiguity explaining that structured output was not recovered; the CLI still prints that so the operator knows what happened.

When the interpretation contains no ambiguities, `SQLGenerator.generate_with_interpretation` immediately calls the existing SQL path. The `QueryIntent` object is rendered into the SQL user prompt under `=== INTERPRETED INTENT ===` so the second model call is grounded in the first model's extraction, not only the raw English. The original question remains in the prompt for traceability. When ambiguities are present, SQL generation is deferred until `generate_with_resolutions` runs after the user (or `--auto-resolve`) supplies a map from each ambiguity description to the chosen option string. That map is injected into the interpretation prompt under `=== USER RESOLUTIONS ===` so the second interpretation pass is aware of the contract the user accepted.

## Ambiguity types and Chinook-flavored examples

The `AmbiguityType` literal covers six cases the prompt steers the model toward. A **dimension** ambiguity captures underspecified grouping, for example "by area" when both `Customer.Country` and `Customer.State` could serve. A **value** ambiguity is appropriate when a bare token like "California" could be a literal filter on `Customer.State`, a substring match on `Customer.City`, or even confusion with a column name that resembles a value elsewhere. A **metric** ambiguity arises for questions such as "top customers" without stating whether "top" means highest invoice total, highest line-item count, or most distinct tracks purchased. **time_range** covers phrases like "last quarter" where fiscal versus calendar meaning differs. **missing_filter** is for questions that imply a filter but omit the predicate. **join_path** is reserved for cases where more than one join graph could answer the question; it is also used for the structured-output fallback when JSON parsing fails twice.

The bundled Chinook semantic fixture is small on purpose: a few entities, two metrics, and two relationships. That keeps the interpreter prompt short enough to scan in a code review while still exercising joins between `Customer`, `Invoice`, `InvoiceLine`, and `Track`. When you run `lumen query ask "Top customers in California"` against that fixture, you should expect the model to surface at least one ambiguity around geography or ranking unless you use `--auto-resolve`, in which case the CLI prints which default strings were applied before SQL generation proceeds.

## Trade-offs: latency, cost, and the escape hatch

Interpretation is an additional round trip to Claude before SQL generation and validation. Latency roughly doubles for interactive questions, and token usage rises because the semantic and physical schema blocks appear in both prompts. For batch benchmarks where the research question is "how good is raw SQL generation without steering," pass `--no-interpret` to restore the session-4 fast path. For quick inspection of what the interpreter would do without paying for SQL tokens, use `--explain-only`. Those flags are documented alongside examples in `docs/usage.md`.

## Interactive CLI transcript (illustrative)

The following transcript is representative of the ASCII-only formatting the CLI emits today. Option letters are generated from the ambiguity's `options` list; pressing Enter accepts `suggested_default` when present, otherwise the first option.

```
$ lumen query ask "Top 10 customers by spending in California" \
    --semantic-dir tests/fixtures/chinook_semantic \
    --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite

--- interpretation ---
I understand this as: Rank the top 10 customers by total invoice spend, focusing on
people located in California.
Entities: customer, invoice
Metrics: total_revenue
Dimensions: ...
Time grain: (none)
Filters: (none)
Sort: (none)
Limit: 10
Interpreter confidence: medium

--- ambiguities ---
1. "California" may refer to Customer.State = 'CA', full name 'California', or a broader
   US filter on Customer.Country.
   a) Customer.State equals the literal 'California'
   b) Customer.State equals 'CA'
   c) Customer.Country = 'USA' and Customer.State is not null
   Default: a
Choose [a/b/c, or Enter for default]: b

--- generated sql ---
SELECT ...
--- validation ---
valid: yes
attempts: 1
...
--- result ---
```

The exact wording varies with the model, but the section headers and the resolution loop stay stable so session nine's Angular client can mirror the same structure.

## Relationship to schema validation

Interpretation is not a substitute for sqlglot validation. Interpretation reasons about intent and language; validation reasons about identifiers in the final SQL string. Both can run in one CLI invocation: after interpretation and any ambiguity resolution, the SQL generator still passes through the session-five validator unless `--skip-validation` is set. That ordering is deliberate. There is little value in validating SQL that should never have been generated because the user never confirmed the metric.

## How this file should evolve

When session seven adds offline evaluation, link to benchmark methodology here instead of duplicating tables. When session nine ships the web UI, add a short subsection describing which fields from `Interpretation` map to which components on screen. Until then, treat this document as the contract for the JSON shape behind `submit_interpretation` and as the narrative answer to "how does Lumen handle ambiguous analytics questions without hiding assumptions?"

## Pydantic models and the Angular contract

The `QueryIntent`, `AmbiguityIssue`, and `Interpretation` types in `src/lumen/interpretation/models.py` are intentionally boring data containers. They exist so the CLI, future HTTP API, and Angular client can share one schema. `FilterClause` keeps operator and value as strings because the interpreter is not a type checker; sqlglot validation later enforces catalog existence, not semantic types. `SortClause` and `limit` mirror what most BI tools expose in a simple query builder. When the frontend arrives, serialize these models with `model_dump` or equivalent and render them in a summary card; do not fork parallel DTOs unless there is a compelling versioning reason.

## Failure handling and operator trust

When both interpretation attempts fail validation, the fallback interpretation still carries the original `question` string on the intent object so logs remain searchable. The synthetic ambiguity explains that structured JSON was not recovered; it is not a database error and not a user insult. Operators can retry with a narrower question or escalate to `--no-interpret` if they suspect the tool schema and the model have drifted. Keeping that path explicit avoids silent degradation into "best effort SQL" without any paper trail.

## Comparison to session five retries

Session five retries malformed or schema-invalid SQL using natural-language correction prompts. Session six retries only the interpretation JSON using Pydantic validation errors as machine-readable feedback. Those loops are intentionally separate. Mixing them would blur responsibility: SQL retries assume a parseable string already exists, while interpretation retries assume the model never emitted executable SQL yet. Maintaining two small retry policies is easier to reason about than one mega-loop with entangled exit codes.

## Security and data handling

The interpreter prompt includes the same warehouse schema excerpt as SQL generation. It should therefore be treated with the same care as any other prompt that might contain column names or sample-sensitive metadata if you extend introspection later. Interpretations are not cached to disk in this milestone; each CLI invocation is stateless aside from whatever the Anthropic account retains under its own retention policy. If you embed Lumen in a multi-tenant service, redact customer-specific literals from logs before storing interpretation JSON.

## Closing

Explain-back and ambiguity resolution are product-shaped features implemented with CLI primitives so they can ship before the frontend. They cost an extra API call and a few seconds of patience, but they buy something precious in analytics tooling: a defensible story about where the model's assumptions live and how a human overrode them. That story is what this file is for.

## Testing strategy for contributors

Unit tests in `tests/unit/test_interpreter.py` drive `QueryInterpreter` with a fake `call_tool_use` implementation so CI never spends Anthropic credits. They cover happy path parsing, a validation failure followed by success, malformed payloads, and the double-failure fallback. Prompt tests assert that the question, dialect, semantic block, and schema block appear in the user message and that the system message references the tool contract. Generator tests mock `QueryInterpreter` to isolate SQL generation behavior when ambiguities block the first pass and to assert that `generate_with_resolutions` forwards the resolutions dict into `interpret`. When you change prompt prose, update those substring expectations deliberately rather than loosening them to empty checks.

## Roadmap touchpoints

Session seven will likely add offline datasets and accuracy metrics; interpretation should remain toggleable so benchmarks can isolate SQL quality. Session nine's Angular UI should reuse the section headers from the CLI for cognitive continuity. If you add streaming responses later, keep the structured tool call as a discrete completion boundary so partial JSON never reaches Pydantic. Those constraints are not hypothetical; they are the lessons from shipping deterministic validation in session five and structured interpretation here in session six.

## Glossary

**Explain-back** means printing the interpreted intent before SQL runs. **Ambiguity** means the model listed more than one defensible reading. **Resolution** means the user picked an option string that is echoed back into the second interpretation prompt. **Fast path** means `--no-interpret`, which skips all of the above. Keeping vocabulary tight in issues and pull requests prevents the team from talking past each other when debugging CLI transcripts attached to bug reports.

## Chinook mental model for reviewers

If you are new to the sample database, remember that revenue rolls up through `Invoice` and `InvoiceLine` into `Track`, while customers live on `Customer` with geography columns on that table. The semantic fixture exposes `total_revenue` and `track_count` metrics so interpretation prompts can anchor on names a human analyst would recognize. When you read a transcript where the model hesitates between state and country, check whether the semantic YAML actually lists both dimensions; the interpreter is only as precise as the entity definitions you ship. Improving the YAML often reduces ambiguity count faster than tweaking prose in the interpreter system prompt.

## Appendix: file map

`src/lumen/interpretation/models.py` holds the Pydantic types. `src/lumen/interpretation/prompt.py` builds the interpreter system and user prompts. `src/lumen/interpretation/tool_spec.py` defines the Anthropic tool schema as nested JSON Schema objects hand-authored for readability. `src/lumen/interpretation/interpreter.py` implements `QueryInterpreter` with the retry loop. `src/lumen/generation/generator.py` exposes `generate_with_interpretation` and `generate_with_resolutions`, while `src/lumen/generation/prompt.py` threads optional `QueryIntent` data into SQL prompts. `src/lumen/cli.py` renders ASCII section headers and drives `click.prompt` loops. Tests mirror that layout under `tests/unit/test_interpreter*.py` and `tests/unit/test_generator_with_*`.

That appendix is the quickest orientation for a reviewer scanning the diff for session six. Everything else in this document is motivation and behavior; the file map is where the code actually lives.

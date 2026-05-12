# Lumen benchmarks

This document describes the three benchmark tracks shipped with Lumen, how accuracy is scored, and how to reproduce runs locally.

## Overview

| Benchmark | Source | Purpose |
|-----------|--------|---------|
| **Spider** | User-provided `train_spider.json` (or dev split) | Classic text-to-SQL; structural SQL match vs gold query when row labels are unavailable. |
| **BIRD** | User-provided BIRD-format JSON | Harder questions with evidence text; same scoring pattern as Spider. |
| **NYC Open Data** | Curated YAML in `tests/fixtures/nyc_benchmark/cases.yaml` | Domain realism for a portfolio narrative; gold **SQL patterns** (substring or structural match) because upstream data changes daily. |

A small **Chinook** YAML (`tests/fixtures/eval_chinook/cases.yaml`) is used for smoke tests and `lumen eval run --benchmark chinook`.

## Downloading Spider and BIRD

Lumen does not vendor benchmark corpora.

- **Spider:** follow the instructions at [https://yale-lily.github.io/spider](https://yale-lily.github.io/spider) and point `--spider-path` at `train_spider.json` (or your chosen split).
- **BIRD:** follow [https://bird-bench.github.io/](https://bird-bench.github.io/) and pass `--bird-path` to the JSON file you exported.

Both loaders accept optional `--spider-db-id` / `--bird-db-id` filters so you can keep a **single SQLite file** attached through DuckDB for the duration of an eval run.

## NYC Open Data benchmark

### Construction

- **Cases:** `tests/fixtures/nyc_benchmark/cases.yaml` (40+ hand-written questions across 311, permits, schools, restaurants, crashes, trees, Citibike, air quality, housing, film permits, and catalog tables).
- **Warehouse:** `benchmarks/datasets/nyc_open_data/warehouse.duckdb` (reproducible local tables with synthetic rows).
- **Semantic layer:** `benchmarks/datasets/nyc_open_data/semantic/` — 52 entities / metrics aligned to physical tables (the “50+ tables” resume claim is realized as 52 physical tables plus curated questions).
- **Build script:** `scripts/download_nyc_data.py` (offline by default; `--live` attempts a tiny Socrata CSV pull).

Run the script from the repo root:

```bash
python scripts/download_nyc_data.py --tables 52
```

The resulting DuckDB file is ~28MB (under the 100MB commit threshold) and is safe to commit for CI smoke tests.

## Methodology

### Row equality (Chinook smoke, optional cases)

When `expected_rows` is present, Lumen compares **multisets** of rows:

- Column order inside a row does not matter.
- Row order in the result set does not matter.
- Values are stringified for comparison (numeric type differences between engines can still surface as mismatches—prefer explicit `CAST` in gold SQL when needed).

### Structural SQL (Spider / BIRD / NYC pattern mode)

When only `expected_sql` exists:

- **Spider / BIRD:** `sqlglot` parses both statements and compares normalized SQL strings. This is **approximate** (aliases, redundant parentheses, or logically equivalent rewrites may differ).
- **NYC:** a case passes if the generated SQL is structurally equivalent **or** contains the gold substring (hand-tuned patterns for `COUNT`, `AVG`, etc.).

### Metrics on `EvalRun.summary`

- **execution_accuracy:** fraction of cases with a defined ground truth where the check above succeeded.
- **validation_pass_rate:** fraction where schema-aware validation passed.
- **generation_success_rate:** fraction where SQL was produced without a top-level runner error.
- **avg_latency_ms / total_cost_usd:** aggregated per-case wall clock and Anthropic usage-derived estimates.

## Running evals

```bash
export ANTHROPIC_API_KEY=...
lumen eval run --benchmark chinook --sample 10 \
  --semantic-dir tests/fixtures/chinook_semantic \
  --warehouse duckdb --path /tmp/chinook.sqlite --dialect sqlite \
  --output benchmarks/runs/chinook-10.json
```

For deterministic CI-style smoke (no API key):

```bash
LUMEN_FAKE_LLM=1 lumen eval run --benchmark chinook --fake-llm --no-interpret ...
```

Concurrency defaults to four in-flight worker threads; reduce `--max-concurrency` if Anthropic returns 429s.

## Cost expectations (Claude Sonnet 4.5 list pricing)

Pricing is centralized in `src/lumen/llm/pricing.py` (Sonnet ≈ **$3 / MTok input**, **$15 / MTok output** as of May 2026). Exact spend depends on prompt size and retries, but order-of-magnitude guidance:

| Track | Subset size | Rough order of magnitude |
|-------|-------------|---------------------------|
| Spider | 100 cases | single-digit dollars if questions are short and succeed in one attempt |
| BIRD | 100 cases | higher (longer prompts + harder SQL) |
| NYC | 40+ cases | similar to Spider subset (smaller N, but wide schema context) |

## Leaderboard (manual)

Fill this table after you capture real runs (model name, commit SHA, benchmark, summary stats):

| Date | Model | Benchmark | Exec accuracy | Validation | Cost (USD) | Notes |
|------|-------|-----------|-----------------|------------|------------|-------|
| | | | | | | |

## Caveats

- DuckDB attaches SQLite under the `lumen_sqlite` catalog; eval gold SQL for Chinook uses the `lumen_sqlite.*` qualifiers so execution matches the CLI default warehouse mode.
- No prompt caching yet—cost estimates assume full-price tokens.
- Background workers (Celery/Redis) are intentionally out of scope; long evals should be launched from the CLI or a notebook.

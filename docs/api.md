# Lumen REST API

FastAPI application (`src/lumen/api/app.py`) exposing the same semantic + generation stack as the CLI. Configuration is **only** via environment variables (and optional `.env`); there are no hard-coded warehouse paths in route handlers.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | yes* | Claude credentials for live `/query` and `/interpret`. |
| `LUMEN_SEMANTIC_DIR` | yes | Directory with `entities/`, `metrics/`, `relationships.yaml`. |
| `LUMEN_WAREHOUSE_PATH` | yes | DuckDB file path **or** SQLite file path (DuckDB attach) **or** Postgres URL when `LUMEN_WAREHOUSE_TYPE=postgres`. |
| `LUMEN_WAREHOUSE_TYPE` | no | `duckdb` (default) or `postgres`. |
| `LUMEN_DIALECT` | no | SQL dialect for prompts / validation (default `sqlite`). |
| `LUMEN_ANTHROPIC_MODEL` | no | Model id passed to Anthropic (default `claude-sonnet-4-5`). |
| `LUMEN_CORS_ORIGINS` | no | Comma-separated list; defaults to Angular/localhost dev ports. |
| `LUMEN_LOG_LEVEL` | no | Python logging level (default `info`). |
| `LUMEN_EVAL_RUNS_DIR` | no | Directory containing `*.json` eval exports (default `benchmarks/runs`). |
| `ENABLE_EVAL_API` | no | When `true`, `POST /eval/runs` stops returning 404—but the handler is still a **501** stub (use the CLI for real runs). |

\*Integration tests inject a dummy key; production calls require a real key.

Copy `.env.example` to `.env` and export overrides as needed.

## Endpoints

### `GET /health`

```bash
curl -s http://localhost:8000/health
```

Response:

```json
{"status": "ok", "version": "0.0.1"}
```

### `GET /ready`

Loads the semantic model, introspects the warehouse, and validates the semantic definitions.

```bash
curl -s http://localhost:8000/ready
```

Example success payload:

```json
{"status": "ok", "warehouse_tables": 11, "semantic_entities": 4}
```

### `GET /schema` / `GET /semantic`

Return the introspected `Schema` and loaded `SemanticModel` JSON.

```bash
curl -s http://localhost:8000/schema | head
curl -s http://localhost:8000/semantic | head
```

### `POST /interpret`

```bash
curl -s -X POST http://localhost:8000/interpret \
  -H 'Content-Type: application/json' \
  -d '{"question": "How many tracks are in each genre?"}'
```

Returns the `Interpretation` Pydantic model (intent summary, entities, ambiguities, etc.).

### `POST /query`

```bash
curl -s -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "How many tracks per genre?", "skip_interpretation": false}'
```

Body fields:

- `question` (required)
- `resolutions` (optional map for ambiguity follow-ups)
- `skip_interpretation` (bool, default `false`)
- `skip_validation` (bool, default `false`)

Response includes `interpretation`, `generated_sql`, `validation`, `rows`, `row_count`, `latency_ms`, and `cost_usd`.

### `POST /query/stream`

Server-Sent Events with phases `interpreting`, `generated_sql`, `validating`, `executing`, and `done` (payload mirrors `/query` JSON). Example:

```bash
curl -N -X POST http://localhost:8000/query/stream \
  -H 'Content-Type: application/json' \
  -d '{"question": "How many genres?", "skip_interpretation": true}'
```

### `GET /eval/runs` / `GET /eval/runs/{run_id}`

Lists JSON exports found in `LUMEN_EVAL_RUNS_DIR`, or returns a single `EvalRun`.

```bash
curl -s http://localhost:8000/eval/runs
```

### `POST /eval/runs`

Returns **404** unless `ENABLE_EVAL_API=true`, then **501** with guidance to use the CLI. This keeps accidental long-running jobs off the HTTP surface.

## Running locally

```bash
uv pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...
export LUMEN_SEMANTIC_DIR=tests/fixtures/chinook_semantic
export LUMEN_WAREHOUSE_PATH=/tmp/chinook.sqlite
lumen api serve --reload
```

## Docker

```bash
docker compose up --build
```

Compose mounts your semantic directory and warehouse file read-only into `/data/...` inside the container—adjust `LUMEN_SEMANTIC_HOST_DIR` / `LUMEN_WAREHOUSE_HOST_PATH` in your shell to match local paths.

## Production considerations (out of scope)

- **Authentication / authorization:** not implemented; bind to localhost or place behind a trusted reverse proxy.
- **Rate limiting:** not implemented; add at the edge if you expose the service.
- **Metrics & tracing:** no Prometheus or OpenTelemetry hooks yet—add if you need SLO dashboards.

These items are intentionally deferred so the repository stays focused on the research narrative (semantic layer + SQL quality).

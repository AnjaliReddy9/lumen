# Lumen

> Natural language analytics that runs against real warehouses, not toy schemas.

## What it does

Lumen lets non-technical users query a data warehouse in English and get a chart back. Runs against schemas with 50+ tables — the size where most NL→SQL demos fall apart.

[Demo video — 60 seconds](#)

## What's interesting about it

- **Real semantic layer.** Entity definitions, metric definitions, and allowed joins live in YAML. The model doesn't get to invent columns or invent joins.
- **Ambiguity resolution.** "California" — column value, region code, or a state column? Lumen asks before guessing.
- **Schema-aware validation.** Every generated query is parsed and validated against the schema before execution. Hallucinated columns never reach the database.
- **Explain-back.** Lumen shows its interpretation of the question before running anything.

## Stack

Python · FastAPI · Postgres · DuckDB · Claude / GPT-4 · Angular · ngx-charts

## Running locally

```bash
git clone https://github.com/AnjaliEga/lumen
cd lumen
cp .env.example .env
docker-compose up
```

Open `localhost:3000` and ask a question against the bundled NYC Open Data sample.

## Benchmarks

Tested on Spider, BIRD, and a 60-table public dataset.

| System         | Spider Exec Acc | BIRD Exec Acc | NYC Open Data |
|----------------|-----------------|---------------|---------------|
| GPT-4 baseline | XX.X%           | XX.X%         | XX.X%         |
| Vanna AI       | XX.X%           | XX.X%         | XX.X%         |
| **Lumen**      | **XX.X%**       | **XX.X%**     | **XX.X%**     |

Methodology: [BENCHMARKS.md](./BENCHMARKS.md)

## Writing

- [NL→SQL on real schemas: notes from a 60-table benchmark](#)

## License

MIT

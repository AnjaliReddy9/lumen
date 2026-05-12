from __future__ import annotations

from pathlib import Path

import yaml

from lumen.eval.models import EvalCase


def load_nyc_open_data_cases(path: Path | None = None) -> list[EvalCase]:
    """Load curated NYC Open Data benchmark cases."""
    p = path or (
        Path(__file__).resolve().parents[4]
        / "tests"
        / "fixtures"
        / "nyc_benchmark"
        / "cases.yaml"
    )
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"invalid NYC benchmark YAML: {p}")
    raw_cases = data["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("cases must be a list")
    out: list[EvalCase] = []
    for i, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            raise ValueError(f"case {i} is not a mapping")
        tags = item.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        out.append(
            EvalCase(
                case_id=str(item["case_id"]),
                question=str(item["question"]),
                expected_sql=str(item["expected_sql"]) if item.get("expected_sql") else None,
                expected_rows=None,
                database=str(item.get("database", "nyc_open_data")),
                dialect=str(item.get("dialect", "duckdb")),
                difficulty=item.get("difficulty"),
                tags=[str(t) for t in tags],
            )
        )
    return out

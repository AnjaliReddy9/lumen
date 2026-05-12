from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from lumen.eval.models import EvalCase


def load_chinook_eval_cases(path: Path | None = None) -> list[EvalCase]:
    """Load built-in Chinook smoke-test cases (YAML)."""
    p = path or (
        Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "eval_chinook" / "cases.yaml"
    )
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "cases" not in data:
        raise ValueError(f"invalid Chinook eval YAML: {p}")
    raw_cases = data["cases"]
    if not isinstance(raw_cases, list):
        raise ValueError("cases must be a list")
    out: list[EvalCase] = []
    for i, item in enumerate(raw_cases):
        if not isinstance(item, dict):
            raise ValueError(f"case {i} is not a mapping")
        er = item.get("expected_rows")
        expected_rows: list[dict[str, Any]] | None = None
        if isinstance(er, list):
            expected_rows = [dict(r) for r in er if isinstance(r, dict)]
        out.append(
            EvalCase(
                case_id=str(item["case_id"]),
                question=str(item["question"]),
                expected_sql=item.get("expected_sql"),
                expected_rows=expected_rows,
                database=str(item.get("database", "chinook")),
                dialect=str(item.get("dialect", "sqlite")),
                difficulty=item.get("difficulty"),
                tags=list(item.get("tags", [])),
            )
        )
    return out

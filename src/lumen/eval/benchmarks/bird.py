from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal, cast

from lumen.eval.models import EvalCase

Difficulty = Literal["easy", "medium", "hard", "extra"]


def load_bird_subset(
    path: Path,
    n_cases: int = 100,
    seed: int = 42,
    *,
    db_id: str | None = None,
) -> list[EvalCase]:
    """Load a deterministic subset from a BIRD-format JSON file (train/dev).

    Each record is expected to expose question/SQL and a database identifier
    (``db_id`` or ``database`` depending on the export).
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"expected JSON array in {path}")
    rows: list[dict[str, object]] = [r for r in raw if isinstance(r, dict)]
    if db_id is not None:
        rows = [r for r in rows if str(r.get("db_id", r.get("database", ""))) == db_id]
    if not rows:
        raise ValueError("no BIRD rows after filtering; check path and db_id")

    rng = random.Random(seed)
    rng.shuffle(rows)
    picked = rows[:n_cases]

    out: list[EvalCase] = []
    for i, row in enumerate(picked):
        q = str(row.get("question", "")).strip()
        sql = str(row.get("SQL", row.get("query", ""))).strip()
        db = str(row.get("db_id", row.get("database", "unknown")))
        diff_raw = row.get("difficulty")
        difficulty: Difficulty | None = None
        if isinstance(diff_raw, str) and diff_raw in ("simple", "moderate", "challenging"):
            mapping: dict[str, Difficulty] = {
                "simple": "easy",
                "moderate": "medium",
                "challenging": "hard",
            }
            difficulty = mapping[diff_raw]
        elif isinstance(diff_raw, str) and diff_raw in ("easy", "medium", "hard", "extra"):
            difficulty = cast(Difficulty, diff_raw)
        out.append(
            EvalCase(
                case_id=f"bird_{db}_{i:04d}",
                question=q,
                expected_sql=sql or None,
                expected_rows=None,
                database=db,
                dialect="sqlite",
                difficulty=difficulty,
                tags=["bird"],
            )
        )
    return out

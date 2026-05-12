from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Literal, cast

from lumen.eval.models import EvalCase

Difficulty = Literal["easy", "medium", "hard", "extra"]


def load_spider_subset(
    path: Path,
    n_cases: int = 100,
    seed: int = 42,
    *,
    db_id: str | None = None,
) -> list[EvalCase]:
    """Load a deterministic random subset from Spider's JSON train/dev file.

    ``path`` should point to ``train_spider.json`` (or dev) from the Spider release.
    When ``db_id`` is set, only cases for that SQLite database are kept so a single
    warehouse file can be used for the whole eval run.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"expected JSON array in {path}")
    rows: list[dict[str, object]] = [r for r in raw if isinstance(r, dict)]
    if db_id is not None:
        rows = [r for r in rows if str(r.get("db_id", "")) == db_id]
    if not rows:
        raise ValueError("no Spider rows after filtering; check path and db_id")

    rng = random.Random(seed)
    rng.shuffle(rows)
    picked = rows[:n_cases]

    out: list[EvalCase] = []
    for i, row in enumerate(picked):
        q = str(row.get("question", "")).strip()
        sql = str(row.get("query", "")).strip()
        db = str(row.get("db_id", "unknown"))
        diff_raw = row.get("hardness") or row.get("difficulty")
        difficulty: Difficulty | None = None
        if isinstance(diff_raw, str) and diff_raw in ("easy", "medium", "hard", "extra"):
            difficulty = cast(Difficulty, diff_raw)
        out.append(
            EvalCase(
                case_id=f"spider_{db}_{i:04d}",
                question=q,
                expected_sql=sql or None,
                expected_rows=None,
                database=db,
                dialect="sqlite",
                difficulty=difficulty,
                tags=["spider"],
            )
        )
    return out

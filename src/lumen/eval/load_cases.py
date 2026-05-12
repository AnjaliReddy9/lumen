from __future__ import annotations

from pathlib import Path

from lumen.eval.benchmarks.bird import load_bird_subset
from lumen.eval.benchmarks.chinook import load_chinook_eval_cases
from lumen.eval.benchmarks.nyc_open_data import load_nyc_open_data_cases
from lumen.eval.benchmarks.spider import load_spider_subset
from lumen.eval.models import EvalCase


def load_cases_for_benchmark(
    benchmark: str,
    *,
    spider_path: Path | None = None,
    bird_path: Path | None = None,
    spider_db_id: str | None = None,
    bird_db_id: str | None = None,
    n_cases: int = 100,
    seed: int = 42,
    chinook_cases_path: Path | None = None,
    nyc_cases_path: Path | None = None,
) -> list[EvalCase]:
    b = benchmark.casefold()
    if b == "chinook":
        return load_chinook_eval_cases(chinook_cases_path)
    if b == "spider":
        if spider_path is None:
            raise ValueError("--spider-path is required for spider benchmark")
        return load_spider_subset(spider_path, n_cases=n_cases, seed=seed, db_id=spider_db_id)
    if b == "bird":
        if bird_path is None:
            raise ValueError("--bird-path is required for bird benchmark")
        return load_bird_subset(bird_path, n_cases=n_cases, seed=seed, db_id=bird_db_id)
    if b == "nyc_open_data":
        return load_nyc_open_data_cases(nyc_cases_path)
    raise ValueError(f"unknown benchmark: {benchmark!r}")

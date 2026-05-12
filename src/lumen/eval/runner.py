from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lumen.eval.models import EvalCase, EvalConfig, EvalResult, EvalRun, EvalSummary
from lumen.eval.sql_compare import sql_matches_expected_pattern, structural_sql_equivalent
from lumen.generation.generator import SQLGenerator
from lumen.generation.runner import run_generated_sql
from lumen.interpretation.models import Interpretation
from lumen.llm.anthropic_provider import AnthropicProvider
from lumen.semantic.models import SemanticModel
from lumen.warehouse.base import Warehouse
from lumen.warehouse.schema import Schema


def _rows_fingerprint(rows: list[dict[str, Any]]) -> set[tuple[tuple[str, str], ...]]:
    """Order-insensitive multiset of rows (column names sorted per row)."""
    out: set[tuple[tuple[str, str], ...]] = set()
    for row in rows:
        items: list[tuple[str, str]] = []
        for k in sorted(row.keys()):
            v = row[k]
            if v is None:
                sv = "__NULL__"
            elif isinstance(v, (dict, list)):
                sv = json.dumps(v, sort_keys=True, default=str)
            else:
                sv = str(v)
            items.append((k, sv))
        out.add(tuple(items))
    return out


def rows_match(expected: list[dict[str, Any]], actual: list[dict[str, Any]] | None) -> bool:
    if actual is None:
        return False
    return _rows_fingerprint(expected) == _rows_fingerprint(actual)


def _empty_summary() -> EvalSummary:
    return EvalSummary(
        execution_accuracy=0.0,
        validation_pass_rate=0.0,
        generation_success_rate=0.0,
        avg_latency_ms=0,
        total_cost_usd=0.0,
        by_difficulty=None,
    )


def build_eval_summary(results: list[EvalResult], *, nested: bool = False) -> EvalSummary:
    if not results:
        return _empty_summary()

    n = len(results)
    val_ok = sum(1 for r in results if r.validation_valid) / n
    gen_ok = sum(1 for r in results if r.generated_sql and r.error is None) / n
    latencies = [r.latency_ms for r in results]
    avg_lat = int(sum(latencies) / n) if latencies else 0
    total_cost = sum(r.cost_usd for r in results)

    with_gt = [r for r in results if r.execution_accuracy is not None]
    exec_acc = (
        sum(1 for r in with_gt if r.execution_accuracy) / len(with_gt) if with_gt else 0.0
    )

    nested_out: dict[str, EvalSummary] | None = None
    if not nested:
        by_diff: dict[str, list[EvalResult]] = {}
        for r in results:
            key = r.difficulty or "unspecified"
            by_diff.setdefault(key, []).append(r)

        if len(by_diff) > 1 or (len(by_diff) == 1 and next(iter(by_diff)) != "unspecified"):
            nested_out = {}
            for diff_key, group in by_diff.items():
                inner = build_eval_summary(group, nested=True)
                nested_out[diff_key] = inner.model_copy(update={"by_difficulty": None})

    return EvalSummary(
        execution_accuracy=exec_acc,
        validation_pass_rate=val_ok,
        generation_success_rate=gen_ok,
        avg_latency_ms=avg_lat,
        total_cost_usd=round(total_cost, 6),
        by_difficulty=nested_out,
    )


def _compute_execution_accuracy(
    case: EvalCase,
    executed_rows: list[dict[str, Any]] | None,
    generated_sql: str | None,
    dialect: str,
    benchmark: str,
) -> bool | None:
    if case.expected_rows is not None:
        return rows_match(case.expected_rows, executed_rows)
    if case.expected_sql and generated_sql:
        if benchmark == "nyc_open_data":
            return sql_matches_expected_pattern(generated_sql, case.expected_sql, dialect)
        return structural_sql_equivalent(generated_sql, case.expected_sql, dialect)
    return None


def _interpretation_summary(interp: Interpretation | None) -> str | None:
    if interp is None:
        return None
    s = interp.intent.intent_summary.strip()
    return s or None


class EvalRunner:
    """Runs eval cases against a generator and warehouse (single warehouse instance)."""

    def __init__(self, generator: SQLGenerator, warehouse: Warehouse) -> None:
        self._generator = generator
        self._warehouse = warehouse

    def run(
        self,
        cases: list[EvalCase],
        config: EvalConfig,
        *,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        benchmark: str,
        model_name: str,
        run_id: str | None = None,
        checkpoint_dir: Path | None = None,
    ) -> EvalRun:
        rid = run_id or str(uuid.uuid4())
        started = datetime.now(UTC)
        cases_in = cases[:]
        if config.sample_size is not None:
            cases_in = cases_in[: config.sample_size]

        runs_dir = checkpoint_dir or Path("benchmarks/runs")
        runs_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = runs_dir / f"{rid}.jsonl"

        results: list[EvalResult] = []
        cost_lock = threading.Lock()
        state: dict[str, Any] = {"total_cost": 0.0, "abort": False}

        def flush_checkpoint(pending: list[EvalResult]) -> None:
            if not pending:
                return
            with checkpoint_path.open("a", encoding="utf-8") as fh:
                for r in pending:
                    fh.write(r.model_dump_json() + "\n")

        gen = self._generator
        wh = self._warehouse
        max_workers = max(1, config.max_concurrency)

        def sync_eval_one(case: EvalCase) -> EvalResult:
            with cost_lock:
                if state["abort"]:
                    return EvalResult(
                        case_id=case.case_id,
                        question=case.question,
                        difficulty=case.difficulty,
                        error="skipped: eval aborted (cost cap)",
                    )

            t0 = time.perf_counter()
            interp_summary: str | None = None
            interp_cost = 0.0
            generated = None
            err: str | None = None

            try:
                provider = gen.provider
                if isinstance(provider, AnthropicProvider):
                    provider.take_pending_cost_usd()

                if config.use_interpretation:
                    try:
                        interp, maybe_gen = gen.generate_with_interpretation(
                            case.question,
                            semantic_model,
                            schema,
                            dialect,
                            skip_validation=config.skip_validation,
                        )
                        interp_summary = _interpretation_summary(interp)
                        if isinstance(provider, AnthropicProvider):
                            interp_cost = provider.take_pending_cost_usd()
                        if maybe_gen is None:
                            generated = None
                            err = "ambiguous interpretation (unresolved)"
                        else:
                            generated = maybe_gen
                    except Exception as exc:
                        err = str(exc)
                        generated = None
                else:
                    generated = gen.generate(
                        case.question,
                        semantic_model,
                        schema,
                        dialect,
                        skip_validation=config.skip_validation,
                    )
            except Exception as exc:
                err = str(exc)

            latency_ms = int((time.perf_counter() - t0) * 1000)

            sql_cost = float(generated.cost_usd) if generated is not None else 0.0
            case_cost = round(interp_cost + sql_cost, 6)

            with cost_lock:
                state["total_cost"] += case_cost
                if state["total_cost"] > config.max_cost_usd:
                    state["abort"] = True

            gen_sql = generated.sql if generated else None
            val_valid = bool(generated and generated.validation.valid)
            val_issues = list(generated.validation.issues) if generated else []
            attempts = generated.attempts if generated else 0

            executed: list[dict[str, Any]] | None = None
            exec_err: str | None = None
            if generated and val_valid and gen_sql:
                try:
                    qr = run_generated_sql(generated, wh)
                    if qr.error:
                        exec_err = qr.error
                    else:
                        executed = qr.rows
                except Exception as exc:
                    exec_err = str(exc)

            if err and exec_err:
                err = f"{err}; exec: {exec_err}"
            elif exec_err and not err:
                err = exec_err

            exec_acc = _compute_execution_accuracy(case, executed, gen_sql, dialect, benchmark)

            return EvalResult(
                case_id=case.case_id,
                question=case.question,
                difficulty=case.difficulty,
                generated_sql=gen_sql,
                executed_rows=executed,
                validation_valid=val_valid,
                validation_issues=val_issues,
                interpretation_summary=interp_summary,
                attempts=attempts,
                latency_ms=latency_ms,
                cost_usd=case_cost,
                execution_accuracy=exec_acc,
                error=err,
            )

        async def run_pool() -> list[EvalResult]:
            sem = asyncio.Semaphore(config.max_concurrency)
            flush_lock = asyncio.Lock()
            loop = asyncio.get_running_loop()
            pending_flush: list[EvalResult] = []

            with ThreadPoolExecutor(max_workers=max_workers) as pool:

                async def guarded(c: EvalCase) -> EvalResult:
                    async with sem:
                        res = await loop.run_in_executor(pool, sync_eval_one, c)
                        async with flush_lock:
                            pending_flush.append(res)
                            if len(pending_flush) >= 10:
                                flush_checkpoint(pending_flush)
                                pending_flush.clear()
                        return res

                out = await asyncio.gather(*(guarded(c) for c in cases_in))
            async with flush_lock:
                flush_checkpoint(pending_flush)
                pending_flush.clear()
            return list(out)

        results = asyncio.run(run_pool())

        completed_at = datetime.now(UTC)
        summary = build_eval_summary(results)
        return EvalRun(
            run_id=rid,
            benchmark=benchmark,
            model=model_name,
            config=config.model_dump(),
            started_at=started,
            completed_at=completed_at,
            cases_total=len(cases_in),
            cases_completed=len(results),
            results=results,
            summary=summary,
        )

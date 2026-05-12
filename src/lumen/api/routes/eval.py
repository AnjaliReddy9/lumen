from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lumen.api.config import Settings
from lumen.api.deps import get_settings
from lumen.eval.models import EvalRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRunTrigger(BaseModel):
    benchmark: Literal["chinook", "spider", "bird", "nyc_open_data"] = "chinook"
    sample: int | None = 5


@router.get("/runs")
def list_eval_runs(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, str | int]]:
    d = settings.eval_runs_dir
    if not d.is_dir():
        return []
    out: list[dict[str, str | int]] = []
    for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            run = EvalRun.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append(
            {
                "run_id": run.run_id,
                "benchmark": run.benchmark,
                "cases_completed": run.cases_completed,
                "path": str(p),
            }
        )
    return out


@router.get("/runs/{run_id}")
def get_eval_run(
    run_id: str, settings: Annotated[Settings, Depends(get_settings)]
) -> EvalRun:
    for p in settings.eval_runs_dir.glob("*.json"):
        try:
            run = EvalRun.model_validate_json(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("bad eval json %s: %s", p, exc)
            continue
        if run.run_id == run_id or p.stem == run_id:
            return run
    raise HTTPException(status_code=404, detail="run not found")


@router.post("/runs")
def trigger_eval_run(
    body: EvalRunTrigger,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    if not settings.enable_eval_api:
        raise HTTPException(status_code=404, detail="eval API disabled")
    raise HTTPException(
        status_code=501,
        detail="Triggering eval runs from the API is not implemented; use `lumen eval run`.",
    )

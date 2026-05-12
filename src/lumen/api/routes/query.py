from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lumen.api.config import Settings
from lumen.api.deps import (
    get_generator,
    get_schema,
    get_semantic_model,
    get_settings,
    get_warehouse,
)
from lumen.generation.generator import GeneratedSQL, SQLGenerator
from lumen.generation.runner import run_generated_sql
from lumen.interpretation.models import Interpretation
from lumen.llm.anthropic_provider import AnthropicProvider
from lumen.semantic.models import SemanticModel
from lumen.semantic.validator import validate_semantic_model
from lumen.validation.models import ValidationResult
from lumen.warehouse.base import Warehouse
from lumen.warehouse.schema import Schema

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    resolutions: dict[str, str] | None = None
    skip_interpretation: bool = False
    skip_validation: bool = False


class QueryResponse(BaseModel):
    interpretation: Interpretation | None = None
    generated_sql: str
    validation: ValidationResult
    rows: list[dict[str, Any]] | None = None
    row_count: int = 0
    error: str | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0


def _sse(obj: dict[str, Any]) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _execute_query(
    *,
    question: str,
    resolutions: dict[str, str] | None,
    skip_interpretation: bool,
    skip_validation: bool,
    settings: Settings,
    gen: SQLGenerator,
    model: SemanticModel,
    schema: Schema,
    wh: Warehouse,
) -> QueryResponse:
    validate_semantic_model(model, schema)
    t0 = time.perf_counter()
    provider = gen.provider
    interp: Interpretation | None = None
    generated: GeneratedSQL | None = None
    cost = 0.0

    if isinstance(provider, AnthropicProvider):
        provider.take_pending_cost_usd()

    if skip_interpretation:
        generated = gen.generate(
            question, model, schema, settings.dialect, skip_validation=skip_validation
        )
    elif resolutions:
        interp, generated = gen.generate_with_resolutions(
            question,
            model,
            schema,
            settings.dialect,
            resolutions,
            skip_validation=skip_validation,
        )
    else:
        interp, maybe = gen.generate_with_interpretation(
            question, model, schema, settings.dialect, skip_validation=skip_validation
        )
        if isinstance(provider, AnthropicProvider):
            cost += provider.take_pending_cost_usd()
        if maybe is None:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return QueryResponse(
                interpretation=interp,
                generated_sql="",
                validation=ValidationResult(valid=False, issues=[], parsed_sql=None),
                rows=None,
                row_count=0,
                error="ambiguous_interpretation",
                latency_ms=latency_ms,
                cost_usd=round(cost, 6),
            )
        generated = maybe

    if generated is None:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return QueryResponse(
            interpretation=interp,
            generated_sql="",
            validation=ValidationResult(valid=False, issues=[], parsed_sql=None),
            rows=None,
            row_count=0,
            error="generation_failed",
            latency_ms=latency_ms,
            cost_usd=round(cost, 6),
        )

    cost += float(generated.cost_usd)
    rows: list[dict[str, Any]] | None = None
    row_count = 0
    err: str | None = None
    if generated.validation.valid or skip_validation:
        qr = run_generated_sql(generated, wh)
        if qr.error:
            err = qr.error
        else:
            rows = qr.rows
            row_count = qr.row_count
    else:
        err = "validation_failed"

    latency_ms = int((time.perf_counter() - t0) * 1000)
    return QueryResponse(
        interpretation=interp,
        generated_sql=generated.sql,
        validation=generated.validation,
        rows=rows,
        row_count=row_count,
        error=err,
        latency_ms=latency_ms,
        cost_usd=round(cost, 6),
    )


@router.post("/query", response_model=QueryResponse)
def post_query(
    body: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    gen: Annotated[SQLGenerator, Depends(get_generator)],
    model: Annotated[SemanticModel, Depends(get_semantic_model)],
    schema: Annotated[Schema, Depends(get_schema)],
    wh: Annotated[Warehouse, Depends(get_warehouse)],
) -> QueryResponse:
    return _execute_query(
        question=body.question,
        resolutions=body.resolutions,
        skip_interpretation=body.skip_interpretation,
        skip_validation=body.skip_validation,
        settings=settings,
        gen=gen,
        model=model,
        schema=schema,
        wh=wh,
    )


@router.post("/query/stream")
async def post_query_stream(
    body: QueryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    gen: Annotated[SQLGenerator, Depends(get_generator)],
    model: Annotated[SemanticModel, Depends(get_semantic_model)],
    schema: Annotated[Schema, Depends(get_schema)],
    wh: Annotated[Warehouse, Depends(get_warehouse)],
) -> StreamingResponse:
    async def event_gen() -> AsyncIterator[str]:
        yield _sse({"phase": "interpreting", "detail": "explain-back"})
        try:
            result = await asyncio.to_thread(
                _execute_query,
                question=body.question,
                resolutions=body.resolutions,
                skip_interpretation=body.skip_interpretation,
                skip_validation=body.skip_validation,
                settings=settings,
                gen=gen,
                model=model,
                schema=schema,
                wh=wh,
            )
        except Exception as exc:
            logger.exception("query stream failed")
            yield _sse({"phase": "error", "detail": str(exc)})
            return
        yield _sse({"phase": "generated_sql", "sql": result.generated_sql})
        yield _sse({"phase": "validating", "valid": result.validation.valid})
        yield _sse({"phase": "executing", "row_count": result.row_count})
        yield _sse({"phase": "done", "payload": result.model_dump(mode="json")})

    return StreamingResponse(event_gen(), media_type="text/event-stream")

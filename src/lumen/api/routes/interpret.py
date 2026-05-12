import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from lumen.api.config import Settings
from lumen.api.deps import (
    get_generator,
    get_schema,
    get_semantic_model,
    get_settings,
    get_warehouse,
)
from lumen.generation.generator import SQLGenerator
from lumen.interpretation.models import Interpretation
from lumen.semantic.models import SemanticModel
from lumen.semantic.validator import validate_semantic_model
from lumen.warehouse.base import Warehouse
from lumen.warehouse.schema import Schema

logger = logging.getLogger(__name__)

router = APIRouter(tags=["interpret"])


class InterpretRequest(BaseModel):
    question: str = Field(min_length=1)


@router.post("/interpret")
def interpret_question(
    body: InterpretRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    gen: Annotated[SQLGenerator, Depends(get_generator)],
    model: Annotated[SemanticModel, Depends(get_semantic_model)],
    schema: Annotated[Schema, Depends(get_schema)],
    wh: Annotated[Warehouse, Depends(get_warehouse)],
) -> Interpretation:
    _ = wh
    validate_semantic_model(model, schema)
    return gen._ensure_interpreter().interpret(  # noqa: SLF001
        body.question, model, schema, settings.dialect
    )

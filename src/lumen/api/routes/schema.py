import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from lumen.api.deps import get_schema, get_semantic_model
from lumen.semantic.models import SemanticModel
from lumen.warehouse.schema import Schema

logger = logging.getLogger(__name__)

router = APIRouter(tags=["schema"])


@router.get("/schema")
def get_introspected_schema(schema: Annotated[Schema, Depends(get_schema)]) -> Schema:
    return schema


@router.get("/semantic")
def get_loaded_semantic(
    model: Annotated[SemanticModel, Depends(get_semantic_model)],
) -> SemanticModel:
    return model

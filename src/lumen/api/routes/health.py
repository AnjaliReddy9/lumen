import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from lumen import __version__
from lumen.api.config import Settings
from lumen.api.deps import get_semantic_model, get_settings, get_warehouse
from lumen.semantic.models import SemanticModel
from lumen.semantic.validator import validate_semantic_model
from lumen.warehouse.base import Warehouse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/ready")
def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    wh: Annotated[Warehouse, Depends(get_warehouse)],
    model: Annotated[SemanticModel, Depends(get_semantic_model)],
) -> dict[str, str | int]:
    try:
        schema = wh.introspect()
        validate_semantic_model(model, schema)
    except Exception as exc:
        logger.exception("readiness check failed")
        return {"status": "error", "detail": str(exc)}
    return {
        "status": "ok",
        "warehouse_tables": len(schema.tables),
        "semantic_entities": len(model.entities),
    }

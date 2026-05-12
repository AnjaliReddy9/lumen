from __future__ import annotations

import logging
from collections.abc import Generator
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends

from lumen.api.config import Settings
from lumen.generation.generator import SQLGenerator
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.llm.anthropic_provider import AnthropicProvider
from lumen.semantic.loader import load_semantic_model
from lumen.semantic.models import SemanticModel
from lumen.warehouse.base import Warehouse
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse
from lumen.warehouse.postgres_warehouse import PostgresWarehouse
from lumen.warehouse.schema import Schema

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=8)
def _warehouse_singleton(
    warehouse_path: str, warehouse_type: Literal["duckdb", "postgres"]
) -> Warehouse:
    if warehouse_type == "duckdb":
        wh: Warehouse = DuckDBWarehouse(warehouse_path)
    else:
        wh = PostgresWarehouse(warehouse_path)
    logger.info("opened warehouse type=%s path=%s", warehouse_type, warehouse_path)
    return wh


@lru_cache(maxsize=8)
def _semantic_singleton(semantic_dir: str) -> SemanticModel:
    model = load_semantic_model(Path(semantic_dir))
    logger.info("loaded semantic model from %s", semantic_dir)
    return model


@lru_cache(maxsize=8)
def _schema_singleton(
    warehouse_path: str, warehouse_type: Literal["duckdb", "postgres"]
) -> Schema:
    return _warehouse_singleton(warehouse_path, warehouse_type).introspect()


@lru_cache(maxsize=4)
def _generator_singleton(
    semantic_dir: str,
    warehouse_path: str,
    warehouse_type: Literal["duckdb", "postgres"],
    model: str,
    api_key: str,
) -> SQLGenerator:
    _ = semantic_dir, warehouse_path, warehouse_type
    provider = AnthropicProvider(api_key=api_key, model=model)
    interpreter = QueryInterpreter(provider)
    return SQLGenerator(provider, interpreter=interpreter)


def clear_singleton_caches() -> None:
    get_settings.cache_clear()
    _warehouse_singleton.cache_clear()
    _semantic_singleton.cache_clear()
    _schema_singleton.cache_clear()
    _generator_singleton.cache_clear()


def get_warehouse(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[Warehouse, None, None]:
    yield _warehouse_singleton(settings.warehouse_path, settings.warehouse_type)


def get_semantic_model(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[SemanticModel, None, None]:
    yield _semantic_singleton(str(settings.semantic_dir.resolve()))


def get_schema(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[Schema, None, None]:
    yield _schema_singleton(settings.warehouse_path, settings.warehouse_type)


def get_generator(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[SQLGenerator, None, None]:
    yield _generator_singleton(
        str(settings.semantic_dir.resolve()),
        settings.warehouse_path,
        settings.warehouse_type,
        settings.anthropic_model,
        settings.anthropic_api_key,
    )

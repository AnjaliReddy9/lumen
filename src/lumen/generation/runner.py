from typing import Any

from pydantic import BaseModel, Field

from lumen.generation.generator import GeneratedSQL
from lumen.warehouse.base import Warehouse


class QueryResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    error: str | None = None


def run_generated_sql(generated: GeneratedSQL, warehouse: Warehouse) -> QueryResult:
    try:
        rows = warehouse.execute(generated.sql)
        return QueryResult(sql=generated.sql, rows=rows, row_count=len(rows), error=None)
    except Exception as exc:
        return QueryResult(sql=generated.sql, rows=[], row_count=0, error=str(exc))

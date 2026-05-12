from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class FilterClause(BaseModel):
    column_or_dimension: str
    operator: str
    value: str
    confidence: Literal["high", "medium", "low"]


class SortClause(BaseModel):
    column_or_dimension: str
    direction: Literal["asc", "desc"]


class QueryIntent(BaseModel):
    question: str
    intent_summary: str
    entities_referenced: list[str]
    metrics_referenced: list[str]
    dimensions_referenced: list[str]
    time_grain: str | None
    filters: list[FilterClause]
    sort: SortClause | None
    limit: int | None


AmbiguityType = Literal[
    "dimension",
    "value",
    "metric",
    "time_range",
    "missing_filter",
    "join_path",
]


class AmbiguityIssue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: AmbiguityType
    description: str
    options: list[str]
    suggested_default: str | None = Field(
        default=None,
        validation_alias=AliasChoices("default", "suggested_default"),
        serialization_alias="default",
    )


class Interpretation(BaseModel):
    intent: QueryIntent
    ambiguities: list[AmbiguityIssue]
    confidence: Literal["high", "medium", "low"]

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Aggregation = Literal["sum", "count", "count_distinct", "avg", "min", "max"]
Granularity = Literal["day", "week", "month", "quarter", "year"]
MetricKind = Literal["simple", "ratio", "derived"]
RelationshipKind = Literal["one_to_one", "many_to_one", "one_to_many", "many_to_many"]


class Dimension(BaseModel):
    name: str
    column: str | None = None
    expression: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def exactly_one_of_column_or_expression(self) -> Self:
        has_col = self.column is not None
        has_expr = self.expression is not None
        if has_col and has_expr:
            raise ValueError("dimension cannot set both column and expression")
        if not has_col and not has_expr:
            raise ValueError("dimension requires exactly one of column or expression")
        return self


class TimeDimension(BaseModel):
    name: str
    column: str
    granularity: Granularity


class Measure(BaseModel):
    expression: str
    aggregation: Aggregation


class Entity(BaseModel):
    """A business entity mapped to one warehouse table."""

    name: str
    description: str | None = None
    table: str
    primary_key: str
    dimensions: list[Dimension] = Field(default_factory=list)
    time_dimensions: list[TimeDimension] = Field(default_factory=list)


class Metric(BaseModel):
    """A quantitative measure defined against a single entity."""

    name: str
    description: str | None = None
    type: MetricKind
    entity: str
    measure: Measure
    dimensions: list[str] = Field(default_factory=list)
    time_dimension: str | None = None


class Relationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    from_key: str
    to: str
    to_key: str
    type: RelationshipKind


class SemanticModel(BaseModel):
    """Full semantic configuration: entities, metrics, and declared joins."""

    entities: list[Entity]
    metrics: list[Metric]
    relationships: list[Relationship]

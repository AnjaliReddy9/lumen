import pytest
from pydantic import ValidationError

from lumen.semantic.models import (
    Dimension,
    Entity,
    Measure,
    Metric,
    Relationship,
    SemanticModel,
)


def test_dimension_requires_column_or_expression() -> None:
    with pytest.raises(ValidationError):
        Dimension(name="x")


def test_dimension_rejects_both_column_and_expression() -> None:
    with pytest.raises(ValidationError):
        Dimension(name="x", column="a", expression="b")


def test_semantic_model_round_trip_dict() -> None:
    original = SemanticModel(
        entities=[
            Entity(
                name="customer",
                table="Customer",
                primary_key="CustomerId",
                dimensions=[Dimension(name="country", column="Country")],
            ),
            Entity(
                name="invoice",
                table="Invoice",
                primary_key="InvoiceId",
                dimensions=[Dimension(name="billing_city", column="BillingCity")],
            ),
        ],
        metrics=[
            Metric(
                name="n",
                type="simple",
                entity="customer",
                measure=Measure(expression="x", aggregation="sum"),
                dimensions=["country"],
            )
        ],
        relationships=[
            Relationship.model_validate(
                {
                    "from": "invoice",
                    "from_key": "CustomerId",
                    "to": "customer",
                    "to_key": "CustomerId",
                    "type": "many_to_one",
                }
            )
        ],
    )
    data = original.model_dump(mode="python", by_alias=True)
    restored = SemanticModel.model_validate(data)
    assert restored == original

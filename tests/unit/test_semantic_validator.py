import pytest

from lumen.semantic.models import Dimension, Entity, Measure, Metric, Relationship, SemanticModel
from lumen.semantic.validator import validate_semantic_model
from lumen.warehouse.schema import Column, Schema, Table


def _col(name: str, pk: bool = False) -> Column:
    return Column(name=name, data_type="INTEGER", nullable=True, is_primary_key=pk)


def _table(name: str, columns: list[Column]) -> Table:
    return Table(name=name, schema_name=None, columns=columns, foreign_keys=[])


def _minimal_schema() -> Schema:
    return Schema(
        tables=[
            _table(
                "Customer",
                [_col("CustomerId", pk=True), _col("Country"), _col("FirstName"), _col("LastName")],
            ),
            _table(
                "Invoice",
                [
                    _col("InvoiceId", pk=True),
                    _col("CustomerId"),
                    _col("Total"),
                    _col("BillingCity"),
                    _col("BillingCountry"),
                    _col("InvoiceDate"),
                ],
            ),
        ]
    )


def test_validate_passes_for_consistent_model() -> None:
    model = SemanticModel(
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
                dimensions=[
                    Dimension(name="billing_city", column="BillingCity"),
                    Dimension(name="billing_country", column="BillingCountry"),
                ],
                time_dimensions=[],
            ),
        ],
        metrics=[
            Metric(
                name="total",
                type="simple",
                entity="invoice",
                measure=Measure(expression="Total", aggregation="sum"),
                dimensions=["billing_city"],
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
    validate_semantic_model(model, _minimal_schema())


def test_validate_fails_when_entity_table_missing() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="ghost",
                table="NoSuchTable",
                primary_key="id",
                dimensions=[Dimension(name="d", column="c")],
            )
        ],
        metrics=[],
        relationships=[],
    )
    with pytest.raises(ValueError, match="not found in warehouse schema"):
        validate_semantic_model(model, _minimal_schema())


def test_validate_fails_when_metric_entity_unknown() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="invoice",
                table="Invoice",
                primary_key="InvoiceId",
                dimensions=[Dimension(name="billing_city", column="BillingCity")],
            )
        ],
        metrics=[
            Metric(
                name="m",
                type="simple",
                entity="nope",
                measure=Measure(expression="Total", aggregation="sum"),
                dimensions=[],
            )
        ],
        relationships=[],
    )
    with pytest.raises(ValueError, match="unknown entity"):
        validate_semantic_model(model, _minimal_schema())


def test_validate_fails_when_dimension_column_missing() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="invoice",
                table="Invoice",
                primary_key="InvoiceId",
                dimensions=[Dimension(name="bad", column="NotAColumn")],
            )
        ],
        metrics=[],
        relationships=[],
    )
    with pytest.raises(ValueError, match="NotAColumn"):
        validate_semantic_model(model, _minimal_schema())


def test_validate_fails_when_relationship_entity_unknown() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="invoice",
                table="Invoice",
                primary_key="InvoiceId",
                dimensions=[],
            )
        ],
        metrics=[],
        relationships=[
            Relationship.model_validate(
                {
                    "from": "invoice",
                    "from_key": "CustomerId",
                    "to": "missing",
                    "to_key": "CustomerId",
                    "type": "many_to_one",
                }
            )
        ],
    )
    with pytest.raises(ValueError, match="unknown entity"):
        validate_semantic_model(model, _minimal_schema())

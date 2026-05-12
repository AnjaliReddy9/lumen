from unittest.mock import MagicMock

from lumen.generation.generator import SQLGenerator
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.interpretation.models import AmbiguityIssue, Interpretation, QueryIntent
from lumen.llm.base import LLMProvider
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.schema import Column, Schema, Table


class _FakeSQL:
    def __init__(self, sql: str) -> None:
        self._sql = sql

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._sql


def _tiny_schema() -> Schema:
    return Schema(
        tables=[
            Table(
                name="T",
                schema_name=None,
                columns=[Column(name="id", data_type="int", nullable=True, is_primary_key=True)],
                foreign_keys=[],
            )
        ]
    )


def _tiny_model() -> SemanticModel:
    return SemanticModel(
        entities=[
            Entity(
                name="e",
                table="T",
                primary_key="id",
                dimensions=[Dimension(name="d", column="id")],
            )
        ],
        metrics=[],
        relationships=[],
    )


def _intent(question: str = "q") -> QueryIntent:
    return QueryIntent(
        question=question,
        intent_summary="summary",
        entities_referenced=[],
        metrics_referenced=[],
        dimensions_referenced=[],
        time_grain=None,
        filters=[],
        sort=None,
        limit=None,
    )


def test_generate_with_interpretation_no_ambiguity_runs_sql() -> None:
    model = _tiny_model()
    schema = _tiny_schema()
    interp = Interpretation(
        intent=_intent("q"),
        ambiguities=[],
        confidence="high",
    )
    mock_i = MagicMock(spec=QueryInterpreter)
    mock_i.interpret.return_value = interp
    p: LLMProvider = _FakeSQL("SELECT id FROM T")
    gen = SQLGenerator(p, interpreter=mock_i)
    out_i, out_g = gen.generate_with_interpretation(
        "q", model, schema, "sqlite", skip_validation=True
    )
    assert out_i is interp
    assert out_g is not None
    assert "SELECT" in out_g.sql.upper()


def test_generate_with_interpretation_ambiguity_skips_sql() -> None:
    model = _tiny_model()
    schema = _tiny_schema()
    interp = Interpretation(
        intent=_intent(),
        ambiguities=[
            AmbiguityIssue(
                type="metric",
                description="Which metric?",
                options=["a", "b"],
                suggested_default="a",
            )
        ],
        confidence="medium",
    )
    mock_i = MagicMock(spec=QueryInterpreter)
    mock_i.interpret.return_value = interp
    p: LLMProvider = _FakeSQL("SELECT id FROM T")
    gen = SQLGenerator(p, interpreter=mock_i)
    out_i, out_g = gen.generate_with_interpretation(
        "q", model, schema, "sqlite", skip_validation=True
    )
    assert out_g is None
    mock_i.interpret.assert_called_once()

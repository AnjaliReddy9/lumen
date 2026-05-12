from typing import Any
from unittest.mock import MagicMock

from lumen.generation.generator import SQLGenerator
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.interpretation.models import Interpretation, QueryIntent
from lumen.llm.base import LLMProvider
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.schema import Column, Schema, Table


class _FakeSQL:
    def __init__(self, sql: str) -> None:
        self._sql = sql

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._sql


def _schema_model() -> tuple[Schema, SemanticModel]:
    schema = Schema(
        tables=[
            Table(
                name="T",
                schema_name=None,
                columns=[Column(name="id", data_type="int", nullable=True, is_primary_key=True)],
                foreign_keys=[],
            )
        ]
    )
    model = SemanticModel(
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
    return schema, model


def test_resolutions_passed_to_interpreter() -> None:
    schema, model = _schema_model()
    calls: list[Any] = []

    def interpret_side_effect(
        question: str,
        semantic_model: SemanticModel,
        sch: Schema,
        dialect: str,
        *,
        resolutions: dict[str, str] | None = None,
    ) -> Interpretation:
        calls.append(resolutions)
        return Interpretation(
            intent=QueryIntent(
                question=question,
                intent_summary="ok",
                entities_referenced=[],
                metrics_referenced=[],
                dimensions_referenced=[],
                time_grain=None,
                filters=[],
                sort=None,
                limit=None,
            ),
            ambiguities=[],
            confidence="high",
        )

    mock_i = MagicMock(spec=QueryInterpreter)
    mock_i.interpret.side_effect = interpret_side_effect
    p: LLMProvider = _FakeSQL("SELECT id FROM T")
    gen = SQLGenerator(p, interpreter=mock_i)
    res = {"Which state?": "CA"}
    gen.generate_with_resolutions("q", model, schema, "sqlite", res, skip_validation=True)
    assert calls == [res]

from lumen.generation.generator import SQLGenerator
from lumen.llm.base import LLMProvider
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.schema import Column, Schema, Table


class _FlipProvider:
    def __init__(self, bad: str, good: str) -> None:
        self._calls = 0
        self._bad = bad
        self._good = good

    def generate(self, prompt: str, system: str | None = None) -> str:
        self._calls += 1
        if self._calls == 1:
            return self._bad
        return self._good


def test_generator_retries_and_succeeds() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="e",
                table="T",
                primary_key="id",
                dimensions=[Dimension(name="d", column="c")],
            )
        ],
        metrics=[],
        relationships=[],
    )
    schema = Schema(
        tables=[
            Table(
                name="T",
                schema_name=None,
                columns=[
                    Column(name="id", data_type="int", nullable=True, is_primary_key=True),
                    Column(name="c", data_type="int", nullable=True, is_primary_key=False),
                ],
                foreign_keys=[],
            )
        ]
    )
    bad = "SELECT mystery FROM T"
    good = "SELECT c FROM T"
    p: LLMProvider = _FlipProvider(bad, good)
    gen = SQLGenerator(p, max_retries=2)
    out = gen.generate("show c", model, schema, "sqlite")
    assert out.attempts == 2
    assert out.validation.valid
    assert "c" in out.sql.lower()

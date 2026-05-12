from lumen.generation.generator import SQLGenerator
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.schema import Column, Schema, Table


class _AlwaysBad:
    def __init__(self, sql: str) -> None:
        self.calls = 0
        self._sql = sql

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.calls += 1
        return self._sql


def test_generator_exhausts_retries() -> None:
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
                columns=[Column(name="id", data_type="int", nullable=True, is_primary_key=True)],
                foreign_keys=[],
            )
        ]
    )
    p = _AlwaysBad("SELECT not_a_column FROM T")
    gen = SQLGenerator(p, max_retries=2)
    out = gen.generate("q", model, schema, "sqlite")
    assert p.calls == 3
    assert not out.validation.valid
    assert out.attempts == 3
    assert any(i.code == "unknown_column" for i in out.validation.issues)

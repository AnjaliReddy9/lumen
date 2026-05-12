from lumen.generation.generator import SQLGenerator
from lumen.llm.base import LLMProvider
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.schema import Column, Schema, Table


class _FakeProvider:
    def __init__(self, text: str) -> None:
        self._text = text

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._text


def test_generator_strips_markdown_sql_fence() -> None:
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
    raw = "```sql\nSELECT 1 AS x\n```\n"
    gen = SQLGenerator(_FakeProvider(raw))
    out = gen.generate("hi", model, schema, "sqlite")
    assert out.raw_response == raw
    assert "SELECT 1 AS x" in out.sql
    assert "```" not in out.sql


def test_generator_strips_plain_fence() -> None:
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
    raw = "```\nSELECT 2\n```"
    gen = SQLGenerator(_FakeProvider(raw))
    out = gen.generate("q", model, schema, "sqlite")
    assert out.sql.strip() == "SELECT 2"


def test_fake_provider_structural_llm() -> None:
    p: LLMProvider = _FakeProvider("x")
    assert p.generate("a", "b") == "x"

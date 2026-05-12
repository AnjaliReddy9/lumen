from pydantic import BaseModel

from lumen.generation.prompt import build_sql_prompt
from lumen.llm.base import LLMProvider
from lumen.semantic.models import SemanticModel
from lumen.warehouse.schema import Schema


class GeneratedSQL(BaseModel):
    question: str
    sql: str
    dialect: str
    raw_response: str


class SQLGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    def generate(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
    ) -> GeneratedSQL:
        system, user = build_sql_prompt(question, semantic_model, schema, dialect)
        raw = self._provider.generate(user, system)
        cleaned = _strip_markdown_sql_fences(raw)
        return GeneratedSQL(
            question=question,
            sql=cleaned,
            dialect=dialect,
            raw_response=raw,
        )


def _strip_markdown_sql_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()

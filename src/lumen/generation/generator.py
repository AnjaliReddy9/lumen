from pydantic import BaseModel

from lumen.generation.prompt import build_correction_prompt, build_sql_prompt
from lumen.llm.base import LLMProvider
from lumen.semantic.models import SemanticModel
from lumen.validation.models import ValidationResult
from lumen.validation.validator import SQLValidator
from lumen.warehouse.schema import Schema


class GeneratedSQL(BaseModel):
    question: str
    sql: str
    dialect: str
    raw_response: str
    validation: ValidationResult
    attempts: int


class SQLGenerator:
    def __init__(self, provider: LLMProvider, max_retries: int = 2) -> None:
        self._provider = provider
        self._max_retries = max_retries

    def generate(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        *,
        skip_validation: bool = False,
    ) -> GeneratedSQL:
        validator = SQLValidator(schema)
        system, user = build_sql_prompt(question, semantic_model, schema, dialect)
        max_attempts = self._max_retries + 1
        attempts = 0
        last_raw = ""
        current_sql = ""
        last_validation = ValidationResult(valid=False, issues=[], parsed_sql=None)

        while attempts < max_attempts:
            attempts += 1
            if attempts == 1:
                last_raw = self._provider.generate(user, system)
            else:
                sys2, usr2 = build_correction_prompt(
                    question,
                    current_sql,
                    last_validation.issues,
                    semantic_model,
                    schema,
                    dialect,
                )
                last_raw = self._provider.generate(usr2, sys2)
            cleaned = _strip_markdown_sql_fences(last_raw)
            current_sql = cleaned

            if skip_validation:
                vr = ValidationResult(valid=True, issues=[], parsed_sql=cleaned)
                return GeneratedSQL(
                    question=question,
                    sql=cleaned,
                    dialect=dialect,
                    raw_response=last_raw,
                    validation=vr,
                    attempts=attempts,
                )

            last_validation = validator.validate(cleaned, dialect)
            if last_validation.valid:
                out_sql = last_validation.parsed_sql or cleaned
                return GeneratedSQL(
                    question=question,
                    sql=out_sql,
                    dialect=dialect,
                    raw_response=last_raw,
                    validation=last_validation,
                    attempts=attempts,
                )

            if attempts >= max_attempts:
                break

        return GeneratedSQL(
            question=question,
            sql=current_sql,
            dialect=dialect,
            raw_response=last_raw,
            validation=last_validation,
            attempts=attempts,
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

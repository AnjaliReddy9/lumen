from pydantic import BaseModel

from lumen.generation.prompt import build_correction_prompt, build_sql_prompt
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.interpretation.models import Interpretation, QueryIntent
from lumen.llm.anthropic_provider import AnthropicProvider
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
    def __init__(
        self,
        provider: LLMProvider,
        max_retries: int = 2,
        interpreter: QueryInterpreter | None = None,
    ) -> None:
        self._provider = provider
        self._max_retries = max_retries
        self._interpreter = interpreter

    def _ensure_interpreter(self) -> QueryInterpreter:
        if self._interpreter is not None:
            return self._interpreter
        if isinstance(self._provider, AnthropicProvider):
            self._interpreter = QueryInterpreter(self._provider)
            return self._interpreter
        raise TypeError(
            "SQL interpretation requires AnthropicProvider or pass interpreter= to "
            "SQLGenerator"
        )

    def generate(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        *,
        skip_validation: bool = False,
    ) -> GeneratedSQL:
        return self._generate_sql(
            question,
            semantic_model,
            schema,
            dialect,
            intent=None,
            skip_validation=skip_validation,
        )

    def generate_with_interpretation(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        *,
        skip_validation: bool = False,
    ) -> tuple[Interpretation, GeneratedSQL | None]:
        interp = self._ensure_interpreter().interpret(
            question, semantic_model, schema, dialect
        )
        if interp.ambiguities:
            return (interp, None)
        gen = self._generate_sql(
            question,
            semantic_model,
            schema,
            dialect,
            intent=interp.intent,
            skip_validation=skip_validation,
        )
        return (interp, gen)

    def generate_with_resolutions(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        resolutions: dict[str, str],
        *,
        skip_validation: bool = False,
    ) -> tuple[Interpretation, GeneratedSQL]:
        interp = self._ensure_interpreter().interpret(
            question, semantic_model, schema, dialect, resolutions=resolutions
        )
        gen = self._generate_sql(
            question,
            semantic_model,
            schema,
            dialect,
            intent=interp.intent,
            skip_validation=skip_validation,
        )
        return (interp, gen)

    def _generate_sql(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        *,
        intent: QueryIntent | None,
        skip_validation: bool,
    ) -> GeneratedSQL:
        validator = SQLValidator(schema)
        system, user = build_sql_prompt(
            question, semantic_model, schema, dialect, intent=intent
        )
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

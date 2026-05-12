from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import ValidationError

from lumen.interpretation.models import (
    AmbiguityIssue,
    Interpretation,
    QueryIntent,
)
from lumen.interpretation.prompt import build_interpretation_prompt
from lumen.interpretation.tool_spec import SUBMIT_INTERPRETATION_TOOL
from lumen.semantic.models import SemanticModel
from lumen.warehouse.schema import Schema


class ToolCallingClient(Protocol):
    def call_tool_use(
        self,
        *,
        system: str,
        user: str,
        tool: Any,
    ) -> dict[str, Any]: ...


def _fallback_interpretation(question: str) -> Interpretation:
    return Interpretation(
        intent=QueryIntent(
            question=question,
            intent_summary="",
            entities_referenced=[],
            metrics_referenced=[],
            dimensions_referenced=[],
            time_grain=None,
            filters=[],
            sort=None,
            limit=None,
        ),
        ambiguities=[
            AmbiguityIssue(
                type="join_path",
                description=(
                    "The interpreter did not return parseable structured interpretation "
                    "JSON after retry."
                ),
                options=["Rephrase the question", "Try again later"],
                suggested_default=None,
            )
        ],
        confidence="low",
    )


class QueryInterpreter:
    def __init__(self, client: ToolCallingClient) -> None:
        self._client = client

    def interpret(
        self,
        question: str,
        semantic_model: SemanticModel,
        schema: Schema,
        dialect: str,
        *,
        resolutions: dict[str, str] | None = None,
    ) -> Interpretation:
        system, base_user = build_interpretation_prompt(
            question, semantic_model, schema, dialect, resolutions=resolutions
        )
        user = base_user
        last_err: str | None = None
        for attempt in range(2):
            if last_err is not None:
                user = (
                    f"{base_user}\n\n=== PREVIOUS OUTPUT FAILED PYDANTIC VALIDATION ===\n"
                    f"{last_err}\n"
                    "Return a corrected submit_interpretation tool call that matches the "
                    "schema exactly."
                )
            raw = self._client.call_tool_use(
                system=system,
                user=user,
                tool=SUBMIT_INTERPRETATION_TOOL,
            )
            try:
                interp = Interpretation.model_validate_json(json.dumps(raw))
            except ValidationError as err:
                last_err = str(err)
                if attempt == 1:
                    return _fallback_interpretation(question)
                continue
            if not interp.intent.question.strip():
                interp.intent.question = question
            return interp
        return _fallback_interpretation(question)

"""Deterministic LLM provider for eval smoke tests (no Anthropic calls)."""

from __future__ import annotations

import re
from typing import Any

_QUESTION_BLOCK = re.compile(
    r"=== QUESTION ===\s*(.*?)(?=\n===)", re.DOTALL | re.IGNORECASE
)
_ORIGINAL_Q = re.compile(
    r"=== ORIGINAL QUESTION ===\s*(.*?)(?=\n===)", re.DOTALL | re.IGNORECASE
)


class EvalGroundTruthFakeProvider:
    """Returns ground-truth SQL when the user prompt contains a known question text."""

    model_name = "eval-ground-truth-fake"

    def __init__(self, question_to_sql: dict[str, str]) -> None:
        self._map = {k.strip(): v.strip() for k, v in question_to_sql.items() if k and v}

    def generate(self, prompt: str, system: str | None = None) -> str:
        _ = system
        m = _ORIGINAL_Q.search(prompt) or _QUESTION_BLOCK.search(prompt)
        q = (m.group(1).strip() if m else "").strip()
        return self._map.get(q, "SELECT 1")

    def take_pending_cost_usd(self) -> float:
        return 0.0

    def call_tool_use(
        self,
        *,
        system: str,
        user: str,
        tool: Any,
    ) -> dict[str, Any]:
        _ = system, tool
        m = _QUESTION_BLOCK.search(user) or _ORIGINAL_Q.search(user)
        qtext = (m.group(1).strip() if m else "") or ""
        return {
            "confidence": "high",
            "intent": {
                "question": qtext,
                "intent_summary": "stub interpretation for eval fake provider",
                "entities_referenced": [],
                "metrics_referenced": [],
                "dimensions_referenced": [],
                "time_grain": None,
                "filters": [],
                "sort": None,
                "limit": None,
            },
            "ambiguities": [],
        }

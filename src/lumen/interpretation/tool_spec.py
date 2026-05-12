from typing import Any, cast

from anthropic.types import ToolParam

_FILTER_ITEM: dict[str, Any] = {
    "type": "object",
    "properties": {
        "column_or_dimension": {"type": "string"},
        "operator": {"type": "string"},
        "value": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["column_or_dimension", "operator", "value", "confidence"],
}

_SORT = {
    "type": "object",
    "properties": {
        "column_or_dimension": {"type": "string"},
        "direction": {"type": "string", "enum": ["asc", "desc"]},
    },
    "required": ["column_or_dimension", "direction"],
}

_INTENT = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "intent_summary": {"type": "string"},
        "entities_referenced": {"type": "array", "items": {"type": "string"}},
        "metrics_referenced": {"type": "array", "items": {"type": "string"}},
        "dimensions_referenced": {"type": "array", "items": {"type": "string"}},
        "time_grain": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "filters": {"type": "array", "items": _FILTER_ITEM},
        "sort": {"anyOf": [_SORT, {"type": "null"}]},
        "limit": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
    },
    "required": [
        "question",
        "intent_summary",
        "entities_referenced",
        "metrics_referenced",
        "dimensions_referenced",
        "time_grain",
        "filters",
        "sort",
        "limit",
    ],
}

_AMBIGUITY = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                "dimension",
                "value",
                "metric",
                "time_range",
                "missing_filter",
                "join_path",
            ],
        },
        "description": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "default": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["type", "description", "options", "default"],
}

SUBMIT_INTERPRETATION_TOOL = cast(
    ToolParam,
    {
        "name": "submit_interpretation",
        "description": (
            "Submit the structured interpretation of the user's analytics question, including "
            "intent fields and any ambiguities that need human resolution."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "intent": _INTENT,
                "ambiguities": {"type": "array", "items": _AMBIGUITY},
            },
            "required": ["confidence", "intent", "ambiguities"],
        },
    },
)

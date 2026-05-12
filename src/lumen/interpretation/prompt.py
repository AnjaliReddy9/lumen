from lumen.generation.prompt import _append_semantic_model_and_schema
from lumen.semantic.models import SemanticModel
from lumen.warehouse.schema import Schema


def build_interpretation_prompt(
    question: str,
    semantic_model: SemanticModel,
    schema: Schema,
    dialect: str,
    resolutions: dict[str, str] | None = None,
) -> tuple[str, str]:
    # System holds role, ambiguity examples, and a compact JSON shape spec (not raw
    # Pydantic export) so the model fills the tool input quickly and predictably.
    system = (
        "You are Lumen's query interpreter. Your job is to read an analytics question, "
        "the semantic model, and the physical warehouse schema, then produce a structured "
        "interpretation using the submit_interpretation tool exactly once.\n"
        "\n"
        "You must:\n"
        "(a) Restate what the user is asking in one plain-English line (intent_summary).\n"
        "(b) List semantic entity names, metric names, and dimension names that plausibly "
        "apply (use exact names from the semantic model when possible).\n"
        "(c) Capture time_grain if the question implies day/week/month/quarter/year "
        "bucketing, else null.\n"
        "(d) List filter clauses with operator one of: =, !=, <, >, <=, >=, LIKE, IN, "
        "BETWEEN and value as readable text.\n"
        "(e) Capture sort (column_or_dimension + asc|desc) and limit if stated.\n"
        "(f) Actively list ambiguities when the question could mean more than one thing. "
        "Each ambiguity has: type (one of dimension|value|metric|time_range|missing_filter|"
        "join_path), description (plain English), options (non-empty list of distinct "
        "choices), and default (the single option string you would pick if forced, or null "
        "if none is safe).\n"
        "\n"
        "Ambiguity examples (flag these patterns):\n"
        '- A bare place name like "California" may mean Customer.State = \'California\' '
        "or a different geography column; use type value or dimension.\n"
        '- "by area" may mean Customer.Country, Customer.State, or another geographic '
        "dimension; use type dimension.\n"
        '- "last quarter" may mean fiscal Q1-Q4 of which year, calendar quarter, or prior '
        "90 days; use type time_range.\n"
        '- "top customers" needs a ranking metric (revenue, track count, recency); use '
        "type metric or missing_filter.\n"
        "\n"
        "Be conservative: when in doubt, add an ambiguity instead of guessing silently. "
        "Set overall confidence to high only if the question maps cleanly to the semantic "
        "model with few assumptions; medium or low when assumptions pile up.\n"
        "\n"
        "JSON shape for tool input (field names and nesting must match exactly):\n"
        "{\n"
        '  "confidence": "high" | "medium" | "low",\n'
        '  "intent": {\n'
        '    "question": "<original question string>",\n'
        '    "intent_summary": "<one line>",\n'
        '    "entities_referenced": ["..."],\n'
        '    "metrics_referenced": ["..."],\n'
        '    "dimensions_referenced": ["..."],\n'
        '    "time_grain": "<string or null>",\n'
        '    "filters": [\n'
        '      {"column_or_dimension": "...", "operator": "=", "value": "...", '
        '"confidence": "high|medium|low"}\n'
        "    ],\n"
        '    "sort": {"column_or_dimension": "...", "direction": "asc|desc"} | null,\n'
        '    "limit": <integer or null>\n'
        "  },\n"
        '  "ambiguities": [\n'
        "    {\n"
        '      "type": "dimension|value|metric|time_range|missing_filter|join_path",\n'
        '      "description": "...",\n'
        '      "options": ["...", "..."],\n'
        '      "default": "<one option string or null>"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        f"\nDialect context for the warehouse engine: {dialect}.\n"
        "Return only the tool call; do not emit markdown or prose outside the tool."
    )

    lines: list[str] = []
    lines.append("=== QUESTION ===")
    lines.append(question.strip())
    lines.append("")
    if resolutions:
        lines.append("=== USER RESOLUTIONS (already chosen) ===")
        for desc, choice in resolutions.items():
            lines.append(f"- {desc}: {choice}")
        lines.append("")
    _append_semantic_model_and_schema(lines, semantic_model, schema)
    user = "\n".join(lines).strip()
    return system, user

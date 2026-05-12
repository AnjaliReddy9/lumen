from lumen.interpretation.models import QueryIntent
from lumen.semantic.models import SemanticModel
from lumen.validation.models import ValidationIssue
from lumen.warehouse.schema import Schema


def _append_semantic_model_and_schema(
    lines: list[str], semantic_model: SemanticModel, schema: Schema
) -> None:
    lines.append("=== SEMANTIC MODEL ===")
    lines.append("--- ENTITIES ---")
    for ent in sorted(semantic_model.entities, key=lambda e: e.name):
        lines.append(f"entity: {ent.name}")
        lines.append(f"  table: {ent.table}")
        lines.append(f"  primary_key: {ent.primary_key}")
        if ent.description:
            lines.append(f"  description: {ent.description}")
        for d in ent.dimensions:
            if d.column is not None:
                lines.append(f"  dimension: {d.name}  column={d.column}")
            else:
                lines.append(f"  dimension: {d.name}  expression={d.expression}")
            if d.description:
                lines.append(f"    note: {d.description}")
        for td in ent.time_dimensions:
            lines.append(
                f"  time_dimension: {td.name}  column={td.column}  granularity={td.granularity}"
            )
        lines.append("")
    lines.append("--- METRICS ---")
    for m in sorted(semantic_model.metrics, key=lambda x: x.name):
        lines.append(f"metric: {m.name}")
        lines.append(f"  entity: {m.entity}")
        lines.append(f"  type: {m.type}")
        lines.append(f"  measure: {m.measure.aggregation}({m.measure.expression})")
        if m.description:
            lines.append(f"  description: {m.description}")
        if m.dimensions:
            lines.append(f"  allowed_dimensions: {', '.join(m.dimensions)}")
        if m.time_dimension:
            lines.append(f"  time_dimension: {m.time_dimension}")
        lines.append("")
    lines.append("--- RELATIONSHIPS ---")
    for rel in semantic_model.relationships:
        lines.append(
            f"  {rel.from_}.{rel.from_key} -> {rel.to}.{rel.to_key}  ({rel.type})"
        )
    lines.append("")
    lines.append("=== WAREHOUSE SCHEMA (physical) ===")
    for tbl in sorted(schema.tables, key=lambda t: t.name):
        lines.append(f"table {tbl.name}")
        for col in sorted(tbl.columns, key=lambda c: c.name):
            pk = " pk" if col.is_primary_key else ""
            null = "" if col.nullable else " not_null"
            lines.append(f"  {col.name}  {col.data_type}{pk}{null}")
        lines.append("")


def build_sql_prompt(
    question: str,
    semantic_model: SemanticModel,
    schema: Schema,
    dialect: str,
    intent: QueryIntent | None = None,
) -> tuple[str, str]:
    # System stays short; user block carries semantic + physical schema.
    system = (
        f"You are Lumen's SQL generator. You turn natural-language analytics questions "
        f"into exactly one SQL query for the {dialect} dialect.\n"
        "\n"
        "Rules:\n"
        "- Use only tables and columns that exist in the warehouse schema provided below.\n"
        "- Prefer semantic-layer entities, dimensions, metrics, and relationships when they "
        "map cleanly to the question.\n"
        "- Return ONLY the SQL statement: no markdown fences, no prose before or after, "
        "and avoid extra comments when possible.\n"
        f"- The query must be executable as-is in {dialect}."
    )

    lines: list[str] = []
    if intent is not None:
        lines.append("=== INTERPRETED INTENT ===")
        lines.append(f"Summary: {intent.intent_summary}")
        if intent.entities_referenced:
            lines.append(f"Entities: {', '.join(intent.entities_referenced)}")
        if intent.metrics_referenced:
            lines.append(f"Metrics: {', '.join(intent.metrics_referenced)}")
        if intent.dimensions_referenced:
            lines.append(f"Dimensions: {', '.join(intent.dimensions_referenced)}")
        if intent.time_grain:
            lines.append(f"Time grain: {intent.time_grain}")
        if intent.filters:
            lines.append("Filters:")
            for f in intent.filters:
                lines.append(
                    f"  - {f.column_or_dimension} {f.operator} {f.value!r} "
                    f"(confidence {f.confidence})"
                )
        if intent.sort:
            lines.append(
                f"Sort: {intent.sort.column_or_dimension} {intent.sort.direction.upper()}"
            )
        if intent.limit is not None:
            lines.append(f"Limit: {intent.limit}")
        lines.append("")
    lines.append("=== QUESTION ===")
    lines.append(question.strip())
    lines.append("")
    _append_semantic_model_and_schema(lines, semantic_model, schema)
    user = "\n".join(lines).strip()
    return system, user


def build_correction_prompt(
    original_question: str,
    previous_sql: str,
    issues: list[ValidationIssue],
    semantic_model: SemanticModel,
    schema: Schema,
    dialect: str,
) -> tuple[str, str]:
    # Correction round: keep system minimal so the model focuses on fixes; user block repeats
    # full semantic + physical context so identifiers stay grounded like the first turn.
    system = (
        "The previous SQL was invalid for this warehouse. Fix it so every table and "
        "column reference exists in the schema below. Return ONLY the corrected SQL for "
        f"the {dialect} dialect: no markdown fences and no explanation."
    )
    lines: list[str] = []
    lines.append("=== ORIGINAL QUESTION ===")
    lines.append(original_question.strip())
    lines.append("")
    lines.append("=== PREVIOUS SQL (INVALID) ===")
    lines.append(previous_sql.strip())
    lines.append("")
    lines.append("=== VALIDATION ISSUES ===")
    for issue in issues:
        lines.append(f"- [{issue.code}] {issue.message}")
    lines.append("")
    _append_semantic_model_and_schema(lines, semantic_model, schema)
    user = "\n".join(lines).strip()
    return system, user

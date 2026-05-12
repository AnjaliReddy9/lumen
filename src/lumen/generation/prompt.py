from lumen.semantic.models import SemanticModel
from lumen.warehouse.schema import Schema


def build_sql_prompt(
    question: str,
    semantic_model: SemanticModel,
    schema: Schema,
    dialect: str,
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
    lines.append("=== QUESTION ===")
    lines.append(question.strip())
    lines.append("")
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
    user = "\n".join(lines).strip()
    return system, user

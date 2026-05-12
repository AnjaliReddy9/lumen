from lumen.semantic.models import Entity, Metric, SemanticModel
from lumen.warehouse.schema import Schema, Table


def validate_semantic_model(model: SemanticModel, schema: Schema) -> None:
    """Ensure semantic definitions line up with the warehouse schema and each other."""
    _assert_unique_entity_names(model.entities)
    _assert_unique_metric_names(model.metrics)

    for metric in model.metrics:
        if metric.type != "simple":
            raise ValueError(
                f"metric {metric.name!r}: only type 'simple' is supported in this release "
                f"(got {metric.type!r})"
            )

    entities_by_name: dict[str, Entity] = {}
    for entity in model.entities:
        entities_by_name[entity.name.casefold()] = entity

    for entity in model.entities:
        wh_table = schema.find_table(entity.table)
        if wh_table is None:
            raise ValueError(
                f"entity {entity.name!r}: table {entity.table!r} not found in warehouse schema"
            )
        _assert_column_exists(wh_table, entity.primary_key, f"entity {entity.name!r} primary_key")
        for dim in entity.dimensions:
            if dim.column is not None:
                ctx = f"entity {entity.name!r} dimension {dim.name!r}"
                _assert_column_exists(wh_table, dim.column, ctx)
        for td in entity.time_dimensions:
            ctx = f"entity {entity.name!r} time_dimension {td.name!r}"
            _assert_column_exists(wh_table, td.column, ctx)

    dim_names_by_entity: dict[str, set[str]] = {}
    time_names_by_entity: dict[str, set[str]] = {}
    for entity in model.entities:
        dnames = {d.name.casefold() for d in entity.dimensions}
        if len(dnames) != len(entity.dimensions):
            raise ValueError(f"entity {entity.name!r}: duplicate dimension names")
        dim_names_by_entity[entity.name.casefold()] = dnames
        tnames = {t.name.casefold() for t in entity.time_dimensions}
        if len(tnames) != len(entity.time_dimensions):
            raise ValueError(f"entity {entity.name!r}: duplicate time_dimension names")
        time_names_by_entity[entity.name.casefold()] = tnames

    for metric in model.metrics:
        ent = entities_by_name.get(metric.entity.casefold())
        if ent is None:
            raise ValueError(f"metric {metric.name!r}: unknown entity {metric.entity!r}")
        dims_ok = dim_names_by_entity[ent.name.casefold()]
        times_ok = time_names_by_entity[ent.name.casefold()]
        for dname in metric.dimensions:
            if dname.casefold() not in dims_ok:
                raise ValueError(
                    f"metric {metric.name!r}: dimension {dname!r} "
                    f"is not defined on entity {ent.name!r}"
                )
        if metric.time_dimension is not None:
            if metric.time_dimension.casefold() not in times_ok:
                raise ValueError(
                    f"metric {metric.name!r}: time_dimension {metric.time_dimension!r} "
                    f"is not defined on entity {ent.name!r}"
                )

    for rel in model.relationships:
        from_ent = entities_by_name.get(rel.from_.casefold())
        to_ent = entities_by_name.get(rel.to.casefold())
        if from_ent is None:
            raise ValueError(f"relationship: unknown entity {rel.from_!r} in 'from'")
        if to_ent is None:
            raise ValueError(f"relationship: unknown entity {rel.to!r} in 'to'")
        from_table = schema.find_table(from_ent.table)
        to_table = schema.find_table(to_ent.table)
        if from_table is None or to_table is None:
            raise ValueError("relationship: warehouse table missing for resolved entity")
        rel_ctx = f"relationship {rel.from_!r} -> {rel.to!r}"
        _assert_column_exists(from_table, rel.from_key, f"{rel_ctx} from_key")
        _assert_column_exists(to_table, rel.to_key, f"{rel_ctx} to_key")


def _assert_unique_entity_names(entities: list[Entity]) -> None:
    seen: set[str] = set()
    for e in entities:
        k = e.name.casefold()
        if k in seen:
            raise ValueError(f"duplicate entity name {e.name!r}")
        seen.add(k)


def _assert_unique_metric_names(metrics: list[Metric]) -> None:
    seen: set[str] = set()
    for m in metrics:
        k = m.name.casefold()
        if k in seen:
            raise ValueError(f"duplicate metric name {m.name!r}")
        seen.add(k)


def _assert_column_exists(table: Table, column_name: str, context: str) -> None:
    for col in table.columns:
        if col.name.casefold() == column_name.casefold():
            return
    raise ValueError(
        f"{context}: column {column_name!r} not found on warehouse table {table.name!r}"
    )

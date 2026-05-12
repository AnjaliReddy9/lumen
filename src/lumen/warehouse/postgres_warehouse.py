from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from lumen.warehouse.schema import Column, ForeignKey, Schema, Table


class PostgresWarehouse:
    """Postgres warehouse using SQLAlchemy's inspector."""

    def __init__(self, url: str) -> None:
        self._engine: Engine = create_engine(url)

    def introspect(self) -> Schema:
        inspector = inspect(self._engine)
        tables_out: list[Table] = []
        schemas = [
            s
            for s in inspector.get_schema_names()
            if s not in ("information_schema", "pg_catalog", "pg_toast")
        ]
        for schema_name in schemas:
            for table_name in inspector.get_table_names(schema=schema_name):
                raw_cols = inspector.get_columns(table_name, schema=schema_name)
                pk_cols = set(
                    inspector.get_pk_constraint(table_name, schema=schema_name).get(
                        "constrained_columns"
                    )
                    or []
                )
                columns = [
                    Column(
                        name=str(col["name"]),
                        data_type=str(col.get("type", "")),
                        nullable=bool(col.get("nullable", True)),
                        is_primary_key=str(col["name"]) in pk_cols,
                    )
                    for col in raw_cols
                ]
                foreign_keys: list[ForeignKey] = []
                for fk in inspector.get_foreign_keys(table_name, schema=schema_name):
                    from_cols = fk["constrained_columns"]
                    to_cols = fk["referred_columns"]
                    ref_table = str(fk["referred_table"])
                    for from_col, to_col in zip(from_cols, to_cols, strict=True):
                        foreign_keys.append(
                            ForeignKey(from_column=from_col, to_table=ref_table, to_column=to_col)
                        )
                schema_label = None if schema_name == "public" else schema_name
                tables_out.append(
                    Table(
                        name=table_name,
                        schema_name=schema_label,
                        columns=columns,
                        foreign_keys=foreign_keys,
                    )
                )
        return Schema(tables=tables_out)

    def execute(self, sql: str) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(row._mapping) for row in result]

    def close(self) -> None:
        self._engine.dispose()

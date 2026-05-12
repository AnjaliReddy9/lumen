import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

import duckdb

from lumen.warehouse.schema import Column, ForeignKey, Schema, Table


class DuckDBWarehouse:
    """DuckDB-backed warehouse using catalog views or an attached SQLite file."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._sqlite_fk_path: Path | None = None
        self._attach_alias: str | None = None
        raw = str(path)
        if raw == ":memory:":
            self._conn = duckdb.connect(raw)
            self._owns_connection = True
            return
        p = Path(path)
        if p.is_file() and p.suffix.lower() in (".sqlite", ".db"):
            self._sqlite_fk_path = p.resolve()
            self._attach_alias = "lumen_sqlite"
            self._conn = duckdb.connect(":memory:")
            self._owns_connection = True
            self._conn.execute("INSTALL sqlite; LOAD sqlite;")
            escaped = str(self._sqlite_fk_path).replace("'", "''")
            self._conn.execute(f"ATTACH '{escaped}' AS {self._attach_alias} (TYPE SQLITE)")
            return
        self._conn = duckdb.connect(raw)
        self._owns_connection = True

    def introspect(self) -> Schema:
        databases = self._conn.execute(
            """
            select distinct database_name
            from duckdb_columns()
            where internal = false
            """
        ).fetchall()
        if not databases:
            return Schema(tables=[])
        if self._attach_alias is not None:
            target_dbs = [self._attach_alias]
        else:
            target_dbs = [cast(str, row[0]) for row in databases]
        tables_out: list[Table] = []
        for database_name in target_dbs:
            col_rows = self._conn.execute(
                """
                select schema_name, table_name, column_name, data_type, is_nullable
                from duckdb_columns()
                where internal = false and database_name = ?
                order by table_name, column_index
                """,
                [database_name],
            ).fetchall()
            pk_rows = self._conn.execute(
                """
                select schema_name, table_name, constraint_column_names
                from duckdb_constraints()
                where database_name = ? and constraint_type = 'PRIMARY KEY'
                """,
                [database_name],
            ).fetchall()
            fk_rows = self._conn.execute(
                """
                select schema_name, table_name, constraint_column_names,
                       referenced_table, referenced_column_names
                from duckdb_constraints()
                where database_name = ? and constraint_type = 'FOREIGN KEY'
                """,
                [database_name],
            ).fetchall()
            by_table: dict[tuple[str | None, str], list[Column]] = defaultdict(list)
            pk_map: dict[tuple[str | None, str], set[str]] = defaultdict(set)
            fk_map: dict[tuple[str | None, str], list[ForeignKey]] = defaultdict(list)
            for schema_name, table_name, cols in pk_rows:
                key = (cast(str | None, schema_name), cast(str, table_name))
                names = cast(list[str], cols)
                pk_map[key].update(names)
            for schema_name, table_name, from_cols, to_table, to_cols in fk_rows:
                key = (cast(str | None, schema_name), cast(str, table_name))
                from_list = cast(list[str], from_cols)
                to_list = cast(list[str], to_cols)
                for fc, tc in zip(from_list, to_list, strict=True):
                    fk_map[key].append(
                        ForeignKey(from_column=fc, to_table=cast(str, to_table), to_column=tc)
                    )
            for schema_name, table_name, column_name, data_type, is_nullable in col_rows:
                key = (cast(str | None, schema_name), cast(str, table_name))
                nullable = cast(bool, is_nullable)
                pk_cols = pk_map.get(key, set())
                by_table[key].append(
                    Column(
                        name=cast(str, column_name),
                        data_type=cast(str, data_type),
                        nullable=nullable,
                        is_primary_key=cast(str, column_name) in pk_cols,
                    )
                )
            sorted_tables = sorted(by_table.items(), key=lambda x: x[0][1])
            for (schema_name, table_name), columns in sorted_tables:
                key_fk = (schema_name, table_name)
                if self._sqlite_fk_path is not None and not fk_map[key_fk]:
                    fk_map[key_fk] = self._sqlite_foreign_keys(table_name)
                schema_label = None if schema_name in (None, "main") else schema_name
                tables_out.append(
                    Table(
                        name=table_name,
                        schema_name=schema_label,
                        columns=columns,
                        foreign_keys=fk_map[key_fk],
                    )
                )
        return Schema(tables=tables_out)

    def _sqlite_foreign_keys(self, table_name: str) -> list[ForeignKey]:
        if self._sqlite_fk_path is None:
            return []
        con = sqlite3.connect(self._sqlite_fk_path)
        try:
            rows = con.execute(
                "select * from pragma_foreign_key_list(?)",
                (table_name,),
            ).fetchall()
        finally:
            con.close()
        out: list[ForeignKey] = []
        for row in rows:
            ref_table = cast(str, row[2])
            from_col = cast(str, row[3])
            to_col = cast(str, row[4])
            out.append(ForeignKey(from_column=from_col, to_table=ref_table, to_column=to_col))
        return out

    def execute(self, sql: str) -> list[dict[str, Any]]:
        result = self._conn.execute(sql)
        names = [d[0] for d in (result.description or ())]
        rows = result.fetchall()
        return [dict(zip(names, tuple(row), strict=True)) for row in rows]

    def close(self) -> None:
        if self._owns_connection:
            self._conn.close()

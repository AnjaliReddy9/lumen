from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


def _sqlglot_dialect(dialect: str) -> str:
    d = dialect.strip().casefold()
    if d in ("postgres", "postgresql"):
        return "postgres"
    if d in ("duckdb",):
        return "duckdb"
    if d in ("sqlite", "sqlite3"):
        return "sqlite"
    return dialect


def parse(sql: str, dialect: str) -> exp.Expr | None:
    try:
        return sqlglot.parse_one(sql, dialect=_sqlglot_dialect(dialect))
    except ParseError:
        return None

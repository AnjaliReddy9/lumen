import sqlite3
from pathlib import Path

import pytest

from lumen.validation.models import ValidationIssue
from lumen.validation.validator import SQLValidator
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse
from lumen.warehouse.schema import Schema


@pytest.fixture
def chinook_schema(tmp_path: Path) -> Schema:
    sql_path = Path(__file__).resolve().parents[1] / "fixtures" / "chinook.sql"
    db_path = tmp_path / "chinook.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql_path.read_text())
    finally:
        con.close()
    wh = DuckDBWarehouse(str(db_path))
    try:
        return wh.introspect()
    finally:
        wh.close()


def test_valid_simple_query(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT * FROM Customer", "sqlite")
    assert r.valid
    assert r.issues == []
    assert r.parsed_sql is not None


def test_unknown_table(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT * FROM Customers", "sqlite")
    assert not r.valid
    assert any(i.code == "unknown_table" for i in r.issues)


def test_unknown_column_qualified(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT Customer.Profit FROM Customer", "sqlite")
    assert not r.valid
    unk = [i for i in r.issues if i.code == "unknown_column"]
    assert unk
    assert "Available columns" in unk[0].message


def test_unknown_column_unqualified(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT Profit FROM Customer", "sqlite")
    assert not r.valid
    unk = [i for i in r.issues if i.code == "unknown_column"]
    assert unk
    assert "Available columns" in unk[0].message


def test_ambiguous_unqualified(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    sql = "SELECT FirstName FROM Customer CROSS JOIN Employee"
    r = v.validate(sql, "sqlite")
    assert not r.valid
    assert any(i.code == "ambiguous_column" for i in r.issues)


def test_alias_resolution(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT c.Country FROM Customer AS c", "sqlite")
    assert r.valid


def test_cte(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    sql = "WITH x AS (SELECT * FROM Customer) SELECT Country FROM x"
    r = v.validate(sql, "sqlite")
    assert r.valid


def test_subquery(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    sql = (
        "SELECT * FROM Customer WHERE CustomerId IN (SELECT CustomerId FROM Invoice)"
    )
    r = v.validate(sql, "sqlite")
    assert r.valid


def test_subquery_invalid(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    sql = "SELECT * FROM Customer WHERE CustomerId IN (SELECT BadCol FROM Invoice)"
    r = v.validate(sql, "sqlite")
    assert not r.valid
    assert any(i.code == "unknown_column" for i in r.issues)


def test_syntax_error(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT FROM", "sqlite")
    assert not r.valid
    assert any(i.code == "syntax_error" for i in r.issues)


def test_multiple_issues(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT Bad1, Bad2 FROM Customer", "sqlite")
    assert not r.valid
    unk = [i for i in r.issues if i.code == "unknown_column"]
    assert len(unk) >= 2


def test_unknown_table_and_column_together(chinook_schema) -> None:
    v = SQLValidator(chinook_schema)
    r = v.validate("SELECT Nope FROM NotATable", "sqlite")
    assert not r.valid
    codes = {i.code for i in r.issues}
    assert "unknown_table" in codes
    assert "unknown_column" in codes


def test_issue_model() -> None:
    i = ValidationIssue(
        severity="error",
        code="syntax_error",
        message="m",
        table=None,
        column=None,
    )
    assert i.code == "syntax_error"

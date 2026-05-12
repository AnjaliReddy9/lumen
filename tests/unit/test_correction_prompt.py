import sqlite3
from pathlib import Path

from lumen.generation.prompt import build_correction_prompt
from lumen.semantic.loader import load_semantic_model
from lumen.validation.models import ValidationIssue
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def _chinook_schema(tmp_path: Path):
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


def test_correction_prompt_includes_question_and_hints(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    schema = _chinook_schema(tmp_path)
    q = "What is profit by region?"
    issues = [
        ValidationIssue(
            severity="error",
            code="unknown_column",
            message=(
                "Column 'Profit' does not exist on 'Customer'. "
                "Available columns on Customer: CustomerId, FirstName, LastName."
            ),
            table="Customer",
            column="Profit",
        )
    ]
    prev = "SELECT Profit FROM Customer"
    system, user = build_correction_prompt(q, prev, issues, model, schema, "sqlite")
    combined = system + "\n" + user
    assert q in user
    assert prev in user
    assert "unknown_column" in user
    assert "Available columns on Customer" in user
    assert "Profit" in user
    assert "sqlite" in system.lower()
    assert len(combined) < 8000


def test_correction_prompt_lists_each_unknown_column_issue(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    schema = _chinook_schema(tmp_path)
    issues = [
        ValidationIssue(
            severity="error",
            code="unknown_column",
            message=(
                "Column 'Foo' does not exist on 'Invoice'. "
                "Available columns on Invoice: Total."
            ),
            table="Invoice",
            column="Foo",
        ),
        ValidationIssue(
            severity="error",
            code="unknown_column",
            message=(
                "Column 'Bar' does not exist on 'Invoice'. "
                "Available columns on Invoice: Total."
            ),
            table="Invoice",
            column="Bar",
        ),
    ]
    _, user = build_correction_prompt("q", "SELECT 1", issues, model, schema, "sqlite")
    assert "Foo" in user and "Bar" in user
    assert user.count("Available columns on Invoice") >= 2

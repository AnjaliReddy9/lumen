import sqlite3
from pathlib import Path

from lumen.generation.prompt import build_sql_prompt
from lumen.semantic.loader import load_semantic_model
from lumen.semantic.models import Dimension, Entity, Measure, Metric, SemanticModel
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse
from lumen.warehouse.schema import Column, Schema, Table


def _chinook_sqlite(tmp_path: Path) -> Path:
    sql_path = Path(__file__).resolve().parents[1] / "fixtures" / "chinook.sql"
    db_path = tmp_path / "chinook.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql_path.read_text())
    finally:
        con.close()
    return db_path


def test_prompt_contains_expected_fragments(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    db = _chinook_sqlite(tmp_path)
    wh = DuckDBWarehouse(db)
    try:
        schema = wh.introspect()
    finally:
        wh.close()
    question = "What is the total revenue by country?"
    system, user = build_sql_prompt(question, model, schema, "sqlite")
    combined = system + "\n" + user
    assert "sqlite" in combined.lower()
    assert question in user
    assert "total_revenue" in user
    assert "entity: invoice" in user or "invoice" in user
    assert "=== WAREHOUSE SCHEMA" in user
    assert "table Invoice" in user


def test_prompt_length_chinook_under_budget(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    db = _chinook_sqlite(tmp_path)
    wh = DuckDBWarehouse(db)
    try:
        schema = wh.introspect()
    finally:
        wh.close()
    system, user = build_sql_prompt("x", model, schema, "sqlite")
    assert len(system) + len(user) < 8000


def test_prompt_includes_metric_measure_line() -> None:
    model = SemanticModel(
        entities=[
            Entity(
                name="e",
                table="T",
                primary_key="id",
                dimensions=[Dimension(name="d", column="c")],
            )
        ],
        metrics=[
            Metric(
                name="m1",
                type="simple",
                entity="e",
                measure=Measure(expression="v", aggregation="sum"),
                dimensions=["d"],
            )
        ],
        relationships=[],
    )
    schema = Schema(
        tables=[
            Table(
                name="T",
                schema_name=None,
                columns=[Column(name="id", data_type="int", nullable=False, is_primary_key=True)],
                foreign_keys=[],
            )
        ]
    )
    _, user = build_sql_prompt("q?", model, schema, "duckdb")
    assert "sum(v)" in user

from pathlib import Path

from lumen.interpretation.prompt import build_interpretation_prompt
from lumen.semantic.loader import load_semantic_model
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def _schema(tmp_path: Path):
    import sqlite3

    sql_path = Path(__file__).resolve().parents[1] / "fixtures" / "chinook.sql"
    db_path = tmp_path / "c.sqlite"
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


def test_interpretation_prompt_includes_question_semantic_dialect(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    schema = _schema(tmp_path)
    q = "Top customers in California"
    system, user = build_interpretation_prompt(q, model, schema, "sqlite")
    combined = system + "\n" + user
    assert q in user
    assert "sqlite" in combined.lower()
    assert "=== SEMANTIC MODEL ===" in user
    assert "JSON" in system or "json" in combined.lower()
    assert "submit_interpretation" in system
    assert "=== WAREHOUSE SCHEMA" in user


def test_interpretation_prompt_includes_resolutions(tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    schema = _schema(tmp_path)
    _, user = build_interpretation_prompt(
        "q", model, schema, "sqlite", resolutions={"Which state?": "California"}
    )
    assert "USER RESOLUTIONS" in user
    assert "California" in user

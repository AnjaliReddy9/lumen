import sqlite3
from pathlib import Path

import pytest

from lumen.semantic.loader import load_semantic_model
from lumen.semantic.validator import validate_semantic_model
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


@pytest.fixture()
def chinook_sqlite(tmp_path: Path) -> Path:
    sql_path = Path(__file__).resolve().parents[1] / "fixtures" / "chinook.sql"
    db_path = tmp_path / "chinook.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql_path.read_text())
    finally:
        con.close()
    return db_path


def test_chinook_semantic_validates_against_warehouse(chinook_sqlite: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    model = load_semantic_model(semantic_dir)
    wh = DuckDBWarehouse(chinook_sqlite)
    try:
        schema = wh.introspect()
        validate_semantic_model(model, schema)
    finally:
        wh.close()

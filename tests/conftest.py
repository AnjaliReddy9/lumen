import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def chinook_sqlite(tmp_path: Path) -> Path:
    sql_path = Path(__file__).resolve().parent / "fixtures" / "chinook.sql"
    db_path = tmp_path / "chinook.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql_path.read_text())
    finally:
        con.close()
    return db_path

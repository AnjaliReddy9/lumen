import sqlite3
from pathlib import Path

import pytest

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


def test_chinook_introspection(chinook_sqlite: Path) -> None:
    wh = DuckDBWarehouse(chinook_sqlite)
    try:
        schema = wh.introspect()
    finally:
        wh.close()
    assert len(schema.tables) == 11
    artist = schema.find_table("Artist")
    assert artist is not None
    assert any(c.name == "ArtistId" and c.is_primary_key for c in artist.columns)
    album = schema.find_table("Album")
    assert album is not None
    links = {(fk.from_column, fk.to_table, fk.to_column) for fk in album.foreign_keys}
    assert ("ArtistId", "Artist", "ArtistId") in links

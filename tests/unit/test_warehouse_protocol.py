import duckdb

from lumen.warehouse.base import Warehouse
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def test_duckdb_warehouse_isinstance_warehouse() -> None:
    wh = DuckDBWarehouse(":memory:")
    try:
        assert isinstance(wh, Warehouse)
    finally:
        wh.close()


def test_duckdb_warehouse_runtime_checkable() -> None:
    def takes_warehouse(w: Warehouse) -> None:
        w.close()

    wh = DuckDBWarehouse(":memory:")
    takes_warehouse(wh)


def test_duckdb_not_warehouse() -> None:
    assert not isinstance(duckdb.connect(":memory:"), Warehouse)

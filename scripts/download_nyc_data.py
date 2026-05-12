#!/usr/bin/env python3
"""Download / build NYC Open Data benchmark warehouse (DuckDB) and semantic YAML.

Default mode is offline: creates reproducible local tables and sample rows.
Pass ``--live`` for a best-effort pull from NYC Open Data (Socrata) — requires network.

Writes:
  - benchmarks/datasets/nyc_open_data/warehouse.duckdb
  - benchmarks/datasets/nyc_open_data/semantic/{entities,metrics,relationships.yaml}
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "benchmarks" / "datasets" / "nyc_open_data" / "semantic"
DB_PATH = ROOT / "benchmarks" / "datasets" / "nyc_open_data" / "warehouse.duckdb"

# (table_name, create_column_spec_without_id)
THEMED: list[tuple[str, str, list[dict[str, str]]]] = [
    (
        "nyc_311_requests",
        "borough VARCHAR, complaint_type VARCHAR, created_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_building_permits",
        "borough VARCHAR, job_type VARCHAR, filing_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_school_results",
        "district VARCHAR, subject VARCHAR, score DOUBLE",
        [{"name": "district", "column": "district"}],
    ),
    (
        "nyc_restaurant_inspections",
        "borough VARCHAR, grade VARCHAR, inspection_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_vehicle_crashes",
        "borough VARCHAR, persons_injured INTEGER, crash_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_street_trees",
        "borough VARCHAR, species VARCHAR, tree_dbh DOUBLE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_citibike_rides",
        "borough VARCHAR, ride_minutes INTEGER, start_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_air_quality",
        "borough VARCHAR, pollutant VARCHAR, value DOUBLE, day DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_housing_violations",
        "borough VARCHAR, violation_class VARCHAR, opened_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
    (
        "nyc_film_permits",
        "borough VARCHAR, event_type VARCHAR, start_date DATE",
        [{"name": "borough", "column": "borough"}],
    ),
]


def _write_semantic(num_tables: int) -> None:
    entities_dir = SEM / "entities"
    metrics_dir = SEM / "metrics"
    entities_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    (SEM / "relationships.yaml").write_text("relationships: []\n", encoding="utf-8")

    entities: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for i in range(num_tables):
        if i < len(THEMED):
            tname, _spec, dims = THEMED[i]
        else:
            tname = f"nyc_catalog_{i:03d}"
            dims = [{"name": "borough", "column": "borough"}]
        entities.append(
            {
                "name": f"entity_{tname}",
                "description": f"Semantic entity for {tname}",
                "table": tname,
                "primary_key": "id",
                "dimensions": dims,
            }
        )
        metrics.append(
            {
                "name": f"rowcount_{tname}",
                "type": "simple",
                "entity": f"entity_{tname}",
                "measure": {"expression": "1", "aggregation": "count"},
                "dimensions": [],
            }
        )

    (entities_dir / "nyc_entities.yaml").write_text(
        yaml.safe_dump(entities, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (metrics_dir / "nyc_metrics.yaml").write_text(
        yaml.safe_dump(metrics, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _insert_themed(con: Any, i: int, tname: str) -> None:
    boro = ("MN", "BK", "QN", "BX", "SI")[i % 5]
    if "311" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'Noise', '2024-01-01'),"
            f"(2, 'BK', 'Heat', '2024-02-01'),"
            f"(3, 'QN', 'Noise', '2024-03-01')"
        )
    elif "permits" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'NB', '2024-01-10'),"
            "(2, 'MN', 'ALT', '2024-02-10'),"
            "(3, 'BK', 'NB', '2024-03-10')"
        )
    elif "school" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            "(1, 'D2', 'Math', 82.0),"
            "(2, 'D3', 'ELA', 77.5),"
            "(3, 'D2', 'ELA', 80.0)"
        )
    elif "restaurant" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'A', '2024-01-05'),"
            "(2, 'MN', 'B', '2024-02-05'),"
            "(3, 'BK', 'A', '2024-03-05')"
        )
    elif "vehicle" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 0, '2024-01-02'),"
            "(2, 'BK', 2, '2024-02-02'),"
            "(3, 'MN', 1, '2024-03-02')"
        )
    elif "trees" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'Oak', 12.0),"
            "(2, 'BK', 'Maple', 8.0),"
            "(3, 'MN', 'Oak', 20.0)"
        )
    elif "citibike" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 15, '2024-01-03'),"
            "(2, 'MN', 22, '2024-02-03'),"
            "(3, 'BK', 10, '2024-03-03')"
        )
    elif "air" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'PM2.5', 35.0, '2024-01-04'),"
            "(2, 'MN', 'O3', 0.04, '2024-02-04'),"
            "(3, 'BK', 'PM2.5', 28.0, '2024-03-04')"
        )
    elif "housing" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'C', '2024-01-06'),"
            "(2, 'BK', 'B', '2024-02-06'),"
            "(3, 'MN', 'C', '2024-03-06')"
        )
    elif "film" in tname:
        con.execute(
            f"INSERT INTO {tname} VALUES "
            f"(1, '{boro}', 'Shoot', '2024-01-07'),"
            "(2, 'MN', 'Park', '2024-02-07'),"
            "(3, 'BK', 'Shoot', '2024-03-07')"
        )


def _build_duckdb(num_tables: int, live: bool) -> None:
    import duckdb

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    try:
        for i in range(num_tables):
            if i < len(THEMED):
                tname, colspec, _dims = THEMED[i]
                ddl = f"CREATE TABLE {tname} (id INTEGER PRIMARY KEY, {colspec})"
                con.execute(ddl)
                _insert_themed(con, i, tname)
            else:
                tname = f"nyc_catalog_{i:03d}"
                ddl = (
                    f"CREATE TABLE {tname} "
                    "(id INTEGER PRIMARY KEY, borough VARCHAR, v DOUBLE, d DATE)"
                )
                con.execute(ddl)
                con.execute(
                    f"INSERT INTO {tname} VALUES "
                    "(1, 'MN', 1.0, '2024-01-01'),"
                    "(2, 'BK', 2.0, '2024-02-01'),"
                    "(3, 'QN', 3.0, '2024-03-01')"
                )
        if live:
            try:
                import urllib.request

                url = (
                    "https://data.cityofnewyork.us/resource/erm2-nwe9.csv?"
                    "$select=unique_key,borough,complaint_type&$limit=100"
                )
                req = urllib.request.Request(url, headers={"User-Agent": "lumen-benchmark/1"})
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                    raw = resp.read()
                p = DB_PATH.parent / "_311_sample.csv"
                p.write_bytes(raw)
                esc = str(p.resolve()).replace("'", "''")
                con.execute(f"CREATE TABLE nyc_311_live AS SELECT * FROM read_csv_auto('{esc}')")
            except Exception as exc:
                print(f"live download skipped: {exc}", file=sys.stderr)
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", type=int, default=52, help="number of physical tables (>=10)")
    ap.add_argument("--live", action="store_true", help="best-effort Socrata CSV pull")
    args = ap.parse_args()
    num = max(10, min(args.tables, 120))
    _build_duckdb(num, args.live)
    _write_semantic(num)
    print(f"wrote {DB_PATH} and semantic under {SEM}")


if __name__ == "__main__":
    main()

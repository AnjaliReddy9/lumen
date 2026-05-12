from lumen.generation.generator import GeneratedSQL
from lumen.generation.runner import run_generated_sql
from lumen.validation.models import ValidationResult
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def test_runner_success_path() -> None:
    wh = DuckDBWarehouse(":memory:")
    try:
        wh.execute("create table t(a int); insert into t values (1),(2);")
        gen = GeneratedSQL(
            question="q",
            sql="select sum(a) as s from t",
            dialect="duckdb",
            raw_response="",
            validation=ValidationResult(valid=True, issues=[], parsed_sql=None),
            attempts=1,
        )
        res = run_generated_sql(gen, wh)
        assert res.error is None
        assert res.row_count == 1
        assert res.rows[0]["s"] == 3
    finally:
        wh.close()


def test_runner_captures_execution_error() -> None:
    wh = DuckDBWarehouse(":memory:")
    try:
        gen = GeneratedSQL(
            question="q",
            sql="select * from does_not_exist",
            dialect="duckdb",
            raw_response="",
            validation=ValidationResult(valid=True, issues=[], parsed_sql=None),
            attempts=1,
        )
        res = run_generated_sql(gen, wh)
        assert res.error is not None
        assert res.row_count == 0
        assert res.rows == []
    finally:
        wh.close()

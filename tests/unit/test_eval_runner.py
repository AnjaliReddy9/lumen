from pathlib import Path

import pytest

from lumen.eval.fake_provider import EvalGroundTruthFakeProvider
from lumen.eval.models import EvalCase, EvalConfig
from lumen.eval.runner import EvalRunner
from lumen.generation.generator import SQLGenerator
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.semantic.models import Dimension, Entity, SemanticModel
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse
from lumen.warehouse.schema import Column, Schema, Table


@pytest.fixture()
def tiny_semantic_and_schema() -> tuple[SemanticModel, Schema]:
    model = SemanticModel(
        entities=[
            Entity(
                name="widget",
                table="widgets",
                primary_key="id",
                dimensions=[Dimension(name="color", column="color")],
            )
        ],
        metrics=[],
        relationships=[],
    )
    schema = Schema(
        tables=[
            Table(
                name="widgets",
                schema_name=None,
                columns=[
                    Column(name="id", data_type="INTEGER", nullable=False, is_primary_key=True),
                    Column(name="color", data_type="VARCHAR", nullable=True, is_primary_key=False),
                ],
                foreign_keys=[],
            )
        ]
    )
    return model, schema


def test_eval_runner_shape(
    tiny_semantic_and_schema: tuple[SemanticModel, Schema], tmp_path: Path
) -> None:
    model, schema = tiny_semantic_and_schema
    wh = DuckDBWarehouse(":memory:")
    wh.execute("CREATE TABLE widgets (id INTEGER PRIMARY KEY, color VARCHAR);")
    wh.execute("INSERT INTO widgets VALUES (1, 'red'), (2, 'blue');")
    cases = [
        EvalCase(
            case_id="e1",
            question="How many widgets?",
            expected_sql="SELECT COUNT(*) AS n FROM widgets",
            expected_rows=[{"n": 2}],
            database="mem",
            dialect="duckdb",
            tags=["unit"],
        ),
    ]
    mapping = {cases[0].question: cases[0].expected_sql or "SELECT 1"}
    fake = EvalGroundTruthFakeProvider(mapping)
    gen = SQLGenerator(fake, max_retries=0, interpreter=QueryInterpreter(fake))
    runner = EvalRunner(gen, wh)
    cfg = EvalConfig(
        use_interpretation=False,
        max_retries=0,
        max_concurrency=1,
        max_cost_usd=100.0,
        sample_size=None,
    )
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run = runner.run(
        cases,
        cfg,
        semantic_model=model,
        schema=schema,
        dialect="duckdb",
        benchmark="unit",
        model_name="fake",
        run_id="unit-test-run",
        checkpoint_dir=runs_dir,
    )
    wh.close()
    assert run.cases_completed == 1
    assert run.results[0].generated_sql is not None
    assert run.cases_total == 1
    assert run.results[0].execution_accuracy is True
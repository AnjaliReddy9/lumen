from pathlib import Path

from lumen.eval.benchmarks.chinook import load_chinook_eval_cases
from lumen.eval.fake_provider import EvalGroundTruthFakeProvider
from lumen.eval.models import EvalConfig
from lumen.eval.runner import EvalRunner
from lumen.generation.generator import SQLGenerator
from lumen.interpretation.interpreter import QueryInterpreter
from lumen.semantic.loader import load_semantic_model
from lumen.semantic.validator import validate_semantic_model
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def test_eval_chinook_execution_accuracy(chinook_sqlite: Path, tmp_path: Path) -> None:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    cases = load_chinook_eval_cases()
    mapping = {c.question.strip(): c.expected_sql for c in cases if c.expected_sql}
    fake = EvalGroundTruthFakeProvider(mapping)
    gen = SQLGenerator(fake, max_retries=0, interpreter=QueryInterpreter(fake))
    wh = DuckDBWarehouse(chinook_sqlite)
    model = load_semantic_model(semantic_dir)
    schema = wh.introspect()
    validate_semantic_model(model, schema)
    cfg = EvalConfig(
        use_interpretation=False,
        max_retries=0,
        max_concurrency=1,
        max_cost_usd=100.0,
        sample_size=3,
    )
    runner = EvalRunner(gen, wh)
    run = runner.run(
        cases,
        cfg,
        semantic_model=model,
        schema=schema,
        dialect="sqlite",
        benchmark="chinook",
        model_name="fake",
        run_id="chinook-integration",
        checkpoint_dir=tmp_path,
    )
    wh.close()
    assert run.cases_completed == 3
    assert run.summary.execution_accuracy == 1.0

import importlib
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient


def _reload_app() -> Any:
    from lumen.api import app as app_mod
    from lumen.api import deps as deps_mod

    deps_mod.clear_singleton_caches()
    deps_mod.get_settings.cache_clear()
    importlib.reload(deps_mod)
    deps_mod.get_settings.cache_clear()
    importlib.reload(app_mod)
    return app_mod.app


@pytest.fixture()
def api_env(monkeypatch: pytest.MonkeyPatch, chinook_sqlite: Path, tmp_path: Path) -> Path:
    semantic_dir = Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-for-api-tests")
    monkeypatch.setenv("LUMEN_SEMANTIC_DIR", str(semantic_dir.resolve()))
    monkeypatch.setenv("LUMEN_WAREHOUSE_PATH", str(chinook_sqlite))
    monkeypatch.setenv("LUMEN_WAREHOUSE_TYPE", "duckdb")
    monkeypatch.setenv("LUMEN_DIALECT", "sqlite")
    monkeypatch.setenv("LUMEN_EVAL_RUNS_DIR", str(runs_dir))
    from lumen.api.deps import clear_singleton_caches, get_settings

    clear_singleton_caches()
    get_settings.cache_clear()
    return runs_dir


def test_health_and_ready(api_env: Path) -> None:
    app = _reload_app()
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready").json()
    assert ready["status"] == "ok"


def test_schema_endpoints(api_env: Path) -> None:
    app = _reload_app()
    client = TestClient(app)
    assert client.get("/schema").status_code == 200
    assert client.get("/semantic").status_code == 200


def test_query_requires_body(api_env: Path) -> None:
    app = _reload_app()
    client = TestClient(app)
    assert client.post("/query", json={}).status_code == 422


def test_eval_runs_listing(api_env: Path) -> None:
    from datetime import datetime

    from lumen.eval.models import EvalResult, EvalRun, EvalSummary

    summary = EvalSummary(
        execution_accuracy=1.0,
        validation_pass_rate=1.0,
        generation_success_rate=1.0,
        avg_latency_ms=1,
        total_cost_usd=0.0,
        by_difficulty=None,
    )
    run = EvalRun(
        run_id="sample-run",
        benchmark="chinook",
        model="fake",
        config={},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        cases_total=1,
        cases_completed=1,
        results=[
            EvalResult(
                case_id="c1",
                question="q",
                generated_sql="SELECT 1",
                validation_valid=True,
                validation_issues=[],
                attempts=1,
                latency_ms=1,
                cost_usd=0.0,
                execution_accuracy=True,
            )
        ],
        summary=summary,
    )
    (api_env / "sample-run.json").write_text(run.model_dump_json(), encoding="utf-8")

    app = _reload_app()
    client = TestClient(app)
    lst = client.get("/eval/runs")
    assert lst.status_code == 200
    assert (api_env / "sample-run.json").is_file()
    assert isinstance(lst.json(), list)

import json
from datetime import UTC, datetime

from lumen.eval.models import EvalCase, EvalResult, EvalRun, EvalSummary
from lumen.validation.models import ValidationIssue


def test_eval_case_roundtrip() -> None:
    c = EvalCase(
        case_id="c1",
        question="q",
        expected_sql="SELECT 1",
        database="db",
        dialect="sqlite",
        difficulty="easy",
        tags=["t"],
    )
    d = json.loads(c.model_dump_json())
    c2 = EvalCase.model_validate(d)
    assert c2.case_id == "c1"


def test_eval_run_roundtrip() -> None:
    summary = EvalSummary(
        execution_accuracy=1.0,
        validation_pass_rate=1.0,
        generation_success_rate=1.0,
        avg_latency_ms=10,
        total_cost_usd=0.01,
        by_difficulty=None,
    )
    r = EvalRun(
        run_id="rid",
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
                latency_ms=5,
                cost_usd=0.0,
                execution_accuracy=True,
            )
        ],
        summary=summary,
    )
    r2 = EvalRun.model_validate_json(r.model_dump_json())
    assert r2.run_id == "rid"


def test_validation_issue_embedded() -> None:
    issue = ValidationIssue(
        severity="error", code="unknown_table", message="m", table="T", column=None
    )
    er = EvalResult(case_id="x", question="q", validation_issues=[issue])
    er2 = EvalResult.model_validate_json(er.model_dump_json())
    assert er2.validation_issues[0].code == "unknown_table"

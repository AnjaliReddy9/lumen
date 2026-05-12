from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from lumen.validation.models import ValidationIssue


class EvalCase(BaseModel):
    case_id: str
    question: str
    expected_sql: str | None = None
    expected_rows: list[dict[str, Any]] | None = None
    database: str
    dialect: str
    difficulty: Literal["easy", "medium", "hard", "extra"] | None = None
    tags: list[str] = Field(default_factory=list)


class EvalSummary(BaseModel):
    execution_accuracy: float
    validation_pass_rate: float
    generation_success_rate: float
    avg_latency_ms: int
    total_cost_usd: float
    by_difficulty: dict[str, EvalSummary] | None = None


class EvalResult(BaseModel):
    case_id: str
    question: str
    difficulty: Literal["easy", "medium", "hard", "extra"] | None = None
    generated_sql: str | None = None
    executed_rows: list[dict[str, Any]] | None = None
    validation_valid: bool = False
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    interpretation_summary: str | None = None
    attempts: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    execution_accuracy: bool | None = None
    error: str | None = None


class EvalRun(BaseModel):
    run_id: str
    benchmark: str
    model: str
    config: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None = None
    cases_total: int = 0
    cases_completed: int = 0
    results: list[EvalResult] = Field(default_factory=list)
    summary: EvalSummary


class EvalConfig(BaseModel):
    use_interpretation: bool = True
    max_retries: int = 2
    max_concurrency: int = 4
    max_cost_usd: float = 10.0
    sample_size: int | None = None
    skip_validation: bool = False

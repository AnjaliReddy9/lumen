from typing import Literal

from pydantic import BaseModel


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: Literal[
        "syntax_error",
        "unknown_table",
        "unknown_column",
        "ambiguous_column",
        "unqualified_column",
    ]
    message: str
    table: str | None = None
    column: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue]
    parsed_sql: str | None

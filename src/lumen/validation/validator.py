from __future__ import annotations

from typing import Literal

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from sqlglot.optimizer.scope import Scope, traverse_scope

from lumen.validation.models import ValidationIssue, ValidationResult
from lumen.validation.parser import _sqlglot_dialect, parse
from lumen.warehouse.schema import Schema
from lumen.warehouse.schema import Table as SchemaTable

_ERR_SEV: Literal["error"] = "error"


def _parse_syntax_detail(sql: str, dialect: str) -> str:
    try:
        sqlglot.parse_one(sql, dialect=_sqlglot_dialect(dialect))
    except ParseError as e:
        return str(e)
    return "could not parse SQL"


def _nearest_select(node: exp.Expr | None) -> exp.Select | None:
    n: exp.Expr | None = node
    while n and not isinstance(n, exp.Select):
        n = n.parent
    return n if isinstance(n, exp.Select) else None


def _own_columns(scope: Scope) -> list[exp.Column]:
    sel = scope.expression
    if not isinstance(sel, exp.Select):
        return []
    return [c for c in scope.columns if _nearest_select(c) is sel]


def _is_select_statement(root: exp.Expr) -> bool:
    unnest = root.unnest()
    return isinstance(unnest, (exp.Select, exp.Union))


def _source_is_derived(scope: Scope, table: exp.Table) -> bool:
    key = table.alias_or_name
    src = scope.sources.get(key)
    return isinstance(src, Scope)


def _schema_table_columns(tbl: SchemaTable) -> set[str]:
    return {c.name for c in tbl.columns}


def _available_columns_message(tbl: SchemaTable) -> str:
    names = sorted(c.name for c in tbl.columns)
    return ", ".join(names)


class SQLValidator:
    def __init__(self, schema: Schema) -> None:
        self._schema = schema

    def validate(self, sql: str, dialect: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        ast = parse(sql, dialect)
        if ast is None:
            detail = _parse_syntax_detail(sql, dialect)
            issues.append(
                ValidationIssue(
                    severity=_ERR_SEV,
                    code="syntax_error",
                    message=f"SQL could not be parsed: {detail}",
                    table=None,
                    column=None,
                )
            )
            return ValidationResult(valid=False, issues=issues, parsed_sql=None)

        root = ast.unnest()
        read_dialect = _sqlglot_dialect(dialect)
        parsed_sql = root.sql(dialect=read_dialect)

        if not _is_select_statement(root):
            issues.append(
                ValidationIssue(
                    severity=_ERR_SEV,
                    code="syntax_error",
                    message="Only SELECT (including WITH and UNION) queries are supported.",
                    table=None,
                    column=None,
                )
            )
            return ValidationResult(valid=False, issues=issues, parsed_sql=parsed_sql)

        for scope in traverse_scope(ast):
            if not isinstance(scope.expression, exp.Select):
                continue
            self._validate_physical_tables(scope, issues)
            self._validate_columns(scope, issues)

        has_error = any(i.severity == "error" for i in issues)
        return ValidationResult(valid=not has_error, issues=issues, parsed_sql=parsed_sql)

    def _validate_physical_tables(self, scope: Scope, issues: list[ValidationIssue]) -> None:
        for table in scope.tables:
            if _source_is_derived(scope, table):
                continue
            name = table.name
            if self._schema.find_table(name) is None:
                issues.append(
                    ValidationIssue(
                        severity=_ERR_SEV,
                        code="unknown_table",
                        message=f"Table '{name}' is not present in the warehouse schema.",
                        table=name,
                        column=None,
                    )
                )

    def _validate_columns(self, scope: Scope, issues: list[ValidationIssue]) -> None:
        for col in _own_columns(scope):
            qual = col.text("table")
            name = col.name
            if not name:
                continue
            if qual:
                self._check_qualified(scope, qual, name, issues)
            else:
                self._check_unqualified(scope, name, issues)

    def _check_qualified(
        self, scope: Scope, qual: str, col_name: str, issues: list[ValidationIssue]
    ) -> None:
        if qual not in scope.selected_sources:
            issues.append(
                ValidationIssue(
                    severity=_ERR_SEV,
                    code="unknown_column",
                    message=(
                        f"Column '{qual}.{col_name}': unknown table or alias '{qual}' in this "
                        "SELECT scope."
                    ),
                    table=qual,
                    column=col_name,
                )
            )
            return

        cols = self._columns_for_selected_source(scope, qual, issues)
        if cols is None:
            return
        if col_name not in cols:
            phys = self._physical_name_for_qualifier(scope, qual)
            extra = ""
            if phys and (st := self._schema.find_table(phys)):
                extra = f" Available columns on {st.name}: {_available_columns_message(st)}."
            issues.append(
                ValidationIssue(
                    severity=_ERR_SEV,
                    code="unknown_column",
                    message=f"Column '{col_name}' does not exist on '{qual}'.{extra}",
                    table=qual,
                    column=col_name,
                )
            )

    def _physical_name_for_qualifier(self, scope: Scope, qual: str) -> str | None:
        if qual not in scope.selected_sources:
            return None
        _, src = scope.selected_sources[qual]
        if isinstance(src, exp.Table):
            return src.name
        if isinstance(src, Scope):
            return None
        return None

    def _check_unqualified(
        self, scope: Scope, col_name: str, issues: list[ValidationIssue]
    ) -> None:
        candidates: list[str] = []
        for src_name in scope.selected_sources:
            cols = self._columns_for_selected_source(scope, src_name, issues)
            if cols is not None and col_name in cols:
                candidates.append(src_name)

        if len(candidates) == 1:
            return
        if len(candidates) > 1:
            issues.append(
                ValidationIssue(
                    severity=_ERR_SEV,
                    code="ambiguous_column",
                    message=(
                        f"Column '{col_name}' is ambiguous; it exists on multiple sources in "
                        f"this scope: {', '.join(sorted(candidates))}."
                    ),
                    table=None,
                    column=col_name,
                )
            )
            return

        ref_tables = [sn for sn, _ in scope.selected_sources.items()]
        hint_tables: list[SchemaTable] = []
        for sn in ref_tables:
            phys = self._physical_name_for_qualifier(scope, sn)
            if phys and (st := self._schema.find_table(phys)):
                hint_tables.append(st)
        if len(hint_tables) == 1:
            st = hint_tables[0]
            extra = f" Available columns on {st.name}: {_available_columns_message(st)}."
        elif hint_tables:
            parts = [
                f"{t.name}: {_available_columns_message(t)}"
                for t in sorted(hint_tables, key=lambda x: x.name)
            ]
            extra = " Available columns: " + "; ".join(parts) + "."
        else:
            extra = ""
        issues.append(
            ValidationIssue(
                severity=_ERR_SEV,
                code="unknown_column",
                message=f"Column '{col_name}' does not exist on any referenced table.{extra}",
                table=None,
                column=col_name,
            )
        )

    def _columns_for_selected_source(
        self, scope: Scope, source_name: str, issues: list[ValidationIssue]
    ) -> set[str] | None:
        if source_name not in scope.selected_sources:
            return set()
        _, src = scope.selected_sources[source_name]
        if isinstance(src, exp.Table):
            st = self._schema.find_table(src.name)
            if st is None:
                return None
            return _schema_table_columns(st)
        if isinstance(src, Scope):
            return self._output_columns_for_derived_scope(src, issues)
        return set()

    def _output_columns_for_derived_scope(
        self, derived: Scope, issues: list[ValidationIssue]
    ) -> set[str] | None:
        inner = derived.expression
        if not isinstance(inner, exp.Select):
            return set()
        names: set[str] = set()
        for proj in inner.expressions:
            if isinstance(proj, exp.Alias):
                names.add(proj.alias)
                continue
            if isinstance(proj, exp.Column) and isinstance(proj.this, exp.Star):
                tbl = proj.text("table")
                if tbl:
                    cols = self._columns_for_selected_source(derived, tbl, issues)
                    if cols is None:
                        return None
                    names |= cols
                else:
                    for sn, _ in derived.selected_sources.items():
                        part = self._columns_for_selected_source(derived, sn, issues)
                        if part is None:
                            return None
                        names |= part
                continue
            if isinstance(proj, exp.Star):
                for sn, _ in derived.selected_sources.items():
                    part = self._columns_for_selected_source(derived, sn, issues)
                    if part is None:
                        return None
                    names |= part
                continue
            if isinstance(proj, exp.Column):
                names.add(proj.name)
                continue
            alias = proj.args.get("alias")
            if isinstance(alias, str):
                names.add(alias)
            elif isinstance(alias, exp.Identifier):
                names.add(alias.this)
        return names

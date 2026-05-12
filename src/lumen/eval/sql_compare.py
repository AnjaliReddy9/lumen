"""Structural SQL comparison for eval (approximate; AST normalization caveats apply)."""

from __future__ import annotations

import sqlglot


def structural_sql_equivalent(
    sql_a: str,
    sql_b: str,
    dialect: str,
) -> bool:
    try:
        a = sqlglot.parse_one(sql_a, read=dialect)
        b = sqlglot.parse_one(sql_b, read=dialect)
    except Exception:
        return False
    try:
        return a.sql(dialect=dialect, normalize=True) == b.sql(dialect=dialect, normalize=True)
    except Exception:
        return False


def sql_matches_expected_pattern(generated: str, expected_pattern: str, dialect: str) -> bool:
    """True if generated SQL is structurally equivalent OR expected appears as a substring.

    NYC benchmark uses hand-written patterns; substring allows ``SELECT ... COUNT`` style hints.
    """
    gen_st = generated.strip()
    exp_st = expected_pattern.strip()
    if not gen_st or not exp_st:
        return False
    if exp_st.upper() in gen_st.upper():
        return True
    return structural_sql_equivalent(gen_st, exp_st, dialect)

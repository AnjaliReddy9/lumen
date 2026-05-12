from lumen.validation.parser import parse


def test_parse_returns_none_on_syntax_error() -> None:
    assert parse("SELECT FROM", "sqlite") is None


def test_parse_returns_ast_for_valid_select() -> None:
    ast = parse("SELECT 1 AS n", "sqlite")
    assert ast is not None
    assert "1" in ast.sql()

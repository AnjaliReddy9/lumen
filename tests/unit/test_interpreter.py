import sqlite3
from pathlib import Path
from typing import Any

from lumen.interpretation.interpreter import QueryInterpreter
from lumen.semantic.loader import load_semantic_model
from lumen.warehouse.duckdb_warehouse import DuckDBWarehouse


def _schema_model(tmp_path: Path):
    sql_path = Path(__file__).resolve().parents[1] / "fixtures" / "chinook.sql"
    db_path = tmp_path / "c.sqlite"
    con = sqlite3.connect(db_path)
    try:
        con.executescript(sql_path.read_text())
    finally:
        con.close()
    wh = DuckDBWarehouse(str(db_path))
    try:
        return wh.introspect(), load_semantic_model(
            Path(__file__).resolve().parents[1] / "fixtures" / "chinook_semantic"
        )
    finally:
        wh.close()


def _valid_tool_payload() -> dict[str, Any]:
    return {
        "confidence": "high",
        "intent": {
            "question": "How many tracks?",
            "intent_summary": "Count tracks per genre",
            "entities_referenced": ["track"],
            "metrics_referenced": [],
            "dimensions_referenced": ["genre"],
            "time_grain": None,
            "filters": [],
            "sort": None,
            "limit": None,
        },
        "ambiguities": [],
    }


class _FakeToolClient:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = list(payloads)
        self.calls = 0

    def call_tool_use(
        self,
        *,
        system: str,
        user: str,
        tool: Any,
    ) -> dict[str, Any]:
        self.calls += 1
        return self._payloads.pop(0)


def test_interpreter_parses_valid_tool_payload(tmp_path: Path) -> None:
    schema, model = _schema_model(tmp_path)
    client = _FakeToolClient([_valid_tool_payload()])
    qi = QueryInterpreter(client)
    out = qi.interpret("How many tracks?", model, schema, "sqlite")
    assert out.confidence == "high"
    assert out.intent.intent_summary
    assert client.calls == 1


def test_interpreter_retries_on_schema_mismatch_then_succeeds(tmp_path: Path) -> None:
    schema, model = _schema_model(tmp_path)
    bad = _valid_tool_payload()
    bad["intent"]["limit"] = "not-an-int"
    good = _valid_tool_payload()
    client = _FakeToolClient([bad, good])
    qi = QueryInterpreter(client)
    out = qi.interpret("How many tracks?", model, schema, "sqlite")
    assert out.intent.limit is None
    assert client.calls == 2


def test_interpreter_retries_on_malformed_structure(tmp_path: Path) -> None:
    schema, model = _schema_model(tmp_path)
    bad = {"confidence": "high"}
    good = _valid_tool_payload()
    client = _FakeToolClient([bad, good])
    qi = QueryInterpreter(client)
    out = qi.interpret("How many tracks?", model, schema, "sqlite")
    assert out.ambiguities == []
    assert client.calls == 2


def test_interpreter_fallback_after_two_failures(tmp_path: Path) -> None:
    schema, model = _schema_model(tmp_path)
    bad = {"confidence": "high"}
    client = _FakeToolClient([bad, bad])
    qi = QueryInterpreter(client)
    out = qi.interpret("Original Q", model, schema, "sqlite")
    assert out.confidence == "low"
    assert len(out.ambiguities) == 1
    assert out.ambiguities[0].type == "join_path"
    assert client.calls == 2

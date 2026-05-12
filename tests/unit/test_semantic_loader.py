from pathlib import Path

import pytest

from lumen.semantic.loader import load_semantic_model


def test_load_semantic_model_from_temp_dir(tmp_path: Path) -> None:
    root = tmp_path / "semantic"
    (root / "entities").mkdir(parents=True)
    (root / "metrics").mkdir(parents=True)
    (root / "entities" / "a.yaml").write_text(
        "name: alpha\ntable: A\ndescription: x\nprimary_key: id\n",
        encoding="utf-8",
    )
    (root / "entities" / "b.yaml").write_text(
        "- name: beta\n  table: B\n  primary_key: id\n",
        encoding="utf-8",
    )
    (root / "metrics" / "m.yaml").write_text(
        "- name: m1\n"
        "  type: simple\n"
        "  entity: alpha\n"
        "  measure:\n"
        "    expression: v\n"
        "    aggregation: sum\n",
        encoding="utf-8",
    )
    (root / "relationships.yaml").write_text(
        "relationships:\n"
        "  - from: alpha\n"
        "    from_key: id\n"
        "    to: beta\n"
        "    to_key: id\n"
        "    type: many_to_one\n",
        encoding="utf-8",
    )
    model = load_semantic_model(root)
    assert {e.name for e in model.entities} == {"alpha", "beta"}
    assert len(model.metrics) == 1
    assert len(model.relationships) == 1


def test_malformed_yaml_includes_path(tmp_path: Path) -> None:
    root = tmp_path / "semantic"
    (root / "entities").mkdir(parents=True)
    (root / "metrics").mkdir(parents=True)
    bad = root / "entities" / "bad.yaml"
    bad.write_text("{\nnot valid yaml {{{\n", encoding="utf-8")
    (root / "relationships.yaml").write_text("relationships: []\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_semantic_model(root)
    assert str(bad) in str(excinfo.value)

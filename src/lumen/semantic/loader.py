from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from lumen.semantic.models import Entity, Metric, Relationship, SemanticModel


def load_semantic_model(directory: Path) -> SemanticModel:
    """Load entities, metrics, and relationships from a semantic directory layout."""
    entities_dir = directory / "entities"
    metrics_dir = directory / "metrics"
    rel_path = directory / "relationships.yaml"

    if not entities_dir.is_dir():
        raise ValueError(f"semantic entities directory missing: {entities_dir}")
    if not metrics_dir.is_dir():
        raise ValueError(f"semantic metrics directory missing: {metrics_dir}")
    if not rel_path.is_file():
        raise ValueError(f"semantic relationships file missing: {rel_path}")

    entities: list[Entity] = []
    metrics: list[Metric] = []

    for path in sorted(entities_dir.glob("*.yaml")):
        entities.extend(_parse_entity_file(path))

    for path in sorted(metrics_dir.glob("*.yaml")):
        metrics.extend(_parse_metric_file(path))

    relationships = _parse_relationships_file(rel_path)

    return SemanticModel(entities=entities, metrics=metrics, relationships=relationships)


def _safe_load(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"cannot read semantic file {path}: {e}") from e
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"malformed yaml in {path}: {e}") from e


def _parse_entity_file(path: Path) -> list[Entity]:
    data = _safe_load(path)
    if data is None:
        return []
    payloads: list[dict[str, Any]]
    if isinstance(data, dict):
        payloads = [data]
    elif isinstance(data, list):
        payloads = []
        for idx, item in enumerate(data):
            if item is None:
                continue
            if not isinstance(item, dict):
                raise ValueError(f"invalid entity entry at index {idx} in {path} (not a mapping)")
            payloads.append(item)
    else:
        raise ValueError(f"unexpected YAML root in {path}: expected mapping or list")

    out: list[Entity] = []
    for item in payloads:
        try:
            out.append(Entity.model_validate(item))
        except ValidationError as e:
            raise ValueError(f"invalid entity in {path}: {e}") from e
    return out


def _parse_metric_file(path: Path) -> list[Metric]:
    data = _safe_load(path)
    if data is None:
        return []
    payloads: list[dict[str, Any]]
    if isinstance(data, dict):
        payloads = [data]
    elif isinstance(data, list):
        payloads = []
        for idx, item in enumerate(data):
            if item is None:
                continue
            if not isinstance(item, dict):
                raise ValueError(f"invalid metric entry at index {idx} in {path} (not a mapping)")
            payloads.append(item)
    else:
        raise ValueError(f"unexpected YAML root in {path}: expected mapping or list")

    out: list[Metric] = []
    for item in payloads:
        try:
            out.append(Metric.model_validate(item))
        except ValidationError as e:
            raise ValueError(f"invalid metric in {path}: {e}") from e
    return out


def _parse_relationships_file(path: Path) -> list[Relationship]:
    data = _safe_load(path)
    if not isinstance(data, dict):
        raise ValueError(f"relationships.yaml must be a mapping at root: {path}")
    raw_list = data.get("relationships")
    if raw_list is None:
        raise ValueError(f"relationships.yaml missing top-level 'relationships' key: {path}")
    if not isinstance(raw_list, list):
        raise ValueError(f"'relationships' must be a list in {path}")

    out: list[Relationship] = []
    for idx, item in enumerate(raw_list):
        if not isinstance(item, dict):
            raise ValueError(f"relationship entry {idx} is not a mapping in {path}")
        try:
            out.append(Relationship.model_validate(item))
        except ValidationError as e:
            raise ValueError(f"invalid relationship at index {idx} in {path}: {e}") from e
    return out

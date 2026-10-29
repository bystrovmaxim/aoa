# packages/maxitor/app/tests/test_list_entities_generalization_relations.py
"""ListEntitiesAction carries the generalization half of a specialization axis."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from maxitor.viewer.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

_EXAMPLE_NAME = "specialization_example"


def _load_example() -> Any:
    """Return the repository's worked specialization example, loaded once per session."""
    if _EXAMPLE_NAME in sys.modules:
        return sys.modules[_EXAMPLE_NAME]
    root = Path(__file__).resolve().parents[4]
    path = root / "examples" / "step_21_relations" / "02_specialization.py"
    spec = importlib.util.spec_from_file_location(_EXAMPLE_NAME, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def slice_payload() -> dict[str, Any]:
    """One real domain slice, built by the action from the worked example's graph."""
    example = _load_example()
    qualname = f"{example.MusicDomain.__module__}.{example.MusicDomain.__qualname__}"
    duck = DuckDBGraphResource.build_from_json(
        json.loads(ActionProductMachine().graph_coordinator.to_json())
    )
    return ListEntitiesAction._slice_payload(duck, qualname, False)


def test_generalization_rows_carry_each_extension(slice_payload: dict[str, Any]) -> None:
    """Each extension points at the head with its declared code as the label."""
    rows = [r for r in slice_payload["relations"] if r["relationship_kind"] == "generalization"]
    assert len(rows) == 3
    pairs = {(r["source"].split(".")[-1], r["target"].split(".")[-1], r["label"]) for r in rows}
    assert pairs == {
        ("FirstPressSpecEntity", "VinylRecordCoreEntity", "first"),
        ("RepressSpecEntity", "VinylRecordCoreEntity", "repress"),
        ("TestPressSpecEntity", "VinylRecordCoreEntity", "test"),
    }


def test_a_head_and_its_variants_are_joined_by_their_declared_fields(slice_payload: dict[str, Any]) -> None:
    """(029 FR-046) Each line names the fields it joins, so hovering either field lights both tables."""
    rows = [r for r in slice_payload["relations"] if r["relationship_kind"] == "generalization"]
    assert {(r["source_field"], r["target_field"]) for r in rows} == {("record", "pressing")}


def test_a_variants_reverse_field_is_a_foreign_key(slice_payload: dict[str, Any]) -> None:
    """(029 FR-046) The field that points a variant at its head carries the FK mark; its other fields do not."""
    variant = next(e for e in slice_payload["entities"] if e["id"].endswith("FirstPressSpecEntity"))
    marks = {f["name"]: f["foreign_key"] for f in variant["fields"]}
    assert marks["record"] is True
    assert marks["id"] is False


def test_a_generalization_ends_zero_or_one_at_the_variant_and_one_at_the_head(slice_payload: dict[str, Any]) -> None:
    """(029 FR-043) A head row has at most one row of each variant; a variant row has exactly one head."""
    rows = [r for r in slice_payload["relations"] if r["relationship_kind"] == "generalization"]
    assert {(r["source_cardinality"], r["target_cardinality"]) for r in rows} == {("zero_one", "one")}

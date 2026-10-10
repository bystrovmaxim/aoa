# packages/aoa-maxitor/tests/test_list_entities_generalization_relations.py
"""ListEntitiesAction carries the generalization half of a specialization axis."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_EXAMPLE_NAME = "specialization_example"


def _load_example() -> Any:
    """Return the repository's worked specialization example, loaded once per session."""
    if _EXAMPLE_NAME in sys.modules:
        return sys.modules[_EXAMPLE_NAME]
    root = Path(__file__).resolve().parents[3]
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
        ("FirstPressEntity", "VinylRecordEntity", "first"),
        ("RepressEntity", "VinylRecordEntity", "repress"),
        ("TestPressEntity", "VinylRecordEntity", "test"),
    }

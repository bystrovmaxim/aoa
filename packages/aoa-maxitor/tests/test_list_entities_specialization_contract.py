# tests/test_list_entities_specialization_contract.py
"""
The ERD entry contract accepts the axis row and the group, and refuses a payload that breaks either.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

`ListEntitiesDomainSlicesJson` is `additionalProperties: false` at every level, so a key the action
starts emitting must be declared before it is emitted, and a key the schema declares must be one the
action can produce. This file is the pair of those statements: the real payload of a model with an
axis validates, and each way of breaking it is refused.

The positive case is built from the **action's own SQL** over a real graph, not assembled by hand,
so what is validated is what a caller receives.

═══════════════════════════════════════════════════════════════════════════════
WHY THE SCHEMA IS REACHED DIRECTLY
═══════════════════════════════════════════════════════════════════════════════

`JsonSchemaValue.define` wraps each schema in a pydantic core schema whose validator calls
`jsonschema.validate` and re-raises a `ValueError`, which pydantic then wraps again — so going
through a `TypeAdapter` reports the **instance** rather than the rule that refused it. The schema
object itself is what the contract is, so the tests validate against it and read the real message.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **ValidationError** — the payload does not match the contract; each test asserts the refusal.

Covers the contract only. What the SQL puts in the payload is the store and ERD tests' subject.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from jsonschema.exceptions import ValidationError

from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_entities_action_schema import ListEntitiesDomainSlicesJson
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SCHEMA: dict[str, Any] = ListEntitiesDomainSlicesJson._json_schema


def _load_example() -> Any:
    """
    Return the repository's worked example module, with its model built.

    The model is taken from `examples/` rather than declared here: an entity class living in a test
    module joins the graph every other test assembles, and this suite's own schema test would then
    fail on a model it never asked for. The example is the model this contract is written against.
    """
    root = Path(__file__).resolve().parents[3]
    path = root / "examples" / "step_21_relations" / "02_specialization.py"
    spec = importlib.util.spec_from_file_location("specialization_example", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def slice_row() -> dict[str, Any]:
    """Return one real domain slice, built by the action from a real graph."""
    example = _load_example()
    qualname = f"{example.MusicDomain.__module__}.{example.MusicDomain.__qualname__}"
    duck = DuckDBGraphResource.build_from_json(
        json.loads(ActionProductMachine().graph_coordinator.to_json())
    )
    payload = ListEntitiesAction._slice_payload(duck, qualname, False)
    return {"domain_label": "Music", "domain_qualname": qualname, "list_entities": payload}


def _validates(row: dict[str, Any]) -> None:
    """Assert the contract accepts ``row``."""
    jsonschema.validate([row], _SCHEMA)


def _refuses(row: dict[str, Any]) -> str:
    """Assert the contract refuses ``row`` and return the rule that refused it."""
    with pytest.raises(ValidationError) as caught:
        jsonschema.validate([row], _SCHEMA)
    return caught.value.message


def _broken(row: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of ``row``, safe to damage."""
    return json.loads(json.dumps(row))


# ─────────────────────────────────────────────────────────────────────────────
# The positive case
# ─────────────────────────────────────────────────────────────────────────────


def test_the_real_payload_matches_the_contract(slice_row: dict[str, Any]) -> None:
    _validates(slice_row)


def test_the_row_and_the_group_carry_what_the_contract_promises(slice_row: dict[str, Any]) -> None:
    """The keys under test are the ones the action emits, so a rename fails here rather than in a diagram."""
    entities = slice_row["list_entities"]["entities"]
    head = next(entity for entity in entities if entity["label"] == "VinylRecordEntity")
    axis_row = next(field for field in head["fields"] if field["name"] == "pressing" and field["foreign_key"])

    assert set(axis_row) == {"field_id", "name", "type", "primary_key", "foreign_key"}
    assert axis_row["foreign_key"] is True, "the ERD colours a leading-out column by this flag"
    assert "first" in axis_row["type"] and "test" in axis_row["type"], "every alternative is named"

    group = slice_row["list_entities"]["groups"][0]
    assert set(group) == {"group_id", "label", "classifier_field", "members"}
    assert group["group_id"] == axis_row["field_id"], "the line into the container aims at the axis"
    assert len(group["members"]) == 3


def test_the_axis_has_exactly_one_relation_line(slice_row: dict[str, Any]) -> None:
    """One line into the container, not one per alternative."""
    lines = [r for r in slice_row["list_entities"]["relations"] if r["relationship_kind"] == "specialization"]

    assert len(lines) == 1
    assert lines[0]["label"] == "by media"


# ─────────────────────────────────────────────────────────────────────────────
# The contract is closed
# ─────────────────────────────────────────────────────────────────────────────


def test_a_slice_without_groups_is_refused(slice_row: dict[str, Any]) -> None:
    broken = _broken(slice_row)
    del broken["list_entities"]["groups"]

    assert "'groups' is a required property" in _refuses(broken)


def test_a_group_with_an_undeclared_key_is_refused(slice_row: dict[str, Any]) -> None:
    broken = _broken(slice_row)
    broken["list_entities"]["groups"][0]["surprise"] = 1

    assert "surprise" in _refuses(broken)


@pytest.mark.parametrize("missing", ["group_id", "label", "classifier_field", "members"])
def test_a_group_without_a_required_key_is_refused(slice_row: dict[str, Any], missing: str) -> None:
    broken = _broken(slice_row)
    del broken["list_entities"]["groups"][0][missing]

    assert f"'{missing}' is a required property" in _refuses(broken)


@pytest.mark.parametrize("members", [[], ["only.one.Entity"]])
def test_a_group_that_does_not_group_is_refused(slice_row: dict[str, Any], members: list[str]) -> None:
    """A container around one member would claim a choice that does not exist (FR-028)."""
    broken = _broken(slice_row)
    broken["list_entities"]["groups"][0]["members"] = members

    assert "is too short" in _refuses(broken)

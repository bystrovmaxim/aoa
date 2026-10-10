# tests/maxitor/test_entity_specialization_erd.py
"""
The store keeps both directions of a specialization, and the ERD draws them as one axis.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two things have to hold for the specialization to be visible at all, and they are checked here on a
payload built by hand so that every row in it is accounted for:

  - **the store** keeps the rows of both edge kinds and round-trips their properties through the
    `edges` view, which is what the viewer reads;
  - **the ERD slice** turns the axis into one field row naming every alternative, one group, and
    one relation line — while a scalar field on the same entity stays exactly one `entity_field`
    row, because the axis row must displace nothing it does not own.

═══════════════════════════════════════════════════════════════════════════════
WHY A HAND-BUILT PAYLOAD AND NOT A MODEL
═══════════════════════════════════════════════════════════════════════════════

The engine-side tests already cover what the graph emits. This file is about what the **store and
the ERD** do with it, so the payload is written out: three alternatives with three codes, one
scalar field beside them, and a domain. A model would add rows this test does not assert on, and a
hand-built payload makes the arithmetic exact — three edges in, three rows out.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- **KeyError** — an edge kind the store does not know; not exercised here (T029 owns that guard).

Covers the store and the ERD slice. The interchange contract is its own file.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

HEAD = "demo.HeadEntity"
FIRST = "demo.FirstEntity"
SECOND = "demo.SecondEntity"
THIRD = "demo.ThirdEntity"
DOMAIN = "demo.DemoDomain"

CODES = ("first", "repress", "test")
ALTERNATIVES = (FIRST, SECOND, THIRD)
ALTERNATIVE_LIST = [f"{code} -> {target}" for code, target in zip(CODES, ALTERNATIVES, strict=True)]
LABELS = ["First (first)", "Repress (repress)", "Third (test)"]


def _specialization_edge(code: str, target: str, index: int) -> dict[str, Any]:
    """Return one head→alternative edge, as the engine emits it."""
    return {
        "source_id": HEAD,
        "target_id": target,
        "type": "entity_specialization",
        "relationship": "Association",
        "is_dag": False,
        "properties": {
            "field_name": "pressing",
            "classifier_field": "media",
            "classifier_value": code,
            "alternative_index": index,
            "alternatives": ALTERNATIVE_LIST,
            "labels": LABELS,
            "relation_type": "specialization",
            "cardinality": "one",
            "description": "how it was pressed",
            "has_inverse": True,
            "deprecated": False,
        },
    }


def _generalization_edge(target: str, code: str) -> dict[str, Any]:
    """Return one extension→head edge, as the engine emits it."""
    return {
        "source_id": target,
        "target_id": HEAD,
        "type": "parent_entity",
        "relationship": "Generalization",
        "is_dag": False,
        "properties": {
            "field_name": "record",
            "inverse_field": "pressing",
            "classifier_value": code,
            "head_entity_id": HEAD,
        },
    }


def _payload() -> dict[str, Any]:
    """Return a graph with one axis of three alternatives and one scalar field beside it."""
    entities = (HEAD, FIRST, SECOND, THIRD)
    nodes: list[dict[str, Any]] = [
        {"id": DOMAIN, "type": "Domain", "label": "DemoDomain", "properties": {"name": "Demo", "description": "d"}},
        *(
            {"id": f"{entity}:title", "type": "EntityField", "label": "title", "properties": {"field_type": "str", "primary_key_hint": False}}
            for entity in (HEAD,)
        ),
        *(
            {"id": entity, "type": "Entity", "label": entity.split(".")[-1], "properties": {"description": entity}}
            for entity in entities
        ),
    ]
    edges: list[dict[str, Any]] = [
        *(
            {"source_id": entity, "target_id": DOMAIN, "type": "domain", "relationship": "Composition", "is_dag": False}
            for entity in entities
        ),
        {
            "source_id": HEAD,
            "target_id": f"{HEAD}:title",
            "type": "entity_field",
            "relationship": "Composition",
            "is_dag": False,
            "properties": {"ordinal": 0, "field_name": "title"},
        },
        *(_specialization_edge(code, target, index) for index, (code, target) in enumerate(zip(CODES, ALTERNATIVES, strict=True))),
        *(_generalization_edge(target, code) for code, target in zip(CODES, ALTERNATIVES, strict=True)),
    ]
    return {"schema_version": "1.0", "nodes": nodes, "edges": edges}


@pytest.fixture(scope="module")
def duck() -> DuckDBGraphResource:
    """Return the store built from the hand-written payload."""
    return DuckDBGraphResource.build_from_json(_payload())


@pytest.fixture(scope="module")
def slice_payload(duck: DuckDBGraphResource) -> dict[str, Any]:
    """Return the ERD slice of the demo domain."""
    return ListEntitiesAction._slice_payload(duck, DOMAIN, include_neighbors=False)


# ─────────────────────────────────────────────────────────────────────────────
# The store holds both directions
# ─────────────────────────────────────────────────────────────────────────────


def test_the_specialization_table_holds_one_row_per_alternative(duck: DuckDBGraphResource) -> None:
    rows = duck.execute_fetch_dicts(
        "SELECT target_id, classifier_value, alternative_index, labels "
        "FROM entity_specialization_edges ORDER BY alternative_index",
    )

    assert [row["target_id"] for row in rows] == list(ALTERNATIVES)
    assert [row["classifier_value"] for row in rows] == list(CODES)
    assert [row["alternative_index"] for row in rows] == [0, 1, 2]


def test_the_generalization_table_holds_one_row_per_alternative(duck: DuckDBGraphResource) -> None:
    rows = duck.execute_fetch_dicts(
        "SELECT source_id, target_id, classifier_value, inverse_field "
        "FROM parent_entity_edges ORDER BY classifier_value",
    )

    assert [row["source_id"] for row in rows] == list(ALTERNATIVES)
    assert {row["target_id"] for row in rows} == {HEAD}
    assert {row["inverse_field"] for row in rows} == {"pressing"}


@pytest.mark.parametrize(
    ("kind", "keys"),
    [
        (
            "entity_specialization_edges",
            {
                "field_name",
                "classifier_field",
                "classifier_value",
                "alternative_index",
                "alternatives",
                "labels",
                "relation_type",
                "cardinality",
                "description",
                "has_inverse",
                "deprecated",
            },
        ),
        ("parent_entity_edges", {"field_name", "inverse_field", "classifier_value", "head_entity_id"}),
    ],
)
def test_the_properties_round_trip_through_the_edges_view(
    duck: DuckDBGraphResource,
    kind: str,
    keys: set[str],
) -> None:
    """The viewer reads the `edges` view, so a column the view forgets is a property the diagram loses."""
    rows = duck.execute_fetch_dicts(f"SELECT payload FROM edges WHERE type = '{kind}'")

    assert rows, f"{kind} reached the view"
    for row in rows:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert set(payload) == keys, f"{kind} exports exactly its own properties"


def test_every_edge_of_the_axis_carries_the_whole_declaration(duck: DuckDBGraphResource) -> None:
    """One row in hand is enough to read the cluster, which is why the list is repeated."""
    rows = duck.execute_fetch_dicts("SELECT labels FROM entity_specialization_edges")

    for row in rows:
        labels = row["labels"]
        if isinstance(labels, str):
            labels = json.loads(labels)
        assert labels == LABELS


def test_the_generalization_stays_out_of_the_full_graph(duck: DuckDBGraphResource) -> None:
    """
    The full graph is a system view and strips generalization, so the axis is drawn in the ERD only.

    Asserted by reading the filter the viewer applies rather than by trusting the comment beside it.
    """
    from aoa.maxitor.model.diagrams.actions.full_graph_action import (
        _FULL_GRAPH_SQL_EXCLUDED_RELATIONSHIP,
    )

    assert _FULL_GRAPH_SQL_EXCLUDED_RELATIONSHIP == "Generalization"
    stored = duck.execute_fetch_dicts("SELECT relationship FROM parent_entity_edges LIMIT 1")
    assert stored[0]["relationship"] == _FULL_GRAPH_SQL_EXCLUDED_RELATIONSHIP


# ─────────────────────────────────────────────────────────────────────────────
# The ERD draws one axis
# ─────────────────────────────────────────────────────────────────────────────


def _head_fields(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the field rows of the head entity."""
    head = next(entity for entity in payload["entities"] if entity["id"] == HEAD)
    return head["fields"]


def test_the_axis_is_one_row_naming_every_alternative(slice_payload: dict[str, Any]) -> None:
    axis_rows = [row for row in _head_fields(slice_payload) if row["name"] == "pressing" and row["foreign_key"]]

    assert len(axis_rows) == 1, "one row for the field, never one per alternative"
    row = axis_rows[0]
    assert row["name"] == "pressing"
    for label in LABELS:
        assert label in row["type"], f"{label} is named in the row"
    assert row["foreign_key"] is True, "the column leads out of the table, and the ERD colours it by this"


def test_the_scalar_field_beside_the_axis_is_one_row_and_not_displaced() -> None:
    """The axis row replaces its own field only: the scalar next to it stays exactly as it was."""
    duck = DuckDBGraphResource.build_from_json(_payload())
    fields = _head_fields(ListEntitiesAction._slice_payload(duck, DOMAIN, include_neighbors=False))
    titles = [row for row in fields if row["name"] == "title"]

    assert len(titles) == 1
    assert titles[0]["foreign_key"] is False
    assert titles[0]["primary_key"] is False


def test_the_axis_has_one_group_with_every_alternative(slice_payload: dict[str, Any]) -> None:
    groups = slice_payload["groups"]

    assert len(groups) == 1
    group = groups[0]
    assert group["group_id"] == f"{HEAD}:pressing"
    assert group["label"] == "pressing (by media)"
    assert group["classifier_field"] == "media"
    assert list(group["members"]) == list(ALTERNATIVES)


def test_the_axis_has_one_relation_line_and_it_aims_at_the_group(slice_payload: dict[str, Any]) -> None:
    lines = [row for row in slice_payload["relations"] if row["relationship_kind"] == "specialization"]

    assert len(lines) == 1, "one line into the container, not one per alternative"
    assert lines[0]["source"] == HEAD
    assert lines[0]["target"] == slice_payload["groups"][0]["group_id"]
    assert lines[0]["label"] == "by media"


def test_a_single_alternative_is_not_grouped() -> None:
    """An axis of one is a plain relation: a container around one table would claim a choice (FR-028)."""
    payload = _payload()
    payload["edges"] = [
        edge
        for edge in payload["edges"]
        if not (edge["type"] == "entity_specialization" and edge["target_id"] != FIRST)
    ]
    duck = DuckDBGraphResource.build_from_json(payload)
    slice_data = ListEntitiesAction._slice_payload(duck, DOMAIN, include_neighbors=False)

    assert slice_data["groups"] == []
    axis_rows = [row for row in _head_fields(slice_data) if "by" in row["name"]]
    assert axis_rows == [], "and it is not drawn as an axis row either"

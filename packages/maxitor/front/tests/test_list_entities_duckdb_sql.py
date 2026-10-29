# tests/maxitor/test_list_entities_duckdb_sql.py
"""Regression: list-entities DuckDB slice must not emit a bogus null ``fields`` row."""

from __future__ import annotations

import json

from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


def _slice(duck: DuckDBGraphResource, qual: str) -> dict:
    return ListEntitiesAction._slice_payload(duck, qual, include_neighbors=False)


def test_slice_payload_empty_fields_list_when_entity_has_no_scalar_rows() -> None:
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e", "entity_kind": "core"}},
        ],
        "edges": [
            {
                "source_id": "e1",
                "target_id": "d1",
                "type": "domain",
                "relationship": "Composition",
                "is_dag": False,
            },
        ],
    }
    duck = DuckDBGraphResource.build_from_json(payload)
    out = _slice(duck, "d1")
    assert out["entities"] == [
        {"id": "e1", "label": "E", "domain_qualname": "d1", "entity_kind": "core", "values": [], "fields": []},
    ]


def test_slice_payload_includes_scalar_field_from_entity_field_tables() -> None:
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e", "entity_kind": "core"}},
            {
                "id": "e1:f1",
                "type": "EntityField",
                "label": "f1",
                "properties": {"field_type": "str", "primary_key_hint": False},
            },
        ],
        "edges": [
            {
                "source_id": "e1",
                "target_id": "d1",
                "type": "domain",
                "relationship": "Composition",
                "is_dag": False,
            },
            {
                "source_id": "e1",
                "target_id": "e1:f1",
                "type": "entity_field",
                "relationship": "Composition",
                "is_dag": False,
                "properties": {"ordinal": 0, "field_name": "f1"},
            },
        ],
    }
    duck = DuckDBGraphResource.build_from_json(payload)
    out = _slice(duck, "d1")
    assert out["entities"][0]["fields"] == [
        {
            "field_id": "e1:f1",
            "name": "f1",
            "type": "str",
            "primary_key": False,
            "foreign_key": False,
            "reference_qualname": None,
            "annotation": None,
        },
    ]


def test_a_field_row_carries_its_clean_type_and_its_full_annotation() -> None:
    """(029 FR-031) The clean name a service sends stays the row's type; its full annotation rides beside it."""
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e", "entity_kind": "core"}},
            {
                "id": "e1:f1",
                "type": "EntityField",
                "label": "nickname",
                "properties": {"field_type": "str | None", "field_annotation": "UnionType[str, NoneType]", "primary_key_hint": False},
            },
        ],
        "edges": [
            {"source_id": "e1", "target_id": "d1", "type": "domain", "relationship": "Composition", "is_dag": False},
            {
                "source_id": "e1",
                "target_id": "e1:f1",
                "type": "entity_field",
                "relationship": "Composition",
                "is_dag": False,
                "properties": {"ordinal": 0, "field_name": "nickname"},
            },
        ],
    }
    row = _slice(DuckDBGraphResource.build_from_json(payload), "d1")["entities"][0]["fields"][0]
    assert (row["type"], row["annotation"]) == ("str | None", "UnionType[str, NoneType]")


def test_the_kind_the_wire_carries_is_the_kind_the_store_returns() -> None:
    """A row keeps its kind through the store, so the renderer reads data and never parses a name."""
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e", "entity_kind": "spec"}},
        ],
        "edges": [
            {"source_id": "e1", "target_id": "d1", "type": "domain", "relationship": "Composition", "is_dag": False},
        ],
    }
    duck = DuckDBGraphResource.build_from_json(payload)

    stored = duck.execute_fetch_dicts("SELECT payload FROM nodes WHERE id = ?", ["e1"])[0]["payload"]

    assert json.loads(stored)["entity_kind"] == "spec"


def _relation(source: str, target: str, field: str, *, optional: bool | None) -> dict:
    """An ``entity_relation`` edge with one end; ``optional`` absent when ``None`` (an older service)."""
    properties = {"field_name": field, "relation_type": "association", "cardinality": "one", "description": "d", "has_inverse": False, "deprecated": False}
    if optional is not None:
        properties["optional"] = optional
    return {"source_id": source, "target_id": target, "type": "entity_relation", "relationship": "Association", "is_dag": False, "properties": properties}


def _in_domain(entity: str) -> dict:
    """The edge that puts ``entity`` into domain ``d1``."""
    return {"source_id": entity, "target_id": "d1", "type": "domain", "relationship": "Composition", "is_dag": False}


def test_an_optional_relation_end_is_zero_or_one_and_a_mandatory_one_is_one() -> None:
    """(029 FR-043) The end at the target shows whether the relation may be empty; an older service reads as mandatory."""
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            *({"id": e, "type": "Entity", "label": e, "properties": {"description": e, "entity_kind": "core"}} for e in ("order", "currency")),
        ],
        "edges": [
            _in_domain("order"),
            _in_domain("currency"),
            _relation("order", "currency", "billed_in", optional=True),
            _relation("order", "currency", "priced_in", optional=False),
            _relation("order", "currency", "legacy", optional=None),
        ],
    }
    relations = _slice(DuckDBGraphResource.build_from_json(payload), "d1")["relations"]
    ends = {r["source_field"]: (r["source_cardinality"], r["target_cardinality"]) for r in relations}
    assert ends == {"billed_in": ("zero_many", "zero_one"), "priced_in": ("zero_many", "one"), "legacy": ("zero_many", "one")}


def test_a_table_lists_every_relation_field_whether_or_not_its_target_is_on_screen() -> None:
    """(029 FR-045) 1-hop decides which extra tables come in, never which fields a table lists."""
    payload = {
        "schema_version": "1.0",
        "nodes": [
            *({"id": d, "type": "Domain", "label": d, "properties": {"name": d, "description": d}} for d in ("d1", "d2")),
            *({"id": e, "type": "Entity", "label": e, "properties": {"description": e, "entity_kind": "core"}} for e in ("order", "currency")),
        ],
        "edges": [
            _in_domain("order"),
            {"source_id": "currency", "target_id": "d2", "type": "domain", "relationship": "Composition", "is_dag": False},
            _relation("order", "currency", "billed_in", optional=False),
        ],
    }
    duck = DuckDBGraphResource.build_from_json(payload)

    for include_neighbors in (False, True):
        out = ListEntitiesAction._slice_payload(duck, "d1", include_neighbors=include_neighbors)
        order = next(e for e in out["entities"] if e["id"] == "order")
        fields = [(f["name"], f["type"], f["foreign_key"]) for f in order["fields"]]
        assert fields == [("billed_in", "currency", True)], include_neighbors

    # Without 1-hop the target table stays off the diagram, and so does its line.
    alone = ListEntitiesAction._slice_payload(duck, "d1", include_neighbors=False)
    assert [e["id"] for e in alone["entities"]] == ["order"]
    assert alone["relations"] == []

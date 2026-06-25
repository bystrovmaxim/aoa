# tests/maxitor/test_list_entities_duckdb_sql.py
"""Regression: list-entities DuckDB slice must not emit a bogus null ``fields`` row."""

from __future__ import annotations

from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource


def _slice(duck: DuckDBGraphResource, qual: str) -> dict:
    return ListEntitiesAction._slice_payload(duck, qual, include_neighbors=False)


def test_slice_payload_empty_fields_list_when_entity_has_no_scalar_rows() -> None:
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e"}},
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
        {"id": "e1", "label": "E", "domain_qualname": "d1", "fields": []},
    ]


def test_slice_payload_includes_scalar_field_from_entity_field_tables() -> None:
    payload = {
        "schema_version": "1.0",
        "nodes": [
            {"id": "d1", "type": "Domain", "label": "D", "properties": {"name": "D", "description": "d"}},
            {"id": "e1", "type": "Entity", "label": "E", "properties": {"description": "e"}},
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
        },
    ]

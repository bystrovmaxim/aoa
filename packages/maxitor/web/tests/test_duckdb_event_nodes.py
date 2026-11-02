# packages/maxitor/web/tests/test_duckdb_event_nodes.py
"""
Events in Maxitor's store: a 1.3 graph loads, and only the views over every node change.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The full graph reads the ``nodes`` and ``edges`` views, so events appear there with no styling
of their own. The ERD, lifecycle and use-case diagrams read their own tables, and those hold
the same rows with events in the document or without them.
"""

from __future__ import annotations

from typing import Any

from maxitor.graph_map import split_areas
from maxitor.web.model.diagrams.actions.list_node_types_action import (
    DEFAULT_NODE_TYPE_COLOR,
    NODE_TYPE_FILL_COLORS,
    interchange_node_type_from_duck,
)
from maxitor.web.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_DOMAIN = "shop.ShopDomain"
_ASPECT = "shop.PlaceAction:finish_aspect"
_EVENT = "shop.PlacedEvent"
_FIELD = "shop.PlacedEvent:order_id"

_DIAGRAM_TABLES = ("action", "domain", "entity", "entity_field", "lifecycle", "state", "regular_aspect", "domain_edges")


def _graph(version: str, *, events: bool) -> dict[str, Any]:
    """A small graph of ``version``; with ``events`` it holds an event, its field and both edges."""
    domain_properties: dict[str, Any] = {"name": "shop", "description": "Shop"}
    if version == "1.3":
        domain_properties["typed_events"] = events
    nodes: list[dict[str, Any]] = [
        {"id": _DOMAIN, "type": "Domain", "label": "ShopDomain", "properties": domain_properties},
        {"id": _ASPECT, "type": "RegularAspect", "label": "finish_aspect", "properties": {"description": "Finish"}},
    ]
    edges: list[dict[str, Any]] = []
    if events:
        nodes += [
            {"id": _EVENT, "type": "Event", "label": "PlacedEvent", "properties": {}},
            {
                "id": _FIELD,
                "type": "Field",
                "label": "order_id",
                "properties": {"required": True, "description": "", "json_schema_value": False, "entity_schema": False},
            },
        ]
        edges += [
            {"source_id": _DOMAIN, "target_id": _EVENT, "type": "domain_event", "relationship": "Aggregation", "is_dag": False, "properties": {}},
            {"source_id": _ASPECT, "target_id": _EVENT, "type": "@emits", "relationship": "Association", "is_dag": False, "properties": {}},
            {"source_id": _EVENT, "target_id": _FIELD, "type": "field", "relationship": "Composition", "is_dag": False, "properties": {}},
        ]
    return {"schema_version": version, "nodes": nodes, "edges": edges}


def _rows(con: Any, table: str) -> list[tuple[Any, ...]]:
    """Return one table's rows in a stable order."""
    return sorted(con.execute(f"SELECT * FROM {table}").fetchall(), key=repr)


def test_events_reach_the_views_of_the_full_graph() -> None:
    con = DuckDBGraphResource.build_from_json(_graph("1.3", events=True)).service

    assert con.execute("SELECT id, label FROM event").fetchall() == [(_EVENT, "PlacedEvent")]
    assert con.execute("SELECT id FROM nodes WHERE type = 'event'").fetchall() == [(_EVENT,)]
    assert {row[0] for row in con.execute("SELECT DISTINCT type FROM edges").fetchall()} == {
        "domain_event_edges",
        "emits_edges",
        "field_edges",
    }


def test_the_event_type_has_a_name_and_no_styling() -> None:
    assert interchange_node_type_from_duck("event") == "Event"
    assert "Event" not in NODE_TYPE_FILL_COLORS
    assert DEFAULT_NODE_TYPE_COLOR


def test_the_tables_of_the_other_diagrams_do_not_change() -> None:
    plain = DuckDBGraphResource.build_from_json(_graph("1.3", events=False)).service
    with_events = DuckDBGraphResource.build_from_json(_graph("1.3", events=True)).service

    for table in _DIAGRAM_TABLES:
        assert _rows(plain, table) == _rows(with_events, table), table


def test_a_1_2_graph_still_loads() -> None:
    con = DuckDBGraphResource.build_from_json(_graph("1.2", events=False)).service

    assert con.execute("SELECT id FROM domain").fetchall() == [(_DOMAIN,)]
    assert con.execute("SELECT COUNT(*) FROM event").fetchone() == (0,)


def test_the_map_places_a_domain_event_in_its_domain() -> None:
    areas = split_areas(_graph("1.3", events=True))

    home = next(area for area in areas.areas if area.id == _DOMAIN)
    assert _EVENT in {node.id for node in home.nodes}

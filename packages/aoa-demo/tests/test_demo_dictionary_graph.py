# tests/test_demo_dictionary_graph.py
"""The demo's dictionaries reach the graph: their values, and the fields that reference them."""

from __future__ import annotations

import json
from typing import Any

from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator


def _graph() -> dict[str, Any]:
    """Return the demo's graph as the coordinator exports it."""
    return json.loads(build_registered_interchange_coordinator().to_json())


def _enums(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the graph's dictionary nodes, by label."""
    return [
        node
        for node in graph["nodes"]
        if node.get("type") == "Entity" and node["properties"].get("entity_kind") == "enum"
    ]


def test_the_currency_dictionary_is_a_node_with_three_values() -> None:
    """A dictionary is an entity node that carries its declared values."""
    currency = next(node for node in _enums(_graph()) if node["label"] == "CurrencyEnumEntity")

    assert [value["code"] for value in currency["properties"]["values"]] == ["usd", "eur", "rub"]
    assert currency["properties"]["values"][1]["display_name"] == "Euro"
    assert currency["properties"]["values"][1]["properties"] == {"symbol": "€"}


def test_every_currency_field_references_the_dictionary() -> None:
    """A field typed by a dictionary names it, so a reader can follow the reference."""
    graph = _graph()
    references = [
        node
        for node in graph["nodes"]
        if node.get("type") == "EntityField"
        and node["properties"].get("reference_qualname", "").endswith("CurrencyEnumEntity")
    ]

    assert len(references) >= 26, f"expected the demo's currency fields, got {len(references)}"


def test_the_drawing_axis_borrows_its_codes_and_has_no_classifier_field() -> None:
    """An axis classified by a dictionary names the dictionary and drops the classifier field."""
    axis_edges = [edge for edge in _graph()["edges"] if edge.get("type") == "entity_specialization"]

    assert axis_edges, "the demo's drawing axis must be in the graph"
    for edge in axis_edges:
        assert edge["properties"]["dictionary_label"] == "GeneralizationShapesKindEnumEntity"
        assert edge["properties"]["dictionary_qualname"].endswith("GeneralizationShapesKindEnumEntity")
        assert "classifier_field" not in edge["properties"]


def test_the_demo_graph_carries_the_dictionary_relation_edges() -> None:
    """Every dictionary selection is an ordinary relation edge, not a reference edge."""
    graph = _graph()
    relations = [
        edge
        for edge in graph["edges"]
        if edge.get("type") == "entity_relation" and edge["target_id"].endswith("CurrencyEnumEntity")
    ]

    assert len(relations) >= 26, f"expected the demo's currency relations, got {len(relations)}"
    for edge in relations:
        assert edge["properties"]["relation_type"] == "association"
        assert edge["properties"]["cardinality"] == "one"
        assert edge["properties"]["has_inverse"] is False
        assert edge["properties"]["field_name"]


def test_the_demo_graph_loads_into_the_viewer_with_the_new_edge() -> None:
    """An edge type the resource does not know raises ``KeyError``; the demo must load."""
    store = DuckDBGraphResource.build_from_json(_graph())

    assert store is not None


def test_the_demo_slice_carries_the_dictionary_association() -> None:
    """The ERD has an arrow from the host to the dictionary, labelled with the field name."""
    graph = _graph()
    relation = next(
        edge
        for edge in graph["edges"]
        if edge.get("type") == "entity_relation" and edge["target_id"].endswith("CurrencyEnumEntity")
    )
    domain = next(
        edge["target_id"]
        for edge in graph["edges"]
        if edge.get("type") == "domain" and edge["source_id"] == relation["source_id"]
    )
    store = DuckDBGraphResource.build_from_json(graph)
    diagram = ListEntitiesAction._slice_payload(store, domain, include_neighbors=True)

    assert relation["target_id"] in {entity["id"] for entity in diagram["entities"]}
    assert any(
        row["relationship_kind"] == "association"
        and row["source"] == relation["source_id"]
        and row["target"] == relation["target_id"]
        and row["label"].startswith(relation["properties"]["field_name"])
        for row in diagram["relations"]
    )

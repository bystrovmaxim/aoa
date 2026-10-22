# tests/test_demo_dictionary_graph.py
"""The demo's dictionaries reach the graph: their values, and the fields that reference them."""

from __future__ import annotations

import json
from typing import Any

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

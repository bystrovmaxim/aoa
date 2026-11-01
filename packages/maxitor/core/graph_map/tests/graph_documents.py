# packages/maxitor/core/graph_map/tests/graph_documents.py
"""The small graph document the map's tests share."""

from __future__ import annotations

from typing import Any

from maxitor.graph_map import split_areas


def node(identifier: str, kind: str = "Entity") -> dict[str, Any]:
    """A node of the graph file."""
    return {"id": identifier, "label": identifier.upper(), "type": kind, "properties": {}}


def edge(source: str, kind: str, target: str, relationship: str = "Association") -> dict[str, Any]:
    """A link of the graph file."""
    return {
        "id": f"{source}|{kind}|{target}",
        "source_id": source,
        "target_id": target,
        "type": kind,
        "relationship": relationship,
        "properties": {},
    }


def document() -> dict[str, Any]:
    """Two domains; a field held by an entity; a node in both domains; one in none; a generalization."""
    return {
        "nodes": [
            node("d1", "Domain"),
            node("d2", "Domain"),
            node("a"),
            node("a:f", "EntityField"),
            node("b"),
            node("shared"),
            node("free", "Role"),
            node("c"),
        ],
        "edges": [
            edge("a", "domain", "d1", "Aggregation"),
            edge("b", "domain", "d2", "Aggregation"),
            edge("shared", "domain", "d1", "Aggregation"),
            edge("shared", "domain", "d2", "Aggregation"),
            edge("c", "domain", "d2", "Aggregation"),
            edge("a", "entity_field", "a:f", "Composition"),
            edge("a", "entity_relation", "b"),
            edge("a", "entity_relation_2", "c"),
            edge("b", "parent_entity", "c", "Generalization"),
        ],
    }


def by_id(document_: dict[str, Any]) -> dict[str, Any]:
    """The areas of a document by id."""
    return {area.id: area for area in split_areas(document_).areas}

# tests/maxitor/test_list_entity_kinds_action.py
"""
Tests for ``GET /api/v1/list-entity-kinds``: the kinds of the loaded graph, named by the graph.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor holds no list of kinds and no table of names. The listing shows exactly the
words the loaded graph states, ordered by word, each named by the graph or — when
the graph names none — by the word with its first letter capitalised.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.api.graph_store import GraphEntry, GraphStore
from maxitor.front.model.diagrams.actions.list_entity_kinds_action import ListEntityKindsAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://kinds.test/graph-json"
_REFERENCE_GRAPH = Path(__file__).resolve().parents[4] / "specs/025-graph-index-memory/data/ref-graph-2026-10-26.json.gz"


def _entity(identifier: str, **properties: Any) -> dict[str, Any]:
    """Return an ``Entity`` node with a description plus ``properties``."""
    return {"id": identifier, "label": identifier.rsplit(".", 1)[-1], "type": "Entity", "properties": {"description": "", **properties}}


def _foreign_graph() -> dict[str, Any]:
    """A graph from a producer that is not AOA, with one row of each interesting shape."""
    return {
        "schema_version": "1.0",
        "nodes": [
            _entity("shop.OrderEntity", entity_kind="aggregate", entity_kind_label="Aggregate root"),
            _entity("shop.CartEntity", entity_kind="aggregate"),
            _entity("shop.PlacedEntity", entity_kind="event"),
            _entity("shop.LinkEntity", entity_kind="link"),
            _entity("shop.LegacyEntity"),
            _entity("tests.fixture.HiddenEntity", entity_kind="fixture"),
            _entity("shop.f.<locals>.LocalEntity", entity_kind="local"),
            _entity("shop.TwoEntity", entity_kind="pair", entity_kind_label="B"),
            _entity("shop.OneEntity", entity_kind="pair", entity_kind_label="A"),
        ],
        "edges": [],
    }


def _client(graph: dict[str, Any]) -> TestClient:
    """Return a client whose store serves ``graph`` for ``_SOURCE``."""

    async def builder(source: str) -> GraphEntry:
        """Build the one graph the test serves."""
        empty_sidebar = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
        return GraphEntry(source=source, graph=DuckDBGraphResource.build_from_json(graph), sidebar=empty_sidebar, last_read=0.0)

    app = create_app()
    app.state.graph_store = GraphStore(builder)
    return TestClient(app, raise_server_exceptions=False)


def test_the_listing_is_the_graphs_kinds_named_by_the_graph() -> None:
    """Every word the graph states, ordered, named by the graph or by the capitalised word."""
    rows = ListEntityKindsAction.entity_kind_rows(DuckDBGraphResource.build_from_json(_foreign_graph()))

    assert rows == [
        {"entity_kind": "aggregate", "label": "Aggregate root"},
        {"entity_kind": "event", "label": "Event"},
        {"entity_kind": "link", "label": "Link"},
        {"entity_kind": "pair", "label": "A"},
        {"entity_kind": "unknown", "label": "Unknown"},
    ]
    ListEntityKindsAction.Result(list_entity_kinds=rows)  # validates against ListEntityKindsJson


def test_the_route_answers_the_listing() -> None:
    """``GET /api/v1/list-entity-kinds`` answers the same rows for the named source."""
    response = _client(_foreign_graph()).get("/api/v1/list-entity-kinds", params={"source": _SOURCE})

    assert response.status_code == 200
    assert [row["entity_kind"] for row in response.json()["list_entity_kinds"]] == [
        "aggregate", "event", "link", "pair", "unknown",
    ]


def test_the_route_without_a_source_is_refused_like_the_others() -> None:
    """A read that names no source answers ``400``, as every diagram route does."""
    response = _client(_foreign_graph()).get("/api/v1/list-entity-kinds")

    assert response.status_code == 400


def test_the_reference_graph_lists_aoas_words_with_capitalised_fallbacks() -> None:
    """The frozen reference export predates display names, so its kinds are named by their words."""
    graph = json.loads(gzip.decompress(_REFERENCE_GRAPH.read_bytes()))
    graph = graph.get("coordinator_json", graph)
    graph = json.loads(graph) if isinstance(graph, str) else graph

    rows = ListEntityKindsAction.entity_kind_rows(DuckDBGraphResource.build_from_json(graph))

    assert rows == [
        {"entity_kind": "core", "label": "Core"},
        {"entity_kind": "detail", "label": "Detail"},
        {"entity_kind": "enum", "label": "Enum"},
        {"entity_kind": "spec", "label": "Spec"},
    ]

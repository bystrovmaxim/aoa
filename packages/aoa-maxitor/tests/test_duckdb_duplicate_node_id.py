# packages/aoa-maxitor/tests/test_duckdb_duplicate_node_id.py
"""A graph that lists the same node ``id`` twice in one table is refused at build time."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.graph_store import GraphEntry, GraphStore
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://duplicate.test/graph-json"
_EMPTY_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])


def _domain(node_id: str) -> dict[str, Any]:
    """Return a minimal Domain node."""
    return {"id": node_id, "label": node_id, "type": "Domain", "properties": {"name": node_id, "description": ""}}


def _action(node_id: str) -> dict[str, Any]:
    """Return a minimal Action node."""
    return {"id": node_id, "label": node_id, "type": "Action", "properties": {"description": ""}}


def _lifecycle(node_id: str) -> dict[str, Any]:
    """Return a minimal Lifecycle node."""
    return {"id": node_id, "label": node_id, "type": "Lifecycle", "properties": {"field_name": "status"}}


def _payload(*nodes: dict[str, Any]) -> dict[str, Any]:
    """Return a coordinator payload with the given nodes and no edges."""
    return {"schema_version": "1.0", "nodes": list(nodes), "edges": []}


def test_one_node_twice_in_one_table_is_refused_with_its_id() -> None:
    """A Domain id listed twice raises a ``ValueError`` that names the id and the table."""
    payload = _payload(_domain("d.dup.Dom"), _domain("d.dup.Dom"))

    with pytest.raises(ValueError) as error:
        DuckDBGraphResource.build_from_json(payload)

    assert str(error.value) == 'Graph has a duplicate node id "d.dup.Dom" in table "domain".'


def test_the_first_duplicate_in_table_then_id_order_is_named() -> None:
    """Two duplicated tables are reported by the table name, then the id, not by payload order."""
    payload = _payload(
        _domain("z.dup.Dom"),
        _domain("z.dup.Dom"),
        _action("a.dup.Act"),
        _action("a.dup.Act"),
    )

    with pytest.raises(ValueError) as error:
        DuckDBGraphResource.build_from_json(payload)

    assert str(error.value) == 'Graph has a duplicate node id "a.dup.Act" in table "action".'


def test_the_same_id_in_two_tables_is_accepted() -> None:
    """A repeat across tables is not a duplicate: the check keeps the primary key's per-table scope."""
    resource = DuckDBGraphResource.build_from_json(_payload(_domain("shared.id"), _lifecycle("shared.id")))

    assert len(resource.execute_fetch_dicts("SELECT id FROM nodes")) == 2


def test_a_graph_without_duplicates_builds() -> None:
    """A payload with no duplicate id builds as before."""
    resource = DuckDBGraphResource.build_from_json(_payload(_domain("d.one.Dom"), _action("a.one.Act")))

    assert len(resource.execute_fetch_dicts("SELECT id FROM nodes")) == 2


def test_the_refusal_reaches_the_application_and_stores_nothing() -> None:
    """A duplicated source answers 422 with the id, and the store holds no entry for it."""
    duplicate = _payload(_domain("d.app.Dom"), _domain("d.app.Dom"))

    async def builder(source: str) -> GraphEntry:
        graph = DuckDBGraphResource.build_from_json(duplicate)
        return GraphEntry(source=source, graph=graph, sidebar=_EMPTY_SIDEBAR, last_read=0.0)

    app = create_app()
    store = GraphStore(builder)
    app.state.graph_store = store
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/list-domains", params={"source": _SOURCE})

    assert response.status_code == 422
    assert "d.app.Dom" in response.json()["detail"]
    assert store.held == 0

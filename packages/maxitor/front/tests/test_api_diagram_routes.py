# tests/maxitor/test_api_diagram_routes.py
"""Tests for the six diagram routes: each answers from the graph of the source it names."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.api.graph_source_middleware import MISSING_SOURCE_DETAIL
from maxitor.front.api.graph_store import GraphEntry, GraphStore
from maxitor.front.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from maxitor.front.model.diagrams.actions.full_graph_action import FullGraphAction
from maxitor.front.model.diagrams.actions.get_lifecycle_finite_automaton_action import (
    GetLifecycleFiniteAutomatonAction,
)
from maxitor.front.model.diagrams.actions.list_domains_action import ListDomainsAction
from maxitor.front.model.diagrams.actions.list_entities_action import ListEntitiesAction
from maxitor.front.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import (
    DUCKDB_GRAPH_CONNECTION_KEY,
    DuckDBGraphResource,
)

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# ─── Fixture ─────────────────────────────────────────────────────────────────

_DEFAULT_DOMAIN_ID = "d.default.Dom"
_LIFECYCLE_ID = "e.x.Entity:lifecycle:status"
_SOURCE_A = "https://a.test/graph-json"
_SOURCE_B = "https://b.test/graph-json"
_EMPTY_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])


def _payload(domain_id: str) -> dict[str, Any]:
    """Return a coordinator payload with one domain and one two-state lifecycle."""
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": domain_id,
                "label": domain_id,
                "type": "Domain",
                "properties": {"name": domain_id, "description": ""},
            },
            {"id": _LIFECYCLE_ID, "label": "status", "type": "Lifecycle", "properties": {"field_name": "status"}},
            {
                "id": f"{_LIFECYCLE_ID}:draft",
                "label": "draft",
                "type": "StateInitial",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "draft"},
            },
            {
                "id": f"{_LIFECYCLE_ID}:done",
                "label": "done",
                "type": "StateFinal",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "done"},
            },
        ],
        "edges": [
            {
                "source_id": _LIFECYCLE_ID,
                "target_id": f"{_LIFECYCLE_ID}:draft",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "draft"},
            },
            {
                "source_id": _LIFECYCLE_ID,
                "target_id": f"{_LIFECYCLE_ID}:done",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "done"},
            },
            {
                "source_id": f"{_LIFECYCLE_ID}:draft",
                "target_id": f"{_LIFECYCLE_ID}:done",
                "type": "lifecycle_transition",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"from_state": "draft", "to_state": "done"},
            },
        ],
    }


def _graph(domain_id: str = _DEFAULT_DOMAIN_ID) -> DuckDBGraphResource:
    """Return a freshly built graph for ``domain_id``."""
    return DuckDBGraphResource.build_from_json(_payload(domain_id))


def _route_cases(domain_id: str) -> tuple[tuple[str, dict[str, str], Any, Any], ...]:
    """Return ``(path, query, action class, params)`` for the six diagram routes against ``domain_id``."""
    return (
        ("/api/v1/list-domains", {}, ListDomainsAction, ParamsStub()),
        ("/api/v1/list-entities", {}, ListEntitiesAction, ListEntitiesAction.Params()),
        ("/api/v1/list-node-types", {}, ListNodeTypesAction, ParamsStub()),
        ("/api/v1/full-graph", {}, FullGraphAction, ParamsStub()),
        (
            "/api/v1/lifecycle-finite-automaton",
            {"lifecycle_graph_node_id": _LIFECYCLE_ID},
            GetLifecycleFiniteAutomatonAction,
            GetLifecycleFiniteAutomatonAction.Params(lifecycle_graph_node_id=_LIFECYCLE_ID),
        ),
        (
            "/api/v1/domain-use-case-diagram",
            {"domain_id": domain_id},
            GetDomainUseCaseDiagramAction,
            GetDomainUseCaseDiagramAction.Params(domain_id=domain_id),
        ),
    )


def _direct_body(action_cls: Any, params: Any, graph: Any) -> dict[str, Any]:
    """Return what the machine answers when the graph is supplied by hand, as it did before the change."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    result = asyncio.run(
        machine.run(Context(), action_cls(), params, connections={DUCKDB_GRAPH_CONNECTION_KEY: graph}),
    )
    return result.model_dump()


def _store(graphs: dict[str, DuckDBGraphResource], calls: list[str]) -> GraphStore:
    """Return a store that serves ``graphs`` by source and records every build."""

    async def builder(source: str) -> GraphEntry:
        calls.append(source)
        return GraphEntry(source=source, graph=graphs[source], sidebar=_EMPTY_SIDEBAR, last_read=0.0)

    return GraphStore(builder)


def _client(graphs: dict[str, DuckDBGraphResource]) -> tuple[TestClient, GraphStore, list[str]]:
    """Return a client over an application whose store serves ``graphs``, the store, and its build log."""
    app = create_app()
    calls: list[str] = []
    store = _store(graphs, calls)
    app.state.graph_store = store
    return TestClient(app, raise_server_exceptions=False), store, calls


# ─── R-1: every route answers for the source it names ───────────────────────


def test_each_route_answers_the_payload_of_its_source() -> None:
    """Every route reaches its action and answers what that action answers with the source's graph by hand."""
    graph = _graph()
    client, _, _ = _client({_SOURCE_A: graph})

    for path, query, action_cls, params in _route_cases(_DEFAULT_DOMAIN_ID):
        response = client.get(path, params={**query, "source": _SOURCE_A})
        assert response.status_code == 200, f"{path} -> {response.status_code} {response.text[:200]}"
        assert response.json() == _direct_body(action_cls, params, graph), path


def test_routes_answer_from_the_source_they_name() -> None:
    """Two sources answer two different graphs, and neither read leaks into the other."""
    client, store, _ = _client({_SOURCE_A: _graph("d.a.Dom"), _SOURCE_B: _graph("d.b.Dom")})

    first = client.get("/api/v1/list-domains", params={"source": _SOURCE_A})
    second = client.get("/api/v1/list-domains", params={"source": _SOURCE_B})
    again = client.get("/api/v1/list-domains", params={"source": _SOURCE_A})

    assert first.json() != second.json()
    assert again.json() == first.json()
    assert store.held == 2


def test_a_cold_read_builds_once_and_repeat_reads_reuse_it() -> None:
    """The first read builds the source; later reads of it cost no build."""
    client, store, calls = _client({_SOURCE_A: _graph()})

    for _ in range(3):
        response = client.get("/api/v1/list-domains", params={"source": _SOURCE_A})
        assert response.status_code == 200

    assert calls == [_SOURCE_A]
    assert store.held == 1


def test_the_sidebar_answers_for_the_named_source() -> None:
    """The sidebar route serves the sidebar built with that source's graph, and that graph's fingerprint."""
    client, _, _ = _client({_SOURCE_A: _graph()})

    response = client.get("/api/sidebar", params={"source": _SOURCE_A})

    assert response.status_code == 200
    assert response.json() == {
        "level1_nodes": [],
        "level2_diagrams": [],
        "level2_nodes": [],
        "level3_diagrams": [],
        "fingerprint": "",
    }


# ─── R-2: a read without a source ───────────────────────────────────────────


def test_every_route_refuses_a_read_without_a_source() -> None:
    """A read that names no source is refused by name, before any action runs."""
    client, _, calls = _client({_SOURCE_A: _graph()})

    for path, query, _, _ in _route_cases(_DEFAULT_DOMAIN_ID):
        response = client.get(path, params=query)
        assert response.status_code == 400, f"{path} -> {response.status_code} {response.text[:200]}"
        assert response.json() == {"detail": MISSING_SOURCE_DETAIL}, path

    sidebar = client.get("/api/sidebar")
    assert sidebar.status_code == 400
    assert sidebar.json() == {"detail": MISSING_SOURCE_DETAIL}
    assert calls == []


def test_a_route_keeps_its_own_parameter_validation() -> None:
    """The source is the middleware's concern; a missing route parameter is still the adapter's."""
    client, _, _ = _client({_SOURCE_A: _graph()})

    response = client.get("/api/v1/lifecycle-finite-automaton", params={"source": _SOURCE_A})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "lifecycle_graph_node_id"]

# tests/maxitor/test_api_diagram_routes.py
"""Tests for the six diagram routes: one shared graph, and the answers they gave before."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aoa.action_machine.context import Context
from aoa.action_machine.exceptions import HandleError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder
from aoa.maxitor.model.diagrams.actions.domain_use_case_diagram_action import GetDomainUseCaseDiagramAction
from aoa.maxitor.model.diagrams.actions.full_graph_action import FullGraphAction
from aoa.maxitor.model.diagrams.actions.get_lifecycle_finite_automaton_action import GetLifecycleFiniteAutomatonAction
from aoa.maxitor.model.diagrams.actions.list_domains_action import ListDomainsAction
from aoa.maxitor.model.diagrams.actions.list_entities_action import ListEntitiesAction
from aoa.maxitor.model.diagrams.actions.list_node_types_action import ListNodeTypesAction
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DUCKDB_GRAPH_CONNECTION_KEY, DuckDBGraphResource

# ─── Fixture ─────────────────────────────────────────────────────────────────

_DEFAULT_DOMAIN_ID = "d.default.Dom"
_LIFECYCLE_ID = "e.x.Entity:lifecycle:status"


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
    """Return what the machine answers when the graph is supplied by hand, as it was before the change."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    result = asyncio.run(
        machine.run(Context(), action_cls(), params, connections={DUCKDB_GRAPH_CONNECTION_KEY: graph}),
    )
    return result.model_dump()


class _RecordingGraph:
    """A graph stand-in that counts how often a route reached it."""

    def __init__(self, inner: DuckDBGraphResource) -> None:
        self.inner = inner
        self.reads = 0

    @property
    def service(self) -> Any:
        """Count the read and answer as the wrapped graph does."""
        self.reads += 1
        return self.inner.service

    def execute_fetch_dicts(self, sql: str, parameters: Any = None) -> Any:
        """Count the read and answer as the wrapped graph does."""
        self.reads += 1
        return self.inner.execute_fetch_dicts(sql, parameters)


def _client_with(graph: Any) -> TestClient:
    """Return a client over an application whose slot already holds ``graph``."""
    app = create_app()
    app.state.duckdb_graph = graph
    return TestClient(app)


# ─── R-2: with a graph loaded ────────────────────────────────────────────────


def test_routes_with_a_graph_answer_the_recorded_baseline() -> None:
    """Every route reaches its action and answers exactly what that action answers with the graph by hand."""
    graph = _graph()
    client = _client_with(graph)

    for path, query, action_cls, params in _route_cases(_DEFAULT_DOMAIN_ID):
        response = client.get(path, params=query)
        assert response.status_code == 200, f"{path} -> {response.status_code} {response.text[:200]}"
        assert response.json() == _direct_body(action_cls, params, graph), path


def test_every_route_reads_the_replaced_slot() -> None:
    """A graph put into the slot after the application was built is what all six routes read."""
    first = _graph("d.first.Dom")
    recording = _RecordingGraph(_graph("d.second.Dom"))
    app = create_app()
    app.state.duckdb_graph = first
    client = TestClient(app)

    sanity = client.get("/api/v1/list-domains")
    assert sanity.status_code == 200, f"/api/v1/list-domains -> {sanity.status_code} {sanity.text[:200]}"
    assert sanity.json() == _direct_body(ListDomainsAction, ParamsStub(), first)

    app.state.duckdb_graph = recording
    for path, query, action_cls, params in _route_cases("d.second.Dom"):
        response = client.get(path, params=query)
        assert response.status_code == 200, f"{path} -> {response.status_code} {response.text[:200]}"
        assert response.json() == _direct_body(action_cls, params, recording.inner), path

    assert recording.reads >= len(_route_cases("d.second.Dom"))


# ─── R-3: with nothing loaded ────────────────────────────────────────────────

#: What five of the six routes answered before this change, with nothing loaded and no query given.
#: Recorded from the unmodified branch; the adapter answers every uncaught exception with one
#: generic body and writes nothing to the log, so these bodies are all a caller ever sees.
_RECORDED_UNCHANGED: dict[str, tuple[int, dict[str, Any]]] = {
    "/api/v1/list-domains": (500, {"detail": "Internal server error"}),
    "/api/v1/list-node-types": (500, {"detail": "Internal server error"}),
    "/api/v1/full-graph": (500, {"detail": "Internal server error"}),
    "/api/v1/lifecycle-finite-automaton": (
        422,
        {
            "detail": [
                {
                    "type": "missing",
                    "loc": ["query", "lifecycle_graph_node_id"],
                    "msg": "Field required",
                    "input": None,
                },
            ],
        },
    ),
    "/api/v1/domain-use-case-diagram": (
        422,
        {
            "detail": [
                {"type": "missing", "loc": ["query", "domain_id"], "msg": "Field required", "input": None},
            ],
        },
    ),
}

#: The sixth route, and the one place this change is visible to a caller. See the divergence test.
_DIVERGED_ROUTE = "/api/v1/list-entities"
_RECORDED_DIVERGED: tuple[int, dict[str, Any]] = (500, {"detail": "Internal server error"})
_ANSWERED_NOW: tuple[int, dict[str, Any]] = (200, {"domain_slices": []})


def test_routes_without_a_graph_answer_the_recorded_baseline() -> None:
    """Nothing loaded: these routes answer exactly what they answered before, status and body."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        for path, expected in _RECORDED_UNCHANGED.items():
            response = client.get(path)
            assert response.status_code == expected[0], f"{path} -> {response.status_code} {response.text[:200]}"
            assert response.json() == expected[1], path


@pytest.mark.xfail(
    strict=True,
    reason=(
        "open decision for issue #213: a ready resource fails on first read, not at connection "
        "resolution, so this route now answers its empty result instead of a server error "
        "(research.md R11)"
    ),
)
def test_routes_without_a_graph_divergence_for_list_entities() -> None:
    """The one caller-visible difference: this route never reads the graph, so nothing has a chance to refuse."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(_DIVERGED_ROUTE)

    assert response.status_code == _RECORDED_DIVERGED[0], (
        f"{_DIVERGED_ROUTE} now answers {response.status_code} {response.text[:80]} instead of {_RECORDED_DIVERGED}"
    )
    assert response.json() == _RECORDED_DIVERGED[1]


def test_the_diverged_route_answers_only_because_it_never_reads_the_graph() -> None:
    """The divergence is lazy resolution, not a missing refusal: with a filter the same route fails."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        without_filter = client.get(_DIVERGED_ROUTE)
        with_filter = client.get(_DIVERGED_ROUTE, params={"domain_qualnames": _DEFAULT_DOMAIN_ID})

    assert (without_filter.status_code, without_filter.json()) == _ANSWERED_NOW
    assert with_filter.status_code == 500
    assert with_filter.json() == {"detail": "Internal server error"}


# ─── R-4: the load path ──────────────────────────────────────────────────────

#: A URL nothing listens on, so the load fails at reachability rather than in the model.
_UNREACHABLE_SERVICE = "http://127.0.0.1:1/"


def test_a_failed_load_leaves_the_loaded_graph_in_place() -> None:
    """A load that fails changes nothing: every route still reads the graph loaded before it."""
    graph = _graph("d.kept.Dom")
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.duckdb_graph = graph

        failed = client.post("/api/load", json={"service_url": _UNREACHABLE_SERVICE})
        assert failed.status_code == 422, failed.text[:200]

        for path, query, action_cls, params in _route_cases("d.kept.Dom"):
            response = client.get(path, params=query)
            assert response.status_code == 200, f"{path} -> {response.status_code} {response.text[:200]}"
            assert response.json() == _direct_body(action_cls, params, graph), path


def test_a_failed_load_does_not_make_an_empty_slot_look_loaded() -> None:
    """A failed load on a fresh application leaves it reporting nothing loaded, not something half-built."""
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as client:
        failed = client.post("/api/load", json={"service_url": _UNREACHABLE_SERVICE})
        assert failed.status_code == 422, failed.text[:200]

        with pytest.raises(HandleError, match="not loaded"):
            _ = DuckDBGraphHolder(app).service

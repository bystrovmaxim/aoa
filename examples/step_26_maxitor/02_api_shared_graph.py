"""
02_api_shared_graph.py — One graph, one resource: how Maxitor's endpoints carry it

Maxitor's six diagram endpoints all read the SAME thing: the coordinator graph the
load request put into the application's state. There is one such graph per process,
so it is declared once — as a single ready resource the endpoints share — and not as
a resource invented fresh on every call.

The difference is not cosmetic. A resource invented per call is resolved at the
moment the request is routed, which is why every endpoint used to fail the same way
while nothing was loaded, even the ones that never look at the graph. A ready
resource is resolved lazily: reading it is what fails, and only when a route actually
reads it.

This script drives the real FastAPI application, with no server and no browser:

  1. before anything is loaded — what a caller sees, and what a developer who reads
     the resource directly sees;
  2. load a graph — a fixture small enough to read; in real use this is POST /api/load;
  3. every one of the six endpoints answers, and a counting stand-in shows they all
     read the one object;
  4. load a second graph — the next read of every endpoint returns the new one, because
     the shared resource resolves per read and caches nothing.

Output:

    1. Nothing loaded yet
       GET /api/v1/list-domains -> 500 {"detail":"Internal server error"}
       reading the resource itself -> HandleError: Graph is not loaded: call POST /api/load first.
       The caller gets the adapter's one generic body; the developer, driving the
       resource directly, gets a sentence that names the situation and the remedy.

    2. Load a graph
       graph loaded: [{'id': 'd.shop'}]

    3. All six endpoints answer, from one shared resource
       /api/v1/list-domains                   -> 200
       /api/v1/list-entities                  -> 200
       /api/v1/list-node-types                -> 200
       /api/v1/full-graph                     -> 200
       /api/v1/lifecycle-finite-automaton     -> 200
       /api/v1/domain-use-case-diagram        -> 200
       the six requests together read the loaded graph 14 times
       (one object, resolved on every read — not one resource per call)

    4. A second load replaces it for everyone
       GET /api/v1/list-domains -> 200 {"list_domains":[{"qualname":"d.warehouse","label":"d.warehouse","color":"#3b82f6"}]}
       Nothing was restarted and no endpoint holds a graph of its own.

Tutorial: ../../docs/tutorials/step-26-maxitor_draft.md  ·  topic: Maxitor (system graph)

Run:
    uv run python examples/step_26_maxitor/02_api_shared_graph.py
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from aoa.action_machine.exceptions import HandleError
from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.duckdb_graph_holder import DuckDBGraphHolder
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_DIAGRAM_ROUTES: tuple[tuple[str, dict[str, str]], ...] = (
    ("/api/v1/list-domains", {}),
    ("/api/v1/list-entities", {}),
    ("/api/v1/list-node-types", {}),
    ("/api/v1/full-graph", {}),
    ("/api/v1/lifecycle-finite-automaton", {"lifecycle_graph_node_id": "e.x.Entity:lifecycle:status"}),
    ("/api/v1/domain-use-case-diagram", {"domain_id": "d.shop"}),
)


def _payload(domain_id: str) -> dict[str, Any]:
    """Return one domain and one two-state lifecycle — enough for every endpoint."""
    lifecycle = "e.x.Entity:lifecycle:status"
    return {
        "schema_version": "1.0",
        "nodes": [
            {
                "id": domain_id,
                "label": domain_id,
                "type": "Domain",
                "properties": {"name": domain_id, "description": ""},
            },
            {"id": lifecycle, "label": "status", "type": "Lifecycle", "properties": {"field_name": "status"}},
            {
                "id": f"{lifecycle}:draft",
                "label": "draft",
                "type": "StateInitial",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "draft"},
            },
            {
                "id": f"{lifecycle}:done",
                "label": "done",
                "type": "StateFinal",
                "properties": {"lifecycle_class_id": "x.Status", "state_key": "done"},
            },
        ],
        "edges": [
            {
                "source_id": lifecycle,
                "target_id": f"{lifecycle}:draft",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "draft"},
            },
            {
                "source_id": lifecycle,
                "target_id": f"{lifecycle}:done",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "done"},
            },
            {
                "source_id": f"{lifecycle}:draft",
                "target_id": f"{lifecycle}:done",
                "type": "lifecycle_transition",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"from_state": "draft", "to_state": "done"},
            },
        ],
    }


class _CountingGraph:
    """A graph stand-in that counts how often an endpoint reached it."""

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


def main() -> None:
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    print("1. Nothing loaded yet")
    answer = client.get("/api/v1/list-domains")
    print(f"   GET /api/v1/list-domains -> {answer.status_code} {answer.text}")
    try:
        _ = DuckDBGraphHolder(app).service
    except HandleError as exc:
        print(f"   reading the resource itself -> {type(exc).__name__}: {exc}")
    print("   The caller gets the adapter's one generic body; the developer, driving the")
    print("   resource directly, gets a sentence that names the situation and the remedy.")

    print("\n2. Load a graph")
    first = DuckDBGraphResource.build_from_json(_payload("d.shop"))
    app.state.duckdb_graph = first
    print(f"   graph loaded: {first.execute_fetch_dicts('SELECT id FROM domain')}")

    print("\n3. All six endpoints answer, from one shared resource")
    for path, query in _DIAGRAM_ROUTES:
        response = client.get(path, params=query)
        print(f"   {path:38s} -> {response.status_code}")

    counting = _CountingGraph(DuckDBGraphResource.build_from_json(_payload("d.shop")))
    app.state.duckdb_graph = counting
    for path, query in _DIAGRAM_ROUTES:
        client.get(path, params=query)
    print(f"   the six requests together read the loaded graph {counting.reads} times")
    print("   (one object, resolved on every read — not one resource per call)")

    print("\n4. A second load replaces it for everyone")
    second = DuckDBGraphResource.build_from_json(_payload("d.warehouse"))
    app.state.duckdb_graph = second
    after = client.get("/api/v1/list-domains")
    print(f"   GET /api/v1/list-domains -> {after.status_code} {after.text}")
    print("   Nothing was restarted and no endpoint holds a graph of its own.")


if __name__ == "__main__":
    main()

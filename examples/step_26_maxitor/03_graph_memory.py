"""
03_graph_memory.py — what a built graph costs, and which broken graph is refused

Maxitor builds an in-memory DuckDB database from a service's ``graph-json``. A built graph
used to spend most of its memory on the 64 indexes and 21 primary keys the build created,
even though no diagram query reads through an index. This example shows the graph that
ships now: no index, no primary key, and a duplicate node id is refused by name.

The cases, with the real output at the bottom:

  1. what a built graph costs, by DuckDB's own memory tag, and that its catalogue has no
     index and no primary key;
  2. a payload with one node listed twice — the build raises and names the id;
  3. the same payload through the application — 422 with the reason, nothing stored;
  4. the same id in two different node tables — accepted, as before;
  5. an empty graph — builds and answers with empty views.

Output:

    1. What a built graph costs
       IN_MEMORY_TABLE      0.57 MiB
       total                0.57 MiB
       indexes: 0, primary keys: 0

    2. A duplicate node is refused by name
       ValueError: Graph has a duplicate node id "d.dup.Dom" in table "domain".

    3. The same duplicate through Maxitor
       GET /api/v1/list-domains -> 422 {'detail': 'Graph has a duplicate node id "d.dup.Dom" in table "domain".'}
       stored for that source: 0 graphs

    4. The same id in two node tables
       domain + lifecycle -> 2 nodes

    5. An empty graph
       nodes: 0

Run:
    uv run python examples/step_26_maxitor/03_graph_memory.py

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (system graph)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from maxitor.front.api.app import create_app
from maxitor.front.api.graph_store import GraphEntry, GraphStore
from maxitor.front.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://duplicate.test/graph-json"
_EMPTY_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
_MIB = 1024 * 1024


def _domain(node_id: str) -> dict[str, Any]:
    """Return a minimal Domain node."""
    return {"id": node_id, "label": node_id, "type": "Domain", "properties": {"name": node_id, "description": ""}}


def _lifecycle(node_id: str) -> dict[str, Any]:
    """Return a minimal Lifecycle node."""
    return {"id": node_id, "label": node_id, "type": "Lifecycle", "properties": {"field_name": "status"}}


def _state(node_id: str, state_key: str, node_type: str) -> dict[str, Any]:
    """Return a minimal lifecycle state node."""
    return {
        "id": node_id,
        "label": state_key,
        "type": node_type,
        "properties": {"lifecycle_class_id": "x.Status", "state_key": state_key},
    }


def _payload(*nodes: dict[str, Any], edges: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
    """Return a coordinator payload with the given nodes and edges."""
    return {"schema_version": "1.0", "nodes": list(nodes), "edges": list(edges)}


def _tiny_graph() -> dict[str, Any]:
    """Return a four-node graph: one domain, one lifecycle and one state."""
    lifecycle_id = "e.x.Entity:lifecycle:status"
    return _payload(
        _domain("d.default.Dom"),
        _lifecycle(lifecycle_id),
        _state(f"{lifecycle_id}:draft", "draft", "StateInitial"),
        edges=(
            {
                "source_id": lifecycle_id,
                "target_id": f"{lifecycle_id}:draft",
                "type": "lifecycle_contains_state",
                "relationship": "COMPOSITION",
                "is_dag": False,
                "properties": {"state_key": "draft"},
            },
        ),
    )


def _duplicate_payload() -> dict[str, Any]:
    """Return a payload that lists the same Domain node twice."""
    return _payload(_domain("d.dup.Dom"), _domain("d.dup.Dom"))


def _application_client() -> tuple[TestClient, GraphStore]:
    """Return a client over a store whose builder builds the duplicated payload."""

    async def builder(source: str) -> GraphEntry:
        graph = DuckDBGraphResource.build_from_json(_duplicate_payload())
        return GraphEntry(source=source, graph=graph, sidebar=_EMPTY_SIDEBAR, last_read=0.0)

    app = create_app()
    store = GraphStore(builder)
    app.state.graph_store = store
    return TestClient(app, raise_server_exceptions=False), store


def main() -> None:
    """Run the five cases and print what each one returns."""
    print("1. What a built graph costs")
    resource = DuckDBGraphResource.build_from_json(_tiny_graph())
    rows = resource.execute_fetch_dicts(
        "SELECT tag, memory_usage_bytes FROM duckdb_memory() WHERE memory_usage_bytes > 0"
    )
    total = sum(int(row["memory_usage_bytes"]) for row in rows) / _MIB
    for row in sorted(rows, key=lambda r: str(r["tag"])):
        print(f"   {row['tag']:<20} {int(row['memory_usage_bytes']) / _MIB:.2f} MiB")
    print(f"   {'total':<20} {total:.2f} MiB")
    indexes = resource.execute_fetch_dicts("SELECT index_name FROM duckdb_indexes()")
    keys = resource.execute_fetch_dicts(
        "SELECT constraint_name FROM duckdb_constraints() WHERE constraint_type = 'PRIMARY KEY'",
    )
    print(f"   indexes: {len(indexes)}, primary keys: {len(keys)}")

    print("\n2. A duplicate node is refused by name")
    try:
        DuckDBGraphResource.build_from_json(_duplicate_payload())
    except ValueError as error:
        print(f"   ValueError: {error}")

    print("\n3. The same duplicate through Maxitor")
    client, store = _application_client()
    response = client.get("/api/v1/list-domains", params={"source": _SOURCE})
    print(f"   GET /api/v1/list-domains -> {response.status_code} {response.json()}")
    print(f"   stored for that source: {store.held} graphs")

    print("\n4. The same id in two node tables")
    shared = DuckDBGraphResource.build_from_json(_payload(_domain("shared.id"), _lifecycle("shared.id")))
    print(f"   domain + lifecycle -> {len(shared.execute_fetch_dicts('SELECT id FROM nodes'))} nodes")

    print("\n5. An empty graph")
    empty = DuckDBGraphResource.build_from_json(_payload())
    print(f"   nodes: {len(empty.execute_fetch_dicts('SELECT id FROM nodes'))}")


if __name__ == "__main__":
    main()

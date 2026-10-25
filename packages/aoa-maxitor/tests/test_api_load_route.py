# packages/aoa-maxitor/tests/test_api_load_route.py
"""Tests for POST /api/load: an explicit reload rebuilds the named source and nothing else."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.graph_store import BUSY_DETAIL, GraphBuildError, GraphEntry, GraphStore, GraphStoreBusyError
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
_SOURCE_X = "https://x.aoa.run/graph-json"
_SOURCE_Y = "https://y.aoa.run/graph-json"
_DOMAIN_X = "d.x.Dom"
_DOMAIN_Y = "d.y.Dom"


def _graph(domain: str) -> DuckDBGraphResource:
    """Return a real graph holding one domain."""
    return DuckDBGraphResource.build_from_json(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "id": domain,
                    "label": domain,
                    "type": "Domain",
                    "properties": {"name": domain, "description": ""},
                },
            ],
            "edges": [],
        },
    )


class RevisionBuilder:
    """A builder whose every build of a source is a new revision, and which can be told to fail."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail = False
        self._revisions: dict[str, int] = {}

    async def __call__(self, source: str) -> GraphEntry:
        """Record the call and return that source's next revision, or fail."""
        self.calls.append(source)
        if self.fail:
            raise GraphBuildError("service is down")
        self._revisions[source] = self._revisions.get(source, 0) + 1
        domain = _DOMAIN_X if source == _SOURCE_X else _DOMAIN_Y
        return GraphEntry(
            source=source,
            graph=_graph(f"{domain}:v{self._revisions[source]}"),
            sidebar=_SIDEBAR,
            last_read=0.0,
        )


def _client(builder: RevisionBuilder | None = None) -> tuple[TestClient, Any, RevisionBuilder]:
    """Return a client over an application with a store that serves two sources."""
    app = create_app()
    real_builder = builder or RevisionBuilder()
    store = GraphStore(real_builder)
    app.state.graph_store = store
    return TestClient(app, raise_server_exceptions=False), store, real_builder


def _list_domains(client: TestClient, source: str) -> list[str]:
    """Return the domain qualnames the list-domains route answers for ``source``."""
    response = client.get("/api/v1/list-domains", params={"source": source})
    assert response.status_code == 200, response.text[:200]
    return [row["qualname"] for row in response.json()["list_domains"]]


# ─── Reload one source ──────────────────────────────────────────────────────


def test_reload_rebuilds_only_the_named_source() -> None:
    """Reading X is unaffected by a reload of Y: X's graph is the one built before it."""
    client, store, _ = _client()
    before = _list_domains(client, _SOURCE_X)
    _list_domains(client, _SOURCE_Y)

    response = client.post("/api/load", json={"service_url": _SOURCE_Y})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert _list_domains(client, _SOURCE_X) == before
    assert store.held == 2


def test_reload_replaces_the_held_graph_of_that_source() -> None:
    """The reloaded source answers from the new build, not from the graph held before it."""
    client, _, builder = _client()
    assert _list_domains(client, _SOURCE_Y) == [_DOMAIN_Y + ":v1"]

    client.post("/api/load", json={"service_url": _SOURCE_Y})

    assert _list_domains(client, _SOURCE_Y) == [_DOMAIN_Y + ":v2"]
    assert builder.calls.count(_SOURCE_Y) == 2


def test_a_failing_reload_keeps_the_previous_graph_and_answers_422() -> None:
    """A reload that cannot build reports the reason and leaves the held graph answering."""
    client, _, builder = _client()
    held = _list_domains(client, _SOURCE_Y)

    builder.fail = True
    response = client.post("/api/load", json={"service_url": _SOURCE_Y})

    assert response.status_code == 422
    assert response.json() == {"detail": "service is down"}
    builder.fail = False
    assert _list_domains(client, _SOURCE_Y) == held


def test_an_unreachable_service_answers_422_with_the_loads_reason() -> None:
    """The real load path still reports a service it cannot reach, with the shape it always had."""
    app = create_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/load", json={"service_url": "http://127.0.0.1:1/"})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert response.json()["detail"]


def test_a_busy_store_answers_503_with_the_pause() -> None:
    """No free build slot: the reload is refused with Retry-After and the entry is not touched."""

    class _BusyStore:
        held = 0

        async def reload(self, source: str) -> GraphEntry:
            """Refuse the reload, as a store that waited out its slot limit does."""
            raise GraphStoreBusyError(BUSY_DETAIL)

    app = create_app()
    app.state.graph_store = _BusyStore()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/load", json={"service_url": _SOURCE_Y})

    assert response.status_code == 503
    assert response.json() == {"detail": BUSY_DETAIL}
    assert response.headers["retry-after"] == "5"


# ─── One key for one source ─────────────────────────────────────────────────


def test_an_awkward_address_is_one_key_for_a_read_and_a_reload() -> None:
    """`&`, `+`, `%2F` and a space survive both paths: one entry, replaced by the reload (FR-027)."""
    awkward = "https://awkward.test/a&b+c/d e/graph-json"
    client, store, builder = _client()

    read = client.get("/api/v1/list-domains", params={"source": awkward})
    assert read.status_code == 200, read.text[:200]
    assert builder.calls == [awkward]

    reloaded = client.post("/api/load", json={"service_url": awkward})

    assert reloaded.status_code == 200
    assert builder.calls == [awkward, awkward]
    assert store.held == 1
    assert store.held_sources() == (awkward,)

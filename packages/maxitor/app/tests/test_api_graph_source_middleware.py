# packages/maxitor/app/tests/test_api_graph_source_middleware.py
"""Tests for GraphSourceMiddleware: a read names its source, and gets that source's graph."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from maxitor.viewer.api.app import create_app
from maxitor.viewer.api.graph_source_middleware import (
    MISSING_SOURCE_DETAIL,
    GraphSourceMiddleware,
    current_graph_entry,
)
from maxitor.viewer.api.graph_store import (
    BUSY_DETAIL,
    GraphBuildError,
    GraphEntry,
    GraphStore,
    GraphStoreBusyError,
)
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE_A = "https://a.test/graph-json"
_SOURCE_B = "https://b.test/graph-json"
_DOMAIN_A = "d.a.Dom"
_DOMAIN_B = "d.b.Dom"
_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])


def _graph(domain: str) -> DuckDBGraphResource:
    """Return a real in-process graph holding one domain, so diagram actions can query it."""
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


class FakeClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward."""
        self.now += seconds


def _source_with_domain(domain: str) -> GraphEntry:
    """Return an entry whose graph stands for one domain."""
    return GraphEntry(source=f"https://{domain}.test/graph-json", graph=domain, sidebar=_SIDEBAR, last_read=0.0)


def _store(*domains: str, calls: list[str] | None = None, clock: Any = None) -> GraphStore:
    """Return a store that answers one domain per source and records every build."""
    by_source = {f"https://{domain}.test/graph-json": _graph(domain) for domain in domains}

    async def builder(source: str) -> GraphEntry:
        if calls is not None:
            calls.append(source)
        return GraphEntry(source=source, graph=by_source[source], sidebar=_SIDEBAR, last_read=0.0)

    kwargs: dict[str, Any] = {}
    if clock is not None:
        kwargs["clock"] = clock
    return GraphStore(builder, **kwargs)


def _client(store: GraphStore) -> TestClient:
    """Return a client over a real application whose store is ``store``."""
    app = create_app()
    app.state.graph_store = store
    return TestClient(app, raise_server_exceptions=False)


class _BusyStore:
    """A store whose every read finds no free build slot."""

    held = 0
    running = 0
    queued = 0

    async def acquire(self, source: str) -> GraphEntry:
        """Refuse the read, as a store that waited out its slot limit does."""
        raise GraphStoreBusyError(BUSY_DETAIL)


class _FailingStore:
    """A store whose every read finds its source unbuildable."""

    held = 0
    running = 0
    queued = 0

    def __init__(self, reason: str) -> None:
        self._reason = reason

    async def acquire(self, source: str) -> GraphEntry:
        """Refuse the read with the reason a failed build would carry."""
        raise GraphBuildError(self._reason)


# ─── Missing source ─────────────────────────────────────────────────────────


def test_a_read_without_a_source_is_refused_by_name() -> None:
    """400 with the exact detail, before any action runs."""
    client = _client(_store(_DOMAIN_A))

    for path in ("/api/v1/full-graph", "/api/sidebar"):
        response = client.get(path)
        assert response.status_code == 400
        assert response.json() == {"detail": MISSING_SOURCE_DETAIL}


def test_a_blank_source_is_refused_like_a_missing_one() -> None:
    """A source of spaces names nothing either."""
    client = _client(_store(_DOMAIN_A))

    response = client.get("/api/sidebar", params={"source": "   "})

    assert response.status_code == 400
    assert response.json() == {"detail": MISSING_SOURCE_DETAIL}


# ─── A source that cannot be built ──────────────────────────────────────────


def test_an_unbuildable_source_answers_422_with_the_reason_and_stores_nothing() -> None:
    """The refusal names the build's reason and leaves the store empty, so the next read retries."""
    client = _client(_store())
    client.app.state.graph_store = _FailingStore("service is down")
    store: Any = client.app.state.graph_store

    response = client.get("/api/sidebar", params={"source": "https://down.test/graph-json"})

    assert response.status_code == 422
    assert response.json() == {"detail": "service is down"}
    assert store.held == 0


# ─── One source, one graph, one build ───────────────────────────────────────


def test_a_cold_read_builds_one_graph_and_repeats_reuse_it() -> None:
    """The first read builds; two more reads of the same source cost nothing."""
    calls: list[str] = []
    store = _store(_DOMAIN_A, calls=calls)
    client = _client(store)

    for _ in range(3):
        response = client.get("/api/sidebar", params={"source": f"https://{_DOMAIN_A}.test/graph-json"})
        assert response.status_code == 200

    assert calls == [f"https://{_DOMAIN_A}.test/graph-json"]
    assert store.held == 1


def test_interleaved_reads_of_two_sources_never_mix() -> None:
    """Fifty reads in random order, alternating two clients, all answer their own source (SC-001)."""
    store = _store(_DOMAIN_A, _DOMAIN_B)
    client = _client(store)
    sources = [f"https://{_DOMAIN_A}.test/graph-json", f"https://{_DOMAIN_B}.test/graph-json"]

    for index in range(50):
        source = sources[index % 2]
        response = client.get("/api/v1/list-domains", params={"source": source})
        assert response.status_code == 200, response.text[:200]
        expected, other = (_DOMAIN_A, _DOMAIN_B) if index % 2 == 0 else (_DOMAIN_B, _DOMAIN_A)
        assert expected in response.text
        assert other not in response.text


def test_a_read_for_one_source_after_another_was_loaded_answers_the_first() -> None:
    """The previous read's graph never answers this one (FR-021 on the server side)."""
    store = _store(_DOMAIN_A, _DOMAIN_B)
    client = _client(store)

    client.get("/api/v1/list-domains", params={"source": f"https://{_DOMAIN_B}.test/graph-json"})
    response = client.get("/api/v1/list-domains", params={"source": f"https://{_DOMAIN_A}.test/graph-json"})

    assert _DOMAIN_A in response.text
    assert _DOMAIN_B not in response.text


def test_a_source_unread_for_hours_is_answered_without_a_new_build() -> None:
    """A graph stays until the store's limit: three hours later the read answers from it (spec 028, FR-080)."""
    clock = FakeClock()
    calls: list[str] = []
    store = _store(_DOMAIN_A, calls=calls, clock=clock)
    client = _client(store)
    source = f"https://{_DOMAIN_A}.test/graph-json"

    assert client.get("/api/sidebar", params={"source": source}).status_code == 200
    clock.advance(3 * 3600.0)
    response = client.get("/api/sidebar", params={"source": source})

    assert response.status_code == 200
    assert calls == [source]


# ─── One request, one graph ─────────────────────────────────────────────────


def test_one_request_reads_one_graph_even_when_its_source_is_rebuilt_mid_request() -> None:
    """A reload between two queries of one request cannot mix two graphs (FR-007)."""
    calls: list[str] = []
    store = _store(_DOMAIN_A, calls=calls)

    async def builder(source: str) -> GraphEntry:
        calls.append(source)
        return GraphEntry(source=source, graph=f"graph-{len(calls)}", sidebar=_SIDEBAR, last_read=0.0)

    store = GraphStore(builder)
    app = FastAPI()
    app.state.graph_store = store

    @app.get("/api/v1/twice")
    async def twice(request: Request) -> dict[str, Any]:
        first = current_graph_entry()
        await store.reload(request.query_params["source"])
        second = current_graph_entry()
        assert first is not None and second is not None
        return {"same": first is second, "graph": first.graph}

    app.add_middleware(GraphSourceMiddleware)
    client = TestClient(app)

    response = client.get("/api/v1/twice", params={"source": f"https://{_DOMAIN_A}.test/graph-json"})

    assert response.json() == {"same": True, "graph": "graph-1"}
    assert calls == [f"https://{_DOMAIN_A}.test/graph-json", f"https://{_DOMAIN_A}.test/graph-json"]


# ─── Settings ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("MAXITOR_MAX_GRAPHS", "0"),
        ("MAXITOR_MAX_GRAPHS", "many"),
        ("MAXITOR_MAX_CONCURRENT_BUILDS", "2.5"),
    ],
)
def test_an_invalid_setting_stops_the_application_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    """A setting that is not a positive number refuses to start, and says which one."""
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=name):
        create_app()


# ─── CORS, the busy answer, and health ──────────────────────────────────────


def test_refusals_carry_the_cors_headers_on_another_origin() -> None:
    """400 and 422 answered to an origin request carry ``Access-Control-Allow-Origin`` (FR-026)."""
    client = _client(_store(_DOMAIN_A))
    headers = {"Origin": "https://other.example"}

    missing = client.get("/api/sidebar", headers=headers)
    assert missing.status_code == 400
    assert missing.headers["access-control-allow-origin"] == "*"

    client.app.state.graph_store = _FailingStore("service is down")
    failed = client.get("/api/sidebar", params={"source": "https://x.test/graph-json"}, headers=headers)
    assert failed.status_code == 422
    assert failed.headers["access-control-allow-origin"] == "*"


def test_a_busy_store_answers_503_with_the_pause_and_exposes_it() -> None:
    """503 carries the exact detail, ``Retry-After: 5``, and the header is readable cross-origin."""
    client = _client(_BusyStore())  # type: ignore[arg-type]
    headers = {"Origin": "https://other.example"}

    response = client.get("/api/sidebar", params={"source": "https://x.test/graph-json"}, headers=headers)

    assert response.status_code == 503
    assert response.json() == {"detail": BUSY_DETAIL}
    assert response.headers["retry-after"] == "5"
    assert response.headers["access-control-allow-origin"] == "*"
    assert "Retry-After" in response.headers["access-control-expose-headers"]


def test_an_options_preflight_passes_through_the_middleware() -> None:
    """A preflight names no source and is answered by CORS, not refused with a 400."""
    client = _client(_store(_DOMAIN_A))

    response = client.options(
        "/api/v1/full-graph",
        headers={"Origin": "https://other.example", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_health_reports_the_stores_load() -> None:
    """The health answer shows held graphs and builds, running and queued (FR-028)."""
    client = _client(_store(_DOMAIN_A))
    client.get("/api/sidebar", params={"source": f"https://{_DOMAIN_A}.test/graph-json"})

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "graphs_held": 1, "builds_running": 0, "builds_queued": 0}

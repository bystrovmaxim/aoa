# packages/aoa-maxitor/tests/test_api_graph_burst.py
"""A burst of readers on one deep link: one download, one build, and no re-check on a timer."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import httpx

from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.graph_store import GraphEntry, GraphStore
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_SOURCE = "https://burst.aoa.run/graph-json"
_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
_READERS = 300


class FakeClock:
    """A monotonic clock the test moves by hand, so an hour costs nothing."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake time forward."""
        self.now += seconds


def _graph() -> DuckDBGraphResource:
    """Return a real in-process graph, so the diagram route has something to query."""
    return DuckDBGraphResource.build_from_json(
        {
            "schema_version": "1.0",
            "nodes": [
                {
                    "id": "d.burst.Dom",
                    "label": "d.burst.Dom",
                    "type": "Domain",
                    "properties": {"name": "d.burst.Dom", "description": ""},
                },
            ],
            "edges": [],
        },
    )


class CountingBuilder:
    """A builder that counts builds and takes long enough for the readers to overlap."""

    def __init__(self, graph: DuckDBGraphResource, delay: float = 0.01) -> None:
        self.calls: list[str] = []
        self._graph = graph
        self._delay = delay

    async def __call__(self, source: str) -> GraphEntry:
        """Record the build, let other readers arrive, then return the entry."""
        self.calls.append(source)
        await asyncio.sleep(self._delay)
        return GraphEntry(source=source, graph=self._graph, sidebar=_SIDEBAR, last_read=0.0)


def _application(store: GraphStore) -> Any:
    """Return the real application with ``store`` in place of the one it built."""
    app = create_app()
    app.state.graph_store = store
    return app


async def _get(client: httpx.AsyncClient, path: str) -> httpx.Response:
    """Read one graph endpoint for the burst's source."""
    return await client.get(path, params={"source": _SOURCE})


async def test_three_hundred_readers_of_one_link_cost_one_build() -> None:
    """600 reads of one cold source, 300 of each graph endpoint, all answered by one build (SC-008)."""
    builder = CountingBuilder(_graph())
    store = GraphStore(builder)
    app = _application(store)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://maxitor.test") as client:
        requests = [
            _get(client, "/api/sidebar" if index % 2 == 0 else "/api/v1/full-graph")
            for index in range(2 * _READERS)
        ]
        responses = await asyncio.gather(*requests)

    statuses = [response.status_code for response in responses]
    assert statuses.count(200) == 2 * _READERS, f"failures: {[s for s in statuses if s != 200][:5]}"
    assert builder.calls == [_SOURCE]
    assert store.held == 1


async def test_a_held_graph_is_never_downloaded_again_on_a_timer() -> None:
    """An hour later the same source answers from the held graph: no new download (SC-002, FR-012)."""
    clock = FakeClock()
    builder = CountingBuilder(_graph())
    store = GraphStore(builder, clock=clock)
    app = _application(store)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://maxitor.test") as client:
        first = await client.get("/api/v1/full-graph", params={"source": _SOURCE})
        clock.advance(3600.0)
        later = await client.get("/api/v1/full-graph", params={"source": _SOURCE})

    assert (first.status_code, later.status_code) == (200, 200)
    assert builder.calls == [_SOURCE]

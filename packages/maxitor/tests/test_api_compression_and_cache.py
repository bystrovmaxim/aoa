# packages/maxitor/tests/test_api_compression_and_cache.py
"""
Compression and cache headers of every answer — gzip above 500 bytes, immutable hashed assets, a page revalidated on every open.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Hold the two promises of issue #245's phase 2 in place:

- an answer above 500 bytes is gzipped when the client accepts gzip, and an answer
  below it is not;
- a file under ``assets/`` whose name carries a content hash is cacheable for a year
  and never changes, while ``index.html`` is revalidated on every open, so a new
  release is picked up on the next visit;
- a refusal from ``GraphSourceMiddleware`` keeps its status, its ``detail`` and its
  cross-origin headers, including the ``Retry-After`` a client reads to time a retry.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TestClient ─► GZipMiddleware ─► CORSMiddleware ─► GraphSourceMiddleware ─► routes / mounts

``create_app`` is built over a temporary static directory, so the real static mount and the
real middleware order are exercised. The graph read runs through the real
``GraphSourceMiddleware`` over a store that answers one fixture graph, and a busy store
answers 503 with ``Retry-After``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from maxitor.viewer.api import app as app_module
from maxitor.viewer.api.app import create_app
from maxitor.viewer.api.graph_source_middleware import MISSING_SOURCE_DETAIL
from maxitor.viewer.api.graph_store import BUSY_DETAIL, GraphEntry, GraphStoreBusyError
from maxitor.viewer.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

_IMMUTABLE = "public, max-age=31536000, immutable"
_SOURCE = "https://fixture.test/graph-json"
_SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])
_ASSET = "/assets/index-abc123.js"


def _graph() -> DuckDBGraphResource:
    """Return a small real graph whose full-graph answer is larger than the compression threshold."""
    nodes = [
        {
            "id": f"d{index}.Dom",
            "label": f"d{index}.Dom",
            "type": "Domain",
            "properties": {"name": f"Domain {index}", "description": "a domain of the fixture"},
        }
        for index in range(12)
    ]
    return DuckDBGraphResource.build_from_json({"schema_version": "1.0", "nodes": nodes, "edges": []})


class _Store:
    """A store that answers one built fixture graph for any source."""

    held = 0
    running = 0
    queued = 0

    async def acquire(self, source: str) -> GraphEntry:
        """Return the fixture entry the graph routes read."""
        return GraphEntry(source=source, graph=_graph(), sidebar=_SIDEBAR, last_read=0.0)


class _BusyStore:
    """A store whose every read finds no free build slot."""

    held = 0
    running = 0
    queued = 0

    async def acquire(self, source: str) -> GraphEntry:
        """Refuse the read, as a store that waited out its slot limit does."""
        raise GraphStoreBusyError(BUSY_DETAIL)


@pytest.fixture()
def static_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A built client in a temporary directory, used instead of the package's own."""
    directory = tmp_path / "static"
    (directory / "assets").mkdir(parents=True)
    (directory / "index.html").write_text(
        "<!doctype html><html><head><title>Maxitor</title></head><body>fixture</body></html>",
        encoding="utf-8",
    )
    (directory / _ASSET.lstrip("/")).write_text("console.log('asset');\n" + "x" * 900, encoding="utf-8")
    monkeypatch.setattr(app_module, "_STATIC_DIR", directory)
    return directory


@pytest.fixture()
def client(static_dir: Path) -> TestClient:
    """A client over the real application and the temporary static directory."""
    application = create_app()
    application.state.graph_store = _Store()
    return TestClient(application, raise_server_exceptions=False)


# ─── A hashed asset ─────────────────────────────────────────────────────────


def test_a_hashed_asset_is_compressed_and_marked_immutable(client: TestClient, static_dir: Path) -> None:
    """Gzip for the client that accepts it, and a year of cache keyed to the content hash."""
    response = client.get(_ASSET, headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "accept-encoding" in response.headers["vary"].lower()
    assert response.headers["cache-control"] == _IMMUTABLE
    assert response.content == (static_dir / _ASSET.lstrip("/")).read_bytes()


def test_a_hashed_asset_without_gzip_is_sent_as_is(client: TestClient, static_dir: Path) -> None:
    """A client that does not accept gzip gets the file's own bytes, with the same lifetime."""
    response = client.get(_ASSET, headers={"Accept-Encoding": "identity"})

    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.headers["cache-control"] == _IMMUTABLE
    assert response.content == (static_dir / _ASSET.lstrip("/")).read_bytes()


# ─── The page ───────────────────────────────────────────────────────────────


def test_the_page_is_revalidated_on_every_open(client: TestClient) -> None:
    """``/`` and ``/index.html`` carry ``no-cache`` and an ``etag``, and the ``etag`` answers 304."""
    for path in ("/", "/index.html"):
        first = client.get(path)
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-cache"
        assert first.headers["etag"]

        again = client.get(path, headers={"If-None-Match": first.headers["etag"]})
        assert again.status_code == 304


def test_a_small_answer_is_not_compressed(client: TestClient) -> None:
    """The page is under the threshold, so compression could not make it smaller."""
    response = client.get("/", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert len(response.content) < 500


# ─── A graph read ───────────────────────────────────────────────────────────


def test_a_graph_read_is_compressed(client: TestClient) -> None:
    """The JSON of the full graph is gzipped like any other large answer."""
    response = client.get("/api/v1/full-graph", params={"source": _SOURCE}, headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["payload"]["nodes"]


# ─── Refusals keep their shape ──────────────────────────────────────────────


def test_a_read_without_a_source_keeps_its_status_detail_and_cors(client: TestClient) -> None:
    """400 with the exact detail, readable from another origin, still."""
    response = client.get("/api/v1/full-graph", headers={"Origin": "https://other.example"})

    assert response.status_code == 400
    assert response.json() == {"detail": MISSING_SOURCE_DETAIL}
    assert response.headers["access-control-allow-origin"] == "*"


def test_a_busy_store_keeps_retry_after_and_exposes_it(client: TestClient) -> None:
    """503 keeps ``Retry-After`` and the header that makes it readable cross-origin."""
    client.app.state.graph_store = _BusyStore()

    response = client.get(
        "/api/v1/full-graph",
        params={"source": _SOURCE},
        headers={"Origin": "https://other.example"},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": BUSY_DETAIL}
    assert response.headers["retry-after"] == "5"
    assert response.headers["access-control-allow-origin"] == "*"
    assert "Retry-After" in response.headers["access-control-expose-headers"]


# ─── A new release ──────────────────────────────────────────────────────────


def test_a_new_release_is_picked_up_on_the_next_open(client: TestClient, static_dir: Path) -> None:
    """The old ``etag`` no longer matches after a deploy, so the page comes back whole."""
    old = client.get("/")
    old_etag = old.headers["etag"]

    (static_dir / "index.html").write_text(
        "<!doctype html><html><head><title>Maxitor</title></head><body>next release</body></html>",
        encoding="utf-8",
    )

    response = client.get("/", headers={"If-None-Match": old_etag})

    assert response.status_code == 200
    assert b"next release" in response.content
    assert response.headers["etag"] != old_etag

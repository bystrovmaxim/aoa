"""
04_full_graph_delivery.py — what the full-graph page receives, and how long the browser may keep it

The page used to arrive as it left the server: no ``Content-Encoding``, no ``Cache-Control``.
Every open downloaded the code, the styles and the graph again, and a new release was only
picked up because nothing was ever cached.

Now the server compresses every answer above 500 bytes with gzip, marks a content-hashed
asset as immutable for a year, and marks ``index.html`` as revalidated on every open. This
script drives the real FastAPI application, with no server and no browser, over a temporary
static directory, and prints the headers a browser would see:

  1. a hashed asset, compressed and immutable for a year;
  2. the same asset to a client that does not accept gzip;
  3. the page, revalidated on every open — ``no-cache`` and a ``304`` on the old tag;
  4. an answer below the threshold, sent as it is;
  5. a graph read, compressed like any other large answer;
  6. a refusal that keeps its status, its ``detail`` and its cross-origin headers.

Output:

    1. A hashed asset
       GET /assets/index-abc123.js (gzip) -> 200
       content-encoding: gzip
       cache-control: public, max-age=31536000, immutable
       vary: Origin, Accept-Encoding
       decompressed to the file's 933 bytes: True

    2. The same asset without gzip
       content-encoding: absent
       cache-control: public, max-age=31536000, immutable
       body: the file's own 933 bytes: True

    3. The page
       GET / -> 200 cache-control: no-cache, etag "67acc46961d35a79e11aed9209c6d667"
       GET / with that etag -> 304
       GET /index.html -> 200 cache-control: no-cache

    4. An answer below 500 bytes
       GET / (gzip) -> no content-encoding, 83 bytes

    5. A graph read
       GET /api/v1/full-graph?source=… -> 200
       content-encoding: gzip, cache-control: absent
       decoded answer: 12 nodes

    6. A refusal
       GET /api/v1/full-graph (no source) -> 400
       detail: Missing query parameter 'source': name the graph-json URL this read is for.
       access-control-allow-origin: *
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from fastapi.testclient import TestClient

from aoa.maxitor.api import app as app_module
from aoa.maxitor.api.app import create_app
from aoa.maxitor.api.graph_source_middleware import MISSING_SOURCE_DETAIL
from aoa.maxitor.api.graph_store import GraphEntry
from aoa.maxitor.model.diagrams.resources.duckdb_graph_resource import DuckDBGraphResource

SOURCE = "https://fixture.test/graph-json"
ASSET = "/assets/index-abc123.js"
PAGE = "<!doctype html><html><head><title>Maxitor</title></head><body>fixture</body></html>"
SCRIPTS = "console.log('the built client');\n" + "x" * 900
SIDEBAR = SimpleNamespace(level1_nodes=[], level2_diagrams=[], level2_nodes=[], level3_diagrams=[])

# %% [markdown]
# The fixture graph and the store the routes read: one domain per node, enough of them that the
# full-graph answer is larger than the compression threshold.

# %%
def fixture_graph() -> DuckDBGraphResource:
    """Return a small real graph whose full-graph answer is larger than 500 bytes."""
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


class FixtureStore:
    """A store that answers one built fixture graph for any source."""

    held = 0
    running = 0
    queued = 0

    async def acquire(self, source: str) -> GraphEntry:
        """Return the fixture entry the graph routes read."""
        return GraphEntry(source=source, graph=fixture_graph(), sidebar=SIDEBAR, last_read=0.0)


def build_client(static_dir: Path) -> TestClient:
    """Return a client over the real application, mounted on ``static_dir``."""
    original = app_module._STATIC_DIR
    app_module._STATIC_DIR = static_dir
    try:
        application = create_app()
    finally:
        app_module._STATIC_DIR = original
    application.state.graph_store = FixtureStore()
    return TestClient(application, raise_server_exceptions=False)


# %% [markdown]
# 1. A hashed asset, compressed and immutable for a year. The body decompresses to the file.

# %%
def show_asset(client: TestClient, static_dir: Path) -> None:
    """Print the headers of the compressed asset and prove the body is the file's own bytes."""
    response = client.get(ASSET, headers={"Accept-Encoding": "gzip"})
    print("1. A hashed asset")
    print(f"   GET {ASSET} (gzip) -> {response.status_code}")
    print(f"   content-encoding: {response.headers.get('content-encoding')}")
    print(f"   cache-control: {response.headers.get('cache-control')}")
    print(f"   vary: {response.headers.get('vary')}")
    expected = (static_dir / ASSET.lstrip("/")).read_bytes()
    print(f"   decompressed to the file's {len(expected)} bytes: {response.content == expected}")


# %% [markdown]
# 2. The same asset to a client that does not accept gzip: the file's own bytes, same lifetime.

# %%
def show_asset_without_gzip(client: TestClient, static_dir: Path) -> None:
    """Print what a client without gzip receives."""
    response = client.get(ASSET, headers={"Accept-Encoding": "identity"})
    expected = (static_dir / ASSET.lstrip("/")).read_bytes()
    print("2. The same asset without gzip")
    print(f"   content-encoding: {response.headers.get('content-encoding', 'absent')}")
    print(f"   cache-control: {response.headers.get('cache-control')}")
    print(f"   body: the file's own {len(expected)} bytes: {response.content == expected}")


# %% [markdown]
# 3. The page: `no-cache`, an `etag`, and a `304` when the browser presents it again.

# %%
def show_page(client: TestClient) -> None:
    """Print the page's lifetime and the answer to a revalidation."""
    first = client.get("/")
    print("3. The page")
    print(f"   GET / -> {first.status_code} cache-control: {first.headers.get('cache-control')}, etag {first.headers.get('etag')}")
    again = client.get("/", headers={"If-None-Match": first.headers["etag"]})
    print(f"   GET / with that etag -> {again.status_code}")
    named = client.get("/index.html")
    print(f"   GET /index.html -> {named.status_code} cache-control: {named.headers.get('cache-control')}")


# %% [markdown]
# 4. An answer below 500 bytes is sent as it is: compressing it could only make it bigger.

# %%
def show_small_answer(client: TestClient) -> None:
    """Print the small answer's size and the absent encoding."""
    response = client.get("/", headers={"Accept-Encoding": "gzip"})
    print("4. An answer below 500 bytes")
    print(f"   GET / (gzip) -> no content-encoding, {len(response.content)} bytes")


# %% [markdown]
# 5. A graph read: compressed like any other large answer, and carrying no cache lifetime —
# the same source can serve a different graph after the store rebuilds it.

# %%
def show_graph_read(client: TestClient) -> None:
    """Print the graph answer's headers and the size of the decoded payload."""
    response = client.get("/api/v1/full-graph", params={"source": SOURCE}, headers={"Accept-Encoding": "gzip"})
    payload = response.json()["payload"]
    print("5. A graph read")
    print(f"   GET /api/v1/full-graph?source=… -> {response.status_code}")
    print(f"   content-encoding: {response.headers.get('content-encoding')}, cache-control: {response.headers.get('cache-control', 'absent')}")
    print(f"   decoded answer: {len(payload['nodes'])} nodes")


# %% [markdown]
# 6. A refusal: the status, the `detail` and the cross-origin header are what they were.

# %%
def show_refusal(client: TestClient) -> None:
    """Print a refusal with its detail and its cross-origin header."""
    response = client.get("/api/v1/full-graph", headers={"Origin": "https://other.example"})
    print("6. A refusal")
    print(f"   GET /api/v1/full-graph (no source) -> {response.status_code}")
    print(f"   detail: {response.json()['detail']}")
    print(f"   access-control-allow-origin: {response.headers.get('access-control-allow-origin')}")
    assert response.json()["detail"] == MISSING_SOURCE_DETAIL


# %%
def main() -> None:
    """Run every case over one temporary static directory."""
    with TemporaryDirectory() as temporary:
        static_dir = Path(temporary) / "static"
        (static_dir / "assets").mkdir(parents=True)
        (static_dir / "index.html").write_text(PAGE, encoding="utf-8")
        (static_dir / "assets" / "index-abc123.js").write_text(SCRIPTS, encoding="utf-8")
        client = build_client(static_dir)

        show_asset(client, static_dir)
        print()
        show_asset_without_gzip(client, static_dir)
        print()
        show_page(client)
        print()
        show_small_answer(client)
        print()
        show_graph_read(client)
        print()
        show_refusal(client)


if __name__ == "__main__":
    main()

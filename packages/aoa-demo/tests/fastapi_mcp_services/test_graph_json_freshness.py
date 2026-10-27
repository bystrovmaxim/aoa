# packages/aoa-demo/tests/fastapi_mcp_services/test_graph_json_freshness.py
"""
The demo's graph-json says whether it changed (spec 029, FR-061).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor keeps a held graph current by asking the service again with the tag of its
last answer. The demo serves ``/examples/model/graph-json`` through the FastAPI adapter
(1.3.0 or later), which tags the answer with an ``ETag`` and answers ``304`` with no
body when nothing changed — a check that costs a header, not the whole graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TestClient ──GET /examples/model/graph-json──► ETag ──If-None-Match──► 304
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from aoa.demo.fastapi_mcp_services.app_fastapi_service import app


def test_the_graph_json_carries_a_tag_and_a_repeated_read_gets_304() -> None:
    """The first read is tagged; the same tag back gets ``304`` and no body."""
    with TestClient(app) as client:
        first = client.get("/examples/model/graph-json")
        again = client.get("/examples/model/graph-json", headers={"If-None-Match": first.headers["etag"]})
    assert first.status_code == 200 and first.headers["etag"].startswith('"')
    assert (again.status_code, again.content) == (304, b"")

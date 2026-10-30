# packages/maxitor/front/tests/test_load_bare_graph.py
"""A graph-json address may answer the envelope or a bare graph (spec 037, FR-004); an error names the source by its label."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.model.core.source_label import label

from tests.fixtures.stand_in_port import GRAPH_B

ANSWERS = {"/bare": GRAPH_B, "/envelope": json.dumps({"coordinator_json": GRAPH_B.decode()}).encode(), "/neither": b'{"something": "else"}'}


@pytest.fixture(scope="module")
def service() -> Iterator[str]:
    """A local service answering a bare graph, an envelope and neither."""

    class Handler(BaseHTTPRequestHandler):
        """Answers each path with its body."""

        def do_GET(self) -> None:
            """Send the body of the path."""
            body = ANSWERS[self.path.split("?", 1)[0]]
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


def test_a_bare_graph_and_an_envelope_both_load_the_same(service: str) -> None:
    """The bare graph and the envelope carrying it draw the same graph."""
    with TestClient(create_app()) as client:
        for path in ("/bare", "/envelope"):
            assert client.get("/api/v1/full-graph", params={"source": f"{service}{path}"}).status_code == 200
        bare = client.app.state.graph_store.peek(f"{service}/bare")  # type: ignore[attr-defined]
        envelope = client.app.state.graph_store.peek(f"{service}/envelope")  # type: ignore[attr-defined]
        assert bare.graph is not None and envelope.graph is not None


def test_neither_is_refused_naming_the_source_by_its_label(service: str) -> None:
    """An answer that is neither: ``422``, the source named as ``origin#hash``, its path nowhere."""
    with TestClient(create_app()) as client:
        refused = client.get("/api/v1/full-graph", params={"source": f"{service}/neither"})
    assert refused.status_code == 422
    assert label(f"{service}/neither") in refused.json()["detail"] and "/neither" not in refused.json()["detail"]

# packages/maxitor/front/tests/test_rooms_page_checks.py
"""
Page checks in a room — the verdict a tab gets after it reports what it drew.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A tab reports its page with the client build, the graph fingerprint and the layout
hash it drew (spec 028, FR-090 … FR-093). The server answers ``check``: ``build`` is
``reload`` when the tab runs another client build, ``fingerprint`` is ``reread`` when
it drew another graph than the one held, and ``layout`` is ``off`` when, with build and
graph agreeing, its hash differs from the first one the room heard for that page and
settings. The fingerprint the tab compares is the one the sidebar route returns.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET /api/sidebar?source=… ──► fingerprint
    {"type": "page", build, fingerprint, layout_hash, settings_digest} ──► check
"""

from __future__ import annotations

import gzip
import threading
from collections.abc import Iterator
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.model.core.resources.static_bundle_resource import StaticBundleResource
from starlette.testclient import WebSocketTestSession

_FIXTURE = Path(__file__).parent / "fixtures" / "ref-graph-2026-10-26.json.gz"
_PAGE = "view=full-graph"
_SERVER_BUILD = "server-build"


@pytest.fixture(scope="module")
def source() -> Iterator[str]:
    """The frozen reference service, served on a free local port; yields its graph-json address."""
    body = gzip.decompress(_FIXTURE.read_bytes())

    class Handler(BaseHTTPRequestHandler):
        """Answers every GET with the reference graph."""

        def do_GET(self) -> None:
            """Send the graph."""
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/graph-json"
    finally:
        server.shutdown()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A fresh application whose static bundle reports a known build."""
    monkeypatch.setattr(StaticBundleResource, "build", lambda self: _SERVER_BUILD)
    with TestClient(create_app()) as test_client:
        yield test_client


def _join(stack: ExitStack, client: TestClient, room: str, participant: str, source: str = "") -> tuple[WebSocketTestSession, dict[str, Any]]:
    """Join ``room`` (``new`` opens one) and return the connection and its welcome."""
    query = {"participant": participant, "tab": f"{participant}-tab", "participant_name": participant, "start_page": _PAGE}
    if source:
        query["source"] = source
    ws = stack.enter_context(client.websocket_connect(f"/api/v1/rooms/{room}/live?{urlencode(query)}"))
    welcome: dict[str, Any] = ws.receive_json()
    assert welcome["type"] == "welcome", welcome
    return ws, welcome


def _check(ws: WebSocketTestSession, **report: str) -> dict[str, Any]:
    """Report the page with ``report`` and return the verdict, skipping room events in between."""
    ws.send_json({"type": "page", "page": _PAGE, **report})
    while True:
        event: dict[str, Any] = ws.receive_json()
        if event["type"] == "check":
            return event


def _fingerprint(client: TestClient, source: str) -> str:
    """The fingerprint the sidebar route gives for ``source``."""
    response = client.get("/api/sidebar", params={"source": source})
    assert response.status_code == 200
    fingerprint: str = response.json()["fingerprint"]
    return fingerprint


def test_the_welcome_names_the_server_build(client: TestClient, source: str) -> None:
    """The welcome carries the build Maxitor serves, so a tab can tell it is stale before drawing."""
    with ExitStack() as stack:
        _, welcome = _join(stack, client, "new", "anna", source)
    assert welcome["server_build"] == _SERVER_BUILD


def test_the_sidebar_fingerprint_is_the_held_graph(client: TestClient, source: str) -> None:
    """After a room built the graph, the sidebar returns the held fingerprint, not an empty one."""
    with ExitStack() as stack:
        _join(stack, client, "new", "anna", source)
        fingerprint = _fingerprint(client, source)
    assert len(fingerprint) == 64


def test_a_matching_picture_is_ok(client: TestClient, source: str) -> None:
    """Same build, same graph, first layout hash: everything is ok."""
    with ExitStack() as stack:
        anna, _ = _join(stack, client, "new", "anna", source)
        verdict = _check(anna, build=_SERVER_BUILD, fingerprint=_fingerprint(client, source), layout_hash="h1", settings_digest="d")
    assert verdict == {"type": "check", "build": "ok", "fingerprint": "ok", "layout": "ok"}


def test_another_build_is_told_to_reload(client: TestClient, source: str) -> None:
    """A tab running an older client build is told to reload."""
    with ExitStack() as stack:
        anna, _ = _join(stack, client, "new", "anna", source)
        verdict = _check(anna, build="old-build", fingerprint=_fingerprint(client, source))
    assert verdict["build"] == "reload"


def test_another_graph_is_told_to_reread(client: TestClient, source: str) -> None:
    """A tab that drew a graph other than the held one is told to re-read it."""
    with ExitStack() as stack:
        anna, _ = _join(stack, client, "new", "anna", source)
        verdict = _check(anna, build=_SERVER_BUILD, fingerprint="0" * 64)
    assert verdict["fingerprint"] == "reread"


def test_a_different_layout_for_the_same_page_and_settings_is_off(client: TestClient, source: str) -> None:
    """Anna's hash is the room's first; Boris with the same build, graph and settings but another hash is off."""
    with ExitStack() as stack:
        anna, welcome = _join(stack, client, "new", "anna", source)
        boris, _ = _join(stack, client, welcome["room"]["id"], "boris")
        fingerprint = _fingerprint(client, source)
        first = _check(anna, build=_SERVER_BUILD, fingerprint=fingerprint, layout_hash="h1", settings_digest="d")
        other = _check(boris, build=_SERVER_BUILD, fingerprint=fingerprint, layout_hash="h2", settings_digest="d")
        other_settings = _check(boris, build=_SERVER_BUILD, fingerprint=fingerprint, layout_hash="h2", settings_digest="e")
    assert first["layout"] == "ok"
    assert other["layout"] == "off"
    assert other_settings["layout"] == "ok"


def test_a_stale_tab_is_not_blamed_for_its_layout(client: TestClient, source: str) -> None:
    """A tab on an old build draws differently for that reason; its layout is not called off."""
    with ExitStack() as stack:
        anna, welcome = _join(stack, client, "new", "anna", source)
        boris, _ = _join(stack, client, welcome["room"]["id"], "boris")
        fingerprint = _fingerprint(client, source)
        _check(anna, build=_SERVER_BUILD, fingerprint=fingerprint, layout_hash="h1", settings_digest="d")
        verdict = _check(boris, build="old-build", fingerprint=fingerprint, layout_hash="h2", settings_digest="d")
    assert verdict == {"type": "check", "build": "reload", "fingerprint": "ok", "layout": "ok"}

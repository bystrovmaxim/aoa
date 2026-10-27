# packages/aoa-maxitor/tests/test_graph_store_controller.py
"""Tests for GraphStoreController and GraphSourceGateway: the store and the download, as resources."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

import pytest

from aoa.maxitor.api.graph_store import GraphBuildError, GraphEntry, GraphStore
from aoa.maxitor.model.core.resources import Document, GraphSourceGateway, GraphStoreController, Unreachable

# ─── GraphStoreController ───────────────────────────────────────────────────


def _store(fail: dict[str, bool] | None = None) -> GraphStore:
    """A store whose builder numbers its builds per source, and fails while ``fail["now"]`` is set."""
    counter: dict[str, int] = {}

    async def builder(source: str) -> GraphEntry:
        if fail is not None and fail.get("now"):
            raise GraphBuildError("down")
        counter[source] = counter.get(source, 0) + 1
        marker = f"{source}#{counter[source]}"
        return GraphEntry(source=source, graph=cast(Any, marker), sidebar=cast(Any, marker), last_read=0.0)

    return GraphStore(builder)


async def test_entry_reads_without_building_and_acquire_builds() -> None:
    """``entry`` answers only what is held; ``acquire`` builds what is not."""
    controller = GraphStoreController(_store())

    assert controller.entry("A") is None
    built = await controller.acquire("A")
    assert cast(str, built.graph) == "A#1"
    assert controller.entry("A") is built
    assert controller.held_sources() == ("A",)


async def test_replace_swaps_only_on_success() -> None:
    """``replace`` rebuilds and swaps; a failed rebuild keeps the entry already held."""
    fail = {"now": False}
    controller = GraphStoreController(_store(fail))
    await controller.acquire("A")

    fresh = await controller.replace("A")
    assert cast(str, fresh.graph) == "A#2"

    fail["now"] = True
    with pytest.raises(GraphBuildError):
        await controller.replace("A")
    assert cast(str, cast(GraphEntry, controller.entry("A")).graph) == "A#2"


async def test_checks_are_marked_on_the_held_entry() -> None:
    """``mark_checked`` and ``set_checking`` write the held entry; an unknown source is ignored."""
    controller = GraphStoreController(_store())
    await controller.acquire("A")

    controller.mark_checked("A", 123.0)
    controller.set_checking("A", True)
    assert cast(GraphEntry, controller.entry("A")).last_checked == 123.0
    assert controller.is_checking("A") is True
    controller.set_checking("A", False)
    assert controller.is_checking("A") is False

    controller.mark_checked("missing", 1.0)
    controller.set_checking("missing", True)
    assert controller.is_checking("missing") is False


# ─── GraphSourceGateway ─────────────────────────────────────────────────────

_BODY = b'{"coordinator_json": "{}"}'


class _Handler(BaseHTTPRequestHandler):
    """Answers ``/ok`` with a body and validators, and ``/missing`` with 404."""

    def do_GET(self) -> None:
        """Serve the two test paths."""
        if self.path == "/ok":
            self.send_response(200)
            self.send_header("ETag", '"v1"')
            self.send_header("Last-Modified", "Tue, 27 Oct 2026 10:00:00 GMT")
            self.send_header("Content-Length", str(len(_BODY)))
            self.end_headers()
            self.wfile.write(_BODY)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args: Any) -> None:
        """Keep the test output quiet."""


@pytest.fixture
def server() -> Iterator[str]:
    """A local HTTP server for the gateway; yields its base address."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()


async def test_fetch_returns_the_body_with_its_identity(server: str) -> None:
    """A 2xx answer comes back as a ``Document`` with the body's SHA-256 and the validators."""
    gateway = GraphSourceGateway()
    try:
        answer = await gateway.fetch(f"{server}/ok")
    finally:
        await gateway.aclose()

    assert answer == Document(
        body=_BODY,
        sha256=hashlib.sha256(_BODY).hexdigest(),
        etag='"v1"',
        last_modified="Tue, 27 Oct 2026 10:00:00 GMT",
    )


async def test_fetch_reports_an_http_error_with_its_status(server: str) -> None:
    """An error status is an ``Unreachable`` that carries it, never an exception."""
    gateway = GraphSourceGateway()
    try:
        answer = await gateway.fetch(f"{server}/missing")
    finally:
        await gateway.aclose()

    assert answer == Unreachable(reason="HTTP 404", status=404)


async def test_fetch_reports_a_service_that_does_not_answer() -> None:
    """A refused connection is an ``Unreachable`` without a status, never an exception."""
    gateway = GraphSourceGateway(timeout=2.0)
    try:
        answer = await gateway.fetch("http://127.0.0.1:9/graph-json")
    finally:
        await gateway.aclose()

    assert isinstance(answer, Unreachable)
    assert answer.status is None
    assert answer.reason

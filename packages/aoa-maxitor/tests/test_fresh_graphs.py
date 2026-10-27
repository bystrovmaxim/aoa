# packages/aoa-maxitor/tests/test_fresh_graphs.py
"""
Fresh graphs — held graphs follow their services, and keep what they have when a service fails.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each test drives the check actions of spec 028 (FR-071 … FR-075) on Maxitor's real machine and
store, against a local ``graph-json`` service whose body, ``ETag`` and availability the test
controls and whose requests it counts: an unchanged service, a changed one, a broken one, an
unreachable one, two checks at once, a source nobody watches, and what the log says.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    local service (body · ETag · up/down · request count)
        ▲ fetch / fetch_if_changed
    GraphSourceGateway ◄── CheckSourceAction / CheckDueSourcesAction / GraphFingerprintAction
        │ build                       ▲ machine.run
    GraphStore ──► GraphStoreController
"""

from __future__ import annotations

import asyncio
import gzip
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.model import ParamsStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.maxitor.api.graph_store import GraphStore, build_graph_entry
from aoa.maxitor.model.core.actions.check_due_sources_action import CheckDueSourcesAction
from aoa.maxitor.model.core.actions.check_source_action import CheckSourceAction, CheckSourceParams
from aoa.maxitor.model.core.actions.graph_fingerprint_action import GraphFingerprintAction, GraphFingerprintParams
from aoa.maxitor.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from aoa.maxitor.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from aoa.maxitor.model.core.resources.open_tabs_registry import OPEN_TABS_CONNECTION_KEY, OpenTabsRegistry
from aoa.maxitor.model.core.resources.source_checks import SOURCE_CHECKS_CONNECTION_KEY, SourceChecks
from aoa.maxitor.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry

_FIXTURE = Path(__file__).parent / "fixtures" / "ref-graph-2026-10-26.json.gz"
_BODY = gzip.decompress(_FIXTURE.read_bytes())
#: The same model, written differently: another body, so another fingerprint.
_CHANGED_BODY = json.dumps(json.loads(_BODY), indent=1).encode()


@dataclass
class Service:
    """What the local service answers, and how often it was asked."""

    body: bytes = _BODY
    etag: str | None = None
    up: bool = True
    requests: int = 0
    conditional: list[str] = field(default_factory=list)


@pytest.fixture
def service() -> Iterator[tuple[Service, str]]:
    """A local graph-json service the test controls; yields it and its address."""
    state = Service()

    class Handler(BaseHTTPRequestHandler):
        """Answers as ``state`` says: 503 when down, 304 to a matching If-None-Match, else the body."""

        def do_GET(self) -> None:
            """Answer one request."""
            state.requests += 1
            asked = self.headers.get("If-None-Match")
            if asked:
                state.conditional.append(asked)
            if not state.up:
                self.send_response(503)
                self.end_headers()
                return
            if state.etag and asked == state.etag:
                self.send_response(304)
                self.end_headers()
                return
            self.send_response(200)
            if state.etag:
                self.send_header("ETag", state.etag)
            self.send_header("Content-Length", str(len(state.body)))
            self.end_headers()
            self.wfile.write(state.body)

        def log_message(self, *args: Any) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield state, f"http://127.0.0.1:{server.server_address[1]}/graph-json"
    finally:
        server.shutdown()


@dataclass
class Maxitor:
    """The pieces ``create_app`` wires, built the same way."""

    machine: ActionProductMachine
    store: GraphStore
    graphs: GraphStoreController
    gateway: GraphSourceGateway
    rooms: RoomRegistry
    tabs: OpenTabsRegistry
    checks: SourceChecks

    def check_connections(self) -> dict[str, Any]:
        """The connections ``CheckSourceAction`` runs with."""
        return {GRAPH_STORE_CONNECTION_KEY: self.graphs, GRAPH_SOURCE_CONNECTION_KEY: self.gateway, ROOM_REGISTRY_KEY: self.rooms}

    async def check(self, source: str) -> str:
        """Run one check of ``source``; its status."""
        result = await self.machine.run(Context(), CheckSourceAction(), CheckSourceParams(source=source), self.check_connections())
        return result.status


def _maxitor() -> Maxitor:
    """Maxitor's machine, store and resources, as ``create_app`` builds them."""
    machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
    gateway = GraphSourceGateway()
    store = GraphStore(partial(build_graph_entry, machine, gateway))
    graphs = GraphStoreController(store)
    rooms = RoomRegistry()
    rooms.bind(machine)
    checks = SourceChecks()
    connections = {GRAPH_STORE_CONNECTION_KEY: graphs, GRAPH_SOURCE_CONNECTION_KEY: gateway, ROOM_REGISTRY_KEY: rooms}
    checks.bind(machine, {CheckSourceAction: connections})
    return Maxitor(machine, store, graphs, gateway, rooms, OpenTabsRegistry(), checks)


async def test_an_unchanged_service_with_an_etag_answers_304_and_nothing_is_rebuilt(service: tuple[Service, str]) -> None:
    """(1) The check sends the held ETag; the service's 304 leaves the graph as it is."""
    state, source = service
    state.etag = '"v1"'
    maxitor = _maxitor()
    held = await maxitor.store.acquire(source)
    assert await maxitor.check(source) == "unchanged"
    assert state.conditional == ['"v1"']
    assert maxitor.store.peek(source) is held


async def test_without_validators_an_equal_body_is_not_rebuilt(service: tuple[Service, str]) -> None:
    """(2) A service with no ETag is downloaded and compared by SHA-256; an equal body changes nothing."""
    _, source = service
    maxitor = _maxitor()
    held = await maxitor.store.acquire(source)
    assert await maxitor.check(source) == "unchanged"
    assert maxitor.store.peek(source) is held


async def test_a_changed_body_is_rebuilt_and_the_rooms_are_told(service: tuple[Service, str], monkeypatch: pytest.MonkeyPatch) -> None:
    """(3) A new body builds a new graph with a new fingerprint, and every room of the source hears it."""
    state, source = service
    maxitor = _maxitor()
    held = await maxitor.store.acquire(source)
    room = maxitor.rooms.open_room(source, "anna")
    heard: list[dict[str, Any]] = []
    monkeypatch.setattr(maxitor.rooms, "broadcast", lambda target, event, **_: heard.append({"room": target.id, **event}))
    state.body = _CHANGED_BODY
    assert await maxitor.check(source) == "rebuilt"
    rebuilt = maxitor.store.peek(source)
    assert rebuilt is not None and rebuilt is not held
    assert rebuilt.fingerprint != held.fingerprint
    assert heard == [{"room": room.id, "type": "graph_changed", "fingerprint": rebuilt.fingerprint}]


async def test_a_failing_build_keeps_the_old_graph(service: tuple[Service, str], capsys: pytest.CaptureFixture[str]) -> None:
    """(4) A body that does not build keeps the graph everyone has, and the log warns."""
    state, source = service
    maxitor = _maxitor()
    held = await maxitor.store.acquire(source)
    state.body = b"not json"
    assert await maxitor.check(source) == "failed"
    assert maxitor.store.peek(source) is held
    assert f"Source {source} not rebuilt" in capsys.readouterr().out


async def test_an_unreachable_service_keeps_the_old_graph_readable(service: tuple[Service, str]) -> None:
    """(5) A service that is down keeps the held graph, and reads still get it."""
    state, source = service
    maxitor = _maxitor()
    held = await maxitor.store.acquire(source)
    state.up = False
    assert await maxitor.check(source) == "unreachable"
    assert await maxitor.store.acquire(source) is held


async def test_two_checks_of_one_source_at_once_ask_the_service_once(service: tuple[Service, str]) -> None:
    """(6) Checks of one source never overlap: the second finds the first running."""
    state, source = service
    maxitor = _maxitor()
    await maxitor.store.acquire(source)
    before = state.requests
    statuses = await asyncio.gather(maxitor.check(source), maxitor.check(source))
    assert sorted(statuses) == ["skipped", "unchanged"]
    assert state.requests - before == 1


async def test_an_unwatched_source_waits_for_its_next_read(service: tuple[Service, str]) -> None:
    """(7) Nobody looks — a tab last asked ten minutes ago is gone: the clock skips the source; a
    fingerprint read answers at once and checks in the background."""
    state, source = service
    maxitor = _maxitor()
    entry = await maxitor.store.acquire(source)
    entry.last_checked -= 1000
    maxitor.tabs.seen(source, maxitor.store.now() - 600)
    due_connections = {**maxitor.check_connections(), OPEN_TABS_CONNECTION_KEY: maxitor.tabs}
    picked = await maxitor.machine.run(Context(), CheckDueSourcesAction(), ParamsStub(), due_connections)
    assert picked.checked == []
    before = state.requests
    answer = await maxitor.machine.run(
        Context(),
        GraphFingerprintAction(),
        GraphFingerprintParams(source=source),
        {GRAPH_STORE_CONNECTION_KEY: maxitor.graphs, OPEN_TABS_CONNECTION_KEY: maxitor.tabs, SOURCE_CHECKS_CONNECTION_KEY: maxitor.checks},
    )
    assert answer.fingerprint == entry.fingerprint
    for _ in range(100):
        if state.requests > before and not entry.checking:
            break
        await asyncio.sleep(0.02)
    assert state.requests == before + 1
    # Asked about a moment ago, the source is now watched: the clock picks it once it is due again.
    entry.last_checked -= 1000
    picked = await maxitor.machine.run(Context(), CheckDueSourcesAction(), ParamsStub(), due_connections)
    assert picked.checked == [source]
    await maxitor.checks.close()


async def test_the_log_names_the_source_and_nobody_else(service: tuple[Service, str], capsys: pytest.CaptureFixture[str]) -> None:
    """(8) Check records carry the source; no participant appears in them."""
    state, source = service
    maxitor = _maxitor()
    await maxitor.store.acquire(source)
    room = maxitor.rooms.open_room(source, "anna-id")
    maxitor.rooms.add_participant(room, "anna-id", "Anna Secret")
    capsys.readouterr()
    await maxitor.check(source)
    state.body = _CHANGED_BODY
    await maxitor.check(source)
    out = capsys.readouterr().out
    assert f"Source {source} unchanged" in out and f"Source {source} rebuilt" in out
    assert "anna" not in out.lower() and "Secret" not in out

"""
09_fresh_graphs.py — held graphs follow their services

Maxitor keeps one built graph per AOA service. It now asks the service, while someone looks at the
graph, whether it changed (spec 028): every 30 seconds when the service gives ``ETag`` or
``Last-Modified`` — an unchanged service then answers ``304`` and costs a header — and every 2 minutes
when it does not, comparing the SHA-256 of the body. A changed service is rebuilt in the background,
and the new graph replaces the old one only when its build succeeded. A service that is down keeps the
graph everyone already has. Every answer of the adapter carries an ``ETag`` of its own content too.

This script drives the real application and the real check action against a local service whose
body, ``ETag`` and availability it controls:

  1. an adapter answer carries an ETag; the same tag back gets 304 with no body;
  2. the fingerprint of the held graph, answered from memory;
  3. an unchanged service answers 304 to the held ETag — nothing is rebuilt;
  4. the service changes — the graph is rebuilt and its fingerprint changes;
  5. the service goes down — the graph everyone has is kept and still read;
  6. Maxitor is an AOA service too: it serves its own model as ``graph-json`` at the path the demo
     uses, tagged like any answer, so its own address opens its own diagram (spec 029).

Output:

The port and the fingerprints vary; the indented lines without an arrow are Maxitor's own log:

    1. An adapter answer and its ETag
       GET list-domains          -> 200, ETag "6c41b90355e7a28bf08152bfdf7ee792", 2809 bytes
       again with If-None-Match  -> 304, 0 bytes

    2. The held graph's fingerprint, from memory
       GET graph-fingerprint     -> c928cf56a055

    3. An unchanged service
      Source http://127.0.0.1:54115/graph-json unchanged
       check -> unchanged, fingerprint c928cf56a055; bodies sent by the service: 0
       the same graph is held: True

    4. The service changes
      Source http://127.0.0.1:54115/graph-json rebuilt
       check -> rebuilt, fingerprint 03a4014fdfec

    5. The service goes down
      Source http://127.0.0.1:54115/graph-json unreachable: HTTP 503
       check -> unreachable, fingerprint 03a4014fdfec
       the graph is kept and still read: True

    6. Maxitor's own graph
       GET /examples/model/graph-json -> 200, 3422 nodes, ETag "7a8d787970a9d303d83a269990409344"
       room actions in it: EndRoomAction, JoinRoomAction, LeaveRoomAction, ReloadSourceForRoomAction, …
       again with If-None-Match       -> 304, 0 bytes

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (fresh graphs)

Run:
    uv run python examples/step_26_maxitor/09_fresh_graphs.py
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from fastapi.testclient import TestClient

from aoa.action_machine.context import Context
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.demo.model.services.graph_json_service import ExampleModelGraphJsonService
from maxitor.front.api.app import create_app
from maxitor.front.api.graph_store import GraphStore, build_graph_entry
from maxitor.front.model.core.actions.check_source_action import CheckSourceAction, CheckSourceParams
from maxitor.front.model.core.resources.graph_source_gateway import GRAPH_SOURCE_CONNECTION_KEY, GraphSourceGateway
from maxitor.front.model.core.resources.graph_store_controller import GRAPH_STORE_CONNECTION_KEY, GraphStoreController
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY, RoomRegistry

MODEL = json.dumps({"coordinator_json": ExampleModelGraphJsonService().coordinator_json()}).encode()


@dataclass
class Service:
    """What the local service answers, and how many bodies it sent."""

    body: bytes = MODEL
    etag: str = '"v1"'
    up: bool = True
    bodies_sent: int = 0


def serve(service: Service) -> str:
    """Serve ``service`` as ``graph-json`` on a free local port; return its address."""

    class Handler(BaseHTTPRequestHandler):
        """Answers as ``service`` says: 503 when down, 304 to its current ETag, else the body."""

        def do_GET(self) -> None:
            """Answer one request."""
            if not service.up:
                self.send_response(503)
                self.end_headers()
            elif self.headers.get("If-None-Match") == service.etag:
                self.send_response(304)
                self.end_headers()
            else:
                service.bodies_sent += 1
                self.send_response(200)
                self.send_header("ETag", service.etag)
                self.send_header("Content-Length", str(len(service.body)))
                self.end_headers()
                self.wfile.write(service.body)

        def log_message(self, *args: Any) -> None:
            """Keep the output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/graph-json"


service = Service()
SOURCE = serve(service)

# The same pieces ``create_app`` wires: the machine, the store, the gateway, the room registry.
machine = ActionProductMachine(graph_coordinator=create_node_graph_coordinator())
gateway = GraphSourceGateway()
store = GraphStore(partial(build_graph_entry, machine, gateway))
connections = {GRAPH_STORE_CONNECTION_KEY: GraphStoreController(store), GRAPH_SOURCE_CONNECTION_KEY: gateway, ROOM_REGISTRY_KEY: RoomRegistry()}


def check() -> str:
    """Run one freshness check of the source, as the clock does every ten seconds."""
    result = asyncio.run(machine.run(Context(), CheckSourceAction(), CheckSourceParams(source=SOURCE), connections))
    return f"{result.status}, fingerprint {result.fingerprint[:12]}"


def case_1_etag_and_304() -> None:
    """Every successful GET of the adapter is tagged; a client that holds the content gets 304."""
    print("1. An adapter answer and its ETag")
    with TestClient(create_app()) as client:
        first = client.get("/api/v1/list-domains", params={"source": SOURCE})
        print(f"   GET list-domains          -> {first.status_code}, ETag {first.headers['etag']}, {len(first.content)} bytes")
        again = client.get("/api/v1/list-domains", params={"source": SOURCE}, headers={"If-None-Match": first.headers["etag"]})
        print(f"   again with If-None-Match  -> {again.status_code}, {len(again.content)} bytes")
        fingerprint = client.get("/api/v1/graph-fingerprint", params={"source": SOURCE}).json()["fingerprint"]
        print(f"\n2. The held graph's fingerprint, from memory\n   GET graph-fingerprint     -> {fingerprint[:12]}")


def case_3_unchanged() -> None:
    """The check sends the held ETag; the service confirms it with 304, and no body travels."""
    print("\n3. An unchanged service")
    entry = asyncio.run(store.acquire(SOURCE))
    sent = service.bodies_sent
    print(f"   check -> {check()}; bodies sent by the service: {service.bodies_sent - sent}")
    print(f"   the same graph is held: {store.peek(SOURCE) is entry}")


def case_4_changed() -> None:
    """A new body is rebuilt; the new graph replaces the old one only once its build succeeded."""
    print("\n4. The service changes")
    service.body = json.dumps(json.loads(MODEL), indent=1).encode()
    service.etag = '"v2"'
    print(f"   check -> {check()}")


def case_5_down() -> None:
    """A service that does not answer keeps the graph everyone already has."""
    print("\n5. The service goes down")
    service.up = False
    held = store.peek(SOURCE)
    print(f"   check -> {check()}")
    print(f"   the graph is kept and still read: {asyncio.run(store.acquire(SOURCE)) is held}")


def case_6_own_graph() -> None:
    """Maxitor's own model, answered by an AOA action at ``/examples/model/graph-json``."""
    print("\n6. Maxitor's own graph")
    with TestClient(create_app()) as client:
        first = client.get("/examples/model/graph-json")
        nodes = json.loads(first.json()["coordinator_json"])["nodes"]
        actions = sorted(n["label"] for n in nodes if n["type"] == "Action" and "Room" in n["label"])
        print(f"   GET /examples/model/graph-json -> {first.status_code}, {len(nodes)} nodes, ETag {first.headers['etag']}")
        print(f"   room actions in it: {', '.join(actions[:4])}, …")
        again = client.get("/examples/model/graph-json", headers={"If-None-Match": first.headers["etag"]})
        print(f"   again with If-None-Match       -> {again.status_code}, {len(again.content)} bytes")


def main() -> None:
    """Run every case in order."""
    case_1_etag_and_304()
    case_3_unchanged()
    case_4_changed()
    case_5_down()
    case_6_own_graph()


if __name__ == "__main__":
    main()

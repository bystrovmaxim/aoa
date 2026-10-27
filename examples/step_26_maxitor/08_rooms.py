"""
08_rooms.py — look at one service together: a room, its settings, its pointers

A room lets several people look at one AOA service at once (spec 028). Everyone in it sees the
others' pointers on the same spot of the diagram, and every filter and layout mode is the room's.
The room lives in Maxitor's process; every operation on it is an AOA action, run once per message of
one WebSocket route, ``/api/v1/rooms/{room_id}/live``. Pointers are the exception: they are relayed
as they come, never run as actions and never logged.

This script drives the real Maxitor application through FastAPI's test client, with no browser.
The service is the AOA demo model, served as ``graph-json`` from a local port:

  1. Anna opens a room; Boris joins by its id — each is welcomed with the whole room;
  2. Boris switches the ERD to Neato — the setting reaches Anna, and later joiners get it too;
  3. Anna's pointer reaches Boris in diagram coordinates, and nothing is run for it;
  4. Anna follows Boris, so Boris cannot follow Anna: the room refuses the circle;
  5. a room holds 20 people — the 21st is refused with close code 4409;
  6. an ended room's link is refused with 4404, and the page opens on its own.

Output:

Room ids and the port are random; the indented lines without an arrow are Maxitor's own log,
which names rooms and participants by id only:

    1. Anna opens a room; Boris joins
      Room WyIjCKaNKUE6mfLymJRvpw created for http://127.0.0.1:58537/graph-json
      Participant anna joined room WyIjCKaNKUE6mfLymJRvpw
       Anna   <- welcome: room of 1, created by anna
      Participant boris joined room WyIjCKaNKUE6mfLymJRvpw
       Boris  <- welcome: room of 2: anna, boris
       Anna   <- joined: Boris

    2. Boris sets the ERD's layout to Neato
      Setting layout changed in room WyIjCKaNKUE6mfLymJRvpw
       Anna   <- setting: view=domain-erd layout = gv-neato (by boris)
      Participant vera joined room WyIjCKaNKUE6mfLymJRvpw
       Vera   <- welcome with settings {'view=domain-erd': {'layout': 'gv-neato'}}

    3. Anna's pointer reaches Boris
       Boris  <- pointer: anna at (120.5, -40.0), mouse

    4. A follow that would close a circle is refused
      Participant anna follows boris in room WyIjCKaNKUE6mfLymJRvpw
       Anna   -> follow boris: the room's links {'anna': 'boris', 'boris': None}
      Follow refused in room WyIjCKaNKUE6mfLymJRvpw: boris to anna
       Boris  <- follow_refused: they already follow you, directly or through others

    5. A room holds 20 people
      Room join refused: WyIjCKaNKUE6mfLymJRvpw is full
       the 21st -> closed 4409: room full

    6. An ended room's link
      Room join refused: wTQRpfc1VRYub-ESEujaFg has ended
       a room nobody is in any more -> closed 4404: room ended

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (rooms)

Run:
    uv run python examples/step_26_maxitor/08_rooms.py
"""

from __future__ import annotations

import io
import json
import threading
from contextlib import ExitStack, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aoa.demo.model.services.graph_json_service import ExampleModelGraphJsonService
from aoa.maxitor.api.app import create_app

ERD = "view=domain-erd"


def serve_demo_model() -> str:
    """Serve the AOA demo model's ``graph-json`` on a free local port; return its address."""
    body = json.dumps({"coordinator_json": ExampleModelGraphJsonService().coordinator_json()}).encode()

    class Handler(BaseHTTPRequestHandler):
        """Answers every GET with the demo model."""

        def do_GET(self) -> None:
            """Send the graph-json document."""
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            """Keep the output quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/graph-json"


def connect(client: TestClient, room: str, participant: str, *, source: str = "", page: str = ERD) -> Any:
    """Open a room connection as the client does: who joins, from which tab, with which name and page."""
    query = {"participant": participant, "tab": f"{participant}-tab", "participant_name": participant.title(), "start_page": page}
    if source:
        query["source"] = source
    return client.websocket_connect(f"/api/v1/rooms/{room}/live?{urlencode(query)}")


def next_event(ws: Any, kind: str) -> dict[str, Any]:
    """The next event of ``kind`` on ``ws``, skipping the room's other news."""
    while True:
        event: dict[str, Any] = ws.receive_json()
        if event["type"] == kind:
            return event


def closed(ws: Any) -> str:
    """How the server closed a refused connection."""
    try:
        ws.receive_json()
    except WebSocketDisconnect as refusal:
        return f"closed {refusal.code}: {refusal.reason}"
    return "not closed"


SOURCE = serve_demo_model()
client = TestClient(create_app()).__enter__()
stack = ExitStack()


def case_1_open_and_join() -> tuple[str, Any, Any]:
    """Anna opens a room for the service; Boris joins it by its id."""
    print("1. Anna opens a room; Boris joins")
    anna = stack.enter_context(connect(client, "new", "anna", source=SOURCE))
    welcome = next_event(anna, "welcome")
    room_id: str = welcome["room"]["id"]
    print(f"   Anna   <- welcome: room of {len(welcome['room']['participants'])}, created by {welcome['room']['created_by']}")
    boris = stack.enter_context(connect(client, room_id, "boris"))
    welcome = next_event(boris, "welcome")
    print(f"   Boris  <- welcome: room of {len(welcome['room']['participants'])}: {', '.join(p['id'] for p in welcome['room']['participants'])}")
    print(f"   Anna   <- joined: {next_event(anna, 'joined')['participant']['name']}")
    return room_id, anna, boris


def case_2_shared_setting(room_id: str, anna: Any, boris: Any) -> None:
    """A setting is sent as the new value and reaches everyone, now and later."""
    print("\n2. Boris sets the ERD's layout to Neato")
    boris.send_json({"type": "setting", "page": ERD, "name": "layout", "value": "gv-neato"})
    heard = next_event(anna, "setting")
    print(f"   Anna   <- setting: {heard['page']} {heard['name']} = {heard['value']} (by {heard['by']})")
    vera = stack.enter_context(connect(client, room_id, "vera", page="view=full-graph"))
    print(f"   Vera   <- welcome with settings {next_event(vera, 'welcome')['room']['settings']}")


def case_3_pointer(anna: Any, boris: Any) -> None:
    """A pointer travels in diagram coordinates, to the tabs on the same page only."""
    print("\n3. Anna's pointer reaches Boris")
    anna.send_json({"type": "pointer", "kind": "mouse", "x": 120.5, "y": -40.0})
    seen = next_event(boris, "pointer")
    print(f"   Boris  <- pointer: {seen['participant']} at ({seen['x']}, {seen['y']}), {seen['kind']}")


def case_4_refused_circle(anna: Any, boris: Any) -> None:
    """Following never closes a circle: the room checks it under its lock."""
    print("\n4. A follow that would close a circle is refused")
    anna.send_json({"type": "follow", "target": "boris"})
    links = next_event(anna, "follows")["follows"]
    print(f"   Anna   -> follow boris: the room's links { {k: links[k] for k in ('anna', 'boris')} }")
    boris.send_json({"type": "follow", "target": "anna"})
    print(f"   Boris  <- follow_refused: {next_event(boris, 'follow_refused')['reason']}")


def case_5_full_room(room_id: str) -> None:
    """Twenty people fit; the next one is refused with a close code the page turns into a sentence."""
    print("\n5. A room holds 20 people")
    # Seventeen guests fill the room; their join records are not printed.
    with redirect_stdout(io.StringIO()):
        for index in range(17):
            next_event(stack.enter_context(connect(client, room_id, f"guest{index}")), "welcome")
    with connect(client, room_id, "late") as late:
        print(f"   the 21st -> {closed(late)}")


def case_6_ended_room() -> None:
    """A room ends two minutes after its last person leaves; its id is never used again."""
    print("\n6. An ended room's link")
    rooms = client.app.state.rooms
    room = rooms.open_room(SOURCE, "nobody")
    rooms.end_room(room)
    with connect(client, room.id, "boris") as late:
        print(f"   a room nobody is in any more -> {closed(late)}")


def main() -> None:
    """Run every case in order."""
    room_id, anna, boris = case_1_open_and_join()
    case_2_shared_setting(room_id, anna, boris)
    case_3_pointer(anna, boris)
    case_4_refused_circle(anna, boris)
    case_5_full_room(room_id)
    case_6_ended_room()
    with redirect_stdout(io.StringIO()):
        stack.close()
        client.__exit__(None, None, None)


if __name__ == "__main__":
    main()

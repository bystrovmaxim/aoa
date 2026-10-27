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
  2. Boris switches the ERD to Neato — the setting reaches Anna, and later joiners get it too; Anna's
     own filters, sent as the room's seed, fill only what the room does not hold yet (spec 029);
  3. Anna's pointer reaches Boris in diagram coordinates, and nothing is run for it; an hour later it
     still reaches Vera when she comes to that page — a pointer stays while its person is in the room;
  4. Anna follows Boris: what he hovers reaches her and nobody else; and Boris cannot follow Anna,
     because the room refuses the circle;
  5. a room holds 20 people — the 21st is refused with close code 4409;
  6. an ended room's link is refused with 4404, and the page opens on its own.

Output:

Room ids and the port are random; the indented lines without an arrow are Maxitor's own log,
which names rooms and participants by id only:

    1. Anna opens a room; Boris joins
      Room dPPUfS2wLJRwtj8Cog8MLQ created for http://127.0.0.1:53937/graph-json
      Participant anna joined room dPPUfS2wLJRwtj8Cog8MLQ
       Anna   <- welcome: room of 1, created by anna
      Participant boris joined room dPPUfS2wLJRwtj8Cog8MLQ
       Boris  <- welcome: room of 2: anna, boris
       Anna   <- joined: Boris

    2. Boris sets the ERD's layout to Neato
      Setting layout changed in room dPPUfS2wLJRwtj8Cog8MLQ
       Anna   <- setting: view=domain-erd layout = gv-neato (by boris)
      Room dPPUfS2wLJRwtj8Cog8MLQ seeded with 1 settings of a page
       Boris  <- setting from Anna's seed: one_hop = False (the layout stays gv-neato)
      Participant vera joined room dPPUfS2wLJRwtj8Cog8MLQ
       Vera   <- welcome with settings {'view=domain-erd': {'layout': 'gv-neato', 'one_hop': False}}

    3. Anna's pointer reaches Boris
       Boris  <- pointer: anna at (120.5, -40.0), mouse
       Vera   <- an hour later, on the ERD: anna's pointer at (120.5, -40.0)

    4. Anna follows Boris; a follow that would close a circle is refused
      Participant anna follows boris in room dPPUfS2wLJRwtj8Cog8MLQ
       Anna   -> follow boris: the room's links {'anna': 'boris', 'boris': None}
       Anna   <- focus: boris hovers Orders, filter panel open at kinds
      Participant vera renamed in room dPPUfS2wLJRwtj8Cog8MLQ
       Vera   <- focus events before her rename comes back: 0
      Follow refused in room dPPUfS2wLJRwtj8Cog8MLQ: boris to anna
       Boris  <- follow_refused: they already follow you, directly or through others

    5. A room holds 20 people
      Room join refused: dPPUfS2wLJRwtj8Cog8MLQ is full
       the 21st -> closed 4409: room full

    6. An ended room's link
      Room join refused: AKxdLAwnObUU_chh2nIUxQ has ended
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


def events_until(ws: Any, kind: str) -> list[dict[str, Any]]:
    """Every event on ``ws`` up to and including the next one of ``kind``."""
    events = [ws.receive_json()]
    while events[-1]["type"] != kind:
        events.append(ws.receive_json())
    return events


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


def case_2_shared_setting(room_id: str, anna: Any, boris: Any) -> Any:
    """A setting is sent as the new value and reaches everyone, now and later; a seed only fills gaps."""
    print("\n2. Boris sets the ERD's layout to Neato")
    boris.send_json({"type": "setting", "page": ERD, "name": "layout", "value": "gv-neato"})
    heard = next_event(anna, "setting")
    print(f"   Anna   <- setting: {heard['page']} {heard['name']} = {heard['value']} (by {heard['by']})")
    # The opener's own filters seed the room; the layout Boris chose stays, 1-hop off is new.
    anna.send_json({"type": "seed", "page": ERD, "settings": {"layout": "gv-dot-lr", "one_hop": False}})
    heard = next_event(boris, "setting")
    while heard["by"] != "anna":  # his own layout comes back to him first
        heard = next_event(boris, "setting")
    print(f"   Boris  <- setting from Anna's seed: {heard['name']} = {heard['value']} (the layout stays gv-neato)")
    vera = stack.enter_context(connect(client, room_id, "vera", page="view=full-graph"))
    print(f"   Vera   <- welcome with settings {next_event(vera, 'welcome')['room']['settings']}")
    return vera


def case_3_pointer(room_id: str, anna: Any, boris: Any, vera: Any) -> None:
    """A pointer travels in diagram coordinates, to the tabs on the same page only, and stays."""
    print("\n3. Anna's pointer reaches Boris")
    anna.send_json({"type": "pointer", "kind": "mouse", "x": 120.5, "y": -40.0})
    seen = next_event(boris, "pointer")
    print(f"   Boris  <- pointer: {seen['participant']} at ({seen['x']}, {seen['y']}), {seen['kind']}")
    # An hour passes with Anna's mouse still; Vera then comes to the ERD.
    client.app.state.rooms.room(room_id).participants["anna"].active_tab.last_activity -= 3600
    vera.send_json({"type": "page", "page": ERD})
    seen = next_event(vera, "pointer")
    print(f"   Vera   <- an hour later, on the ERD: {seen['participant']}'s pointer at ({seen['x']}, {seen['y']})")


def case_4_follow(anna: Any, boris: Any, vera: Any) -> None:
    """A follower sees what the followed person looks at; following never closes a circle."""
    print("\n4. Anna follows Boris; a follow that would close a circle is refused")
    anna.send_json({"type": "follow", "target": "boris"})
    links = next_event(anna, "follows")["follows"]
    print(f"   Anna   -> follow boris: the room's links { {k: links[k] for k in ('anna', 'boris')} }")
    # Boris hovers a table: the hover, its tooltip and his open panels go to his followers only.
    boris.send_json({"type": "focus", "page": ERD, "hover": {"kind": "table", "id": "Orders"}, "tooltip": None,
                     "selection": None, "panels": {"sidebar": [], "filter": "kinds", "legend": False}})
    seen = next_event(anna, "focus")
    print(f"   Anna   <- focus: {seen['participant']} hovers {seen['hover']['id']}, filter panel open at {seen['panels']['filter']}")
    vera.send_json({"type": "rename", "name": "Vera"})
    print(f"   Vera   <- focus events before her rename comes back: {sum(e['type'] == 'focus' for e in events_until(vera, 'renamed'))}")
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
    vera = case_2_shared_setting(room_id, anna, boris)
    case_3_pointer(room_id, anna, boris, vera)
    case_4_follow(anna, boris, vera)
    case_5_full_room(room_id)
    case_6_ended_room()
    with redirect_stdout(io.StringIO()):
        stack.close()
        client.__exit__(None, None, None)


if __name__ == "__main__":
    main()

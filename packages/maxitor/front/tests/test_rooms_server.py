# packages/maxitor/front/tests/test_rooms_server.py
"""
Rooms on the server — the whole room protocol against the real application.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Opens real WebSocket connections to ``/api/v1/rooms/{room_id}/live`` of the real
Maxitor application, whose graph comes from the frozen reference service served on a
local port. Each test drives one rule of spec 028: opening and joining, colours, tabs,
limits, names, the return window, the end of an empty room, the origin, shared
settings, the follow circle under concurrency, the pointer relay, the fallback page,
and a log that never names anyone.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    local HTTP server ── graph-json (fixture) ──► GraphStore of create_app()
                                                        │
    TestClient.websocket_connect(/api/v1/rooms/…/live) ─┴─► room actions ──► events
"""

from __future__ import annotations

import gzip
import threading
import time
from collections.abc import Iterator
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.model.rooms.resources.room_registry import RoomRegistry
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

_FIXTURE = Path(__file__).parent / "fixtures" / "ref-graph-2026-10-26.json.gz"
_FULL_GRAPH = "view=full-graph"
_ALL_DOMAINS = "view=domain-erd"


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
def client() -> Iterator[TestClient]:
    """A fresh application, with its own registry and store."""
    with TestClient(create_app()) as test_client:
        yield test_client


def _rooms(client: TestClient) -> RoomRegistry:
    """The application's room registry."""
    rooms: RoomRegistry = client.app.state.rooms  # type: ignore[attr-defined]
    return rooms


def _connect(
    client: TestClient,
    room: str,
    participant: str,
    *,
    name: str | None = None,
    tab: str | None = None,
    page: str = _FULL_GRAPH,
    source: str = "",
    origin: str | None = None,
) -> Any:
    """Open a room connection (a context manager) with the query the client sends."""
    query = {
        "participant": participant,
        "tab": tab or f"{participant}-tab",
        "participant_name": name if name is not None else participant.title(),
        "start_page": page,
    }
    if source:
        query["source"] = source
    headers = {"origin": origin} if origin is not None else {}
    return client.websocket_connect(f"/api/v1/rooms/{room}/live?{urlencode(query)}", headers=headers)


def _expect(ws: WebSocketTestSession, kind: str) -> dict[str, Any]:
    """The next event, which must be of ``kind``."""
    event: dict[str, Any] = ws.receive_json()
    assert event["type"] == kind, event
    return event


def _open(stack: ExitStack, client: TestClient, source: str, participant: str = "anna") -> tuple[WebSocketTestSession, str]:
    """Open a new room as ``participant``; return the connection and the room id."""
    ws = stack.enter_context(_connect(client, "new", participant, source=source))
    welcome = _expect(ws, "welcome")
    return ws, welcome["room"]["id"]


def _until(ws: WebSocketTestSession, kind: str) -> set[str]:
    """The types of every event up to and including the first of ``kind``."""
    seen: set[str] = set()
    while kind not in seen:
        seen.add(ws.receive_json()["type"])
    return seen


def _closed(ws: WebSocketTestSession) -> tuple[int, str]:
    """The close code and reason the server ends this connection with, before it sends anything."""
    with pytest.raises(WebSocketDisconnect) as closed:
        ws.receive_json()
    return closed.value.code, closed.value.reason


def _wait_for(predicate: Any, timeout: float = 3.0) -> bool:
    """Poll ``predicate``; the application runs on its own thread."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return bool(predicate())


def test_open_and_join_a_room(client: TestClient, source: str) -> None:
    """(1) Anna opens a room; Boris joins by its id and is welcomed with the whole room."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        welcome = _expect(boris, "welcome")
        joined = _expect(anna, "joined")

    assert welcome["you"]["id"] == "boris"
    assert {p["id"] for p in welcome["room"]["participants"]} == {"anna", "boris"}
    assert welcome["room"]["settings"] == {} and welcome["room"]["created_by"] == "anna"
    assert "server_build" in welcome and welcome["fallback_page"] is None
    assert joined["participant"]["id"] == "boris" and joined["participant"]["name"] == "Boris"


def test_colours_are_unique_and_freed_on_leave(client: TestClient, source: str) -> None:
    """(2) Two participants get different colours; a colour left behind goes to the next newcomer."""
    with ExitStack() as stack:
        anna = stack.enter_context(_connect(client, "new", "anna", source=source))
        anna_welcome = _expect(anna, "welcome")
        room_id = anna_welcome["room"]["id"]
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        boris_colour = _expect(boris, "welcome")["you"]["colour"]
        _expect(anna, "joined")
        assert boris_colour != anna_welcome["you"]["colour"]
        boris.send_json({"type": "leave"})
        _expect(anna, "left")
        _expect(anna, "follows")
        vera = stack.enter_context(_connect(client, room_id, "vera"))
        assert _expect(vera, "welcome")["you"]["colour"] == boris_colour


def test_two_tabs_are_one_participant(client: TestClient, source: str) -> None:
    """(3) A second tab of Boris joins as the same participant; his page is the latest active tab's."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris_one = stack.enter_context(_connect(client, room_id, "boris", tab="one"))
        _expect(boris_one, "welcome")
        _expect(anna, "joined")
        boris_two = stack.enter_context(_connect(client, room_id, "boris", tab="two", page=_ALL_DOMAINS))
        welcome = _expect(boris_two, "welcome")
        presence = _expect(anna, "presence")

    assert sorted(p["id"] for p in welcome["room"]["participants"]) == ["anna", "boris"]
    assert presence["id"] == "boris" and presence["page"] == _ALL_DOMAINS


def test_the_twenty_first_person_is_refused(client: TestClient, source: str) -> None:
    """(4) A room holds 20 people; the 21st connection is closed with 4409."""
    with ExitStack() as stack:
        _, room_id = _open(stack, client, source)
        for index in range(1, 20):
            ws = stack.enter_context(_connect(client, room_id, f"p{index}"))
            _expect(ws, "welcome")
        late = stack.enter_context(_connect(client, room_id, "late"))
        assert _closed(late) == (4409, "room full")


def test_the_hundred_and_first_room_is_refused(client: TestClient, source: str) -> None:
    """(4) A process holds 100 rooms; opening the 101st is refused with 4503."""
    for index in range(100):
        with _connect(client, "new", f"owner{index}", source=source) as ws:
            _expect(ws, "welcome")
    with _connect(client, "new", "one-too-many", source=source) as ws:
        assert _closed(ws) == (4503, "too many rooms")


@pytest.mark.parametrize("name", ["   ", "x" * 41])
def test_an_invalid_name_is_refused(client: TestClient, source: str, name: str) -> None:
    """(5) A name of spaces only, or over 40 characters, closes the connection with 4422."""
    with _connect(client, "new", "anna", name=name, source=source) as ws:
        assert _closed(ws) == (4422, "invalid name")


def test_a_quick_return_is_not_a_leave(client: TestClient, source: str) -> None:
    """(6) Boris drops and comes back within the window: nobody is told he left or joined."""
    _rooms(client).return_window_seconds = 1.0
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        with _connect(client, room_id, "boris") as boris:
            _expect(boris, "welcome")
            _expect(anna, "joined")
        away = _expect(anna, "presence")
        assert away["id"] == "boris" and away["away"] is True
        back = stack.enter_context(_connect(client, room_id, "boris"))
        welcome = _expect(back, "welcome")
        returned = _expect(anna, "presence")

    assert welcome["you"]["colour"] == away["colour"]
    assert returned["away"] is False


def test_a_lost_participant_leaves_after_the_window(client: TestClient, source: str) -> None:
    """(6) Boris drops and does not come back: when the window ends, the room is told he left."""
    _rooms(client).return_window_seconds = 0.3
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        with _connect(client, room_id, "boris") as boris:
            _expect(boris, "welcome")
            _expect(anna, "joined")
        _expect(anna, "presence")
        left = _expect(anna, "left")
    assert left["participant"]["id"] == "boris"


def test_an_empty_room_ends_and_its_link_says_so(client: TestClient, source: str) -> None:
    """(7) The last person leaves; after the delay the room ends and its id is refused with 4404."""
    rooms = _rooms(client)
    rooms.empty_room_seconds = 0.3
    with _connect(client, "new", "anna", source=source) as anna:
        room_id = _expect(anna, "welcome")["room"]["id"]
        anna.send_json({"type": "leave"})
    assert _wait_for(lambda: rooms.room(room_id) is None)
    with _connect(client, room_id, "boris") as late:
        assert _closed(late) == (4404, "room ended")


def test_a_foreign_origin_is_refused(client: TestClient, source: str) -> None:
    """(8) A browser page from another site cannot join: 4403."""
    with _connect(client, "new", "anna", source=source, origin="https://evil.example") as ws:
        assert _closed(ws) == (4403, "origin not allowed")


def test_settings_are_shared_and_the_last_one_wins(client: TestClient, source: str) -> None:
    """(9) A setting reaches everyone and a later joiner; two changes in a row end in the last."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        anna.send_json({"type": "setting", "page": _ALL_DOMAINS, "name": "layout", "value": "gv-neato"})
        boris.send_json({"type": "setting", "page": _ALL_DOMAINS, "name": "layout", "value": "gv-circo"})
        seen = [_expect(boris, "setting")["value"], _expect(boris, "setting")["value"]]
        _expect(anna, "setting")
        last = _expect(anna, "setting")["value"]
        vera = stack.enter_context(_connect(client, room_id, "vera"))
        settings = _expect(vera, "welcome")["room"]["settings"]

    assert seen[-1] == last
    assert settings == {_ALL_DOMAINS: {"layout": last}}


def test_a_setting_the_page_does_not_have_is_refused(client: TestClient, source: str) -> None:
    """(9) An unknown setting is refused with its reason; the connection stays open."""
    with ExitStack() as stack:
        anna, _ = _open(stack, client, source)
        anna.send_json({"type": "setting", "page": _ALL_DOMAINS, "name": "colour", "value": "red"})
        refused = _expect(anna, "refused")
        assert refused["code"] == 4422 and "colour" in refused["reason"]


def test_crossing_follows_never_both_succeed(client: TestClient, source: str) -> None:
    """(10) Anna and Boris press Follow on each other at once: exactly one link, one refusal."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        anna.send_json({"type": "follow", "target": "boris"})
        boris.send_json({"type": "follow", "target": "anna"})
        room = _rooms(client).room(room_id)
        assert _wait_for(lambda: any(room.follows().values()))
        winner = next(who for who, target in room.follows().items() if target)
        sockets = {"anna": anna, "boris": boris}
        loser = sockets["boris" if winner == "anna" else "anna"]
        winner_events = [sockets[winner].receive_json()["type"]]
        loser_events = [loser.receive_json()["type"], loser.receive_json()["type"]]
        follows = room.follows()

    assert winner_events == ["follows"]
    assert loser_events == ["follows", "follow_refused"]
    assert sum(1 for target in follows.values() if target) == 1


def test_pointers_reach_only_the_same_page(client: TestClient, source: str) -> None:
    """(11) Anna's pointer reaches Boris on her page, not Vera on another page."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        vera = stack.enter_context(_connect(client, room_id, "vera", page=_ALL_DOMAINS))
        _expect(vera, "welcome")
        _expect(anna, "joined")
        _expect(boris, "joined")
        anna.send_json({"type": "pointer", "kind": "mouse", "x": 12.5, "y": -3})
        pointer = _expect(boris, "pointer")
        vera.send_json({"type": "stop_following"})
        next_for_vera = vera.receive_json()

    assert pointer == {"type": "pointer", "participant": "anna", "x": 12.5, "y": -3, "kind": "mouse"}
    assert next_for_vera["type"] == "follows"


def test_a_click_reaches_the_same_page_and_is_not_kept(client: TestClient, source: str) -> None:
    """Anna's click reaches Boris on her page as it happened; it is not her pointer, which stays where it was."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        anna.send_json({"type": "click", "x": 4, "y": 5.5})
        click = _expect(boris, "click")

    assert click == {"type": "click", "participant": "anna", "x": 4, "y": 5.5}


def test_a_page_the_service_lacks_falls_back(client: TestClient, source: str) -> None:
    """(12) Boris's link names a page the service does not offer: he opens Anna's page instead."""
    with ExitStack() as stack:
        _, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris", page="view=domain-erd&domain=nowhere"))
        welcome = _expect(boris, "welcome")
    assert welcome["fallback_page"] == _FULL_GRAPH


def test_the_log_names_ids_never_names(client: TestClient, source: str, capsys: pytest.CaptureFixture[str]) -> None:
    """(13) Joining, renaming and leaving are logged with ids; the names typed never appear."""
    with ExitStack() as stack:
        anna = stack.enter_context(_connect(client, "new", "anna-id", name="Anna Secret", source=source))
        room_id = _expect(anna, "welcome")["room"]["id"]
        anna.send_json({"type": "rename", "name": "Another Secret"})
        _expect(anna, "renamed")
        anna.send_json({"type": "leave"})
    log = capsys.readouterr().out
    assert room_id in log and "anna-id" in log
    assert "Secret" not in log


def test_arriving_on_a_page_brings_the_last_screen_and_a_live_pointer(client: TestClient, source: str) -> None:
    """(14) Boris comes to Anna's page and at once knows her screen and her pointer, without her moving."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        anna.send_json({"type": "viewport", "cx": 10, "cy": 20, "w": 300, "h": 200})
        anna.send_json({"type": "pointer", "kind": "mouse", "x": 1.5, "y": 2.5})
        boris = stack.enter_context(_connect(client, room_id, "boris", page=_ALL_DOMAINS))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        boris.send_json({"type": "page", "page": _FULL_GRAPH})
        caught = {}
        while len(caught) < 2:
            event = boris.receive_json()
            if event["type"] in ("viewport", "pointer"):
                caught[event["type"]] = event

    assert caught["viewport"] == {"type": "viewport", "participant": "anna", "cx": 10, "cy": 20, "w": 300, "h": 200}
    assert caught["pointer"] == {"type": "pointer", "participant": "anna", "x": 1.5, "y": 2.5, "kind": "mouse"}


def test_a_pointer_still_for_an_hour_is_still_brought(client: TestClient, source: str) -> None:
    """(029 FR-021) A pointer shows while its person is in the room, however long it has stood still."""
    rooms = _rooms(client)
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        anna.send_json({"type": "pointer", "kind": "mouse", "x": 1.5, "y": 2.5})
        anna.send_json({"type": "viewport", "cx": 10, "cy": 20, "w": 300, "h": 200})
        assert _wait_for(lambda: rooms.room(room_id).participants["anna"].active_tab.viewport is not None)
        rooms.room(room_id).participants["anna"].active_tab.last_activity -= 3600
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        boris.send_json({"type": "stop_following"})
        caught = _until(boris, "follows")
    assert {"viewport", "pointer"} <= caught


def test_a_tap_is_never_brought(client: TestClient, source: str) -> None:
    """(029 FR-022) A tap is a moment: a newcomer gets the screen only."""
    rooms = _rooms(client)
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        anna.send_json({"type": "pointer", "kind": "touch", "x": 1.5, "y": 2.5})
        anna.send_json({"type": "viewport", "cx": 10, "cy": 20, "w": 300, "h": 200})
        assert _wait_for(lambda: rooms.room(room_id).participants["anna"].active_tab.viewport is not None)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        first = boris.receive_json()
        boris.send_json({"type": "stop_following"})
        rest = [boris.receive_json()["type"]]
    assert first["type"] == "viewport"
    assert rest == ["follows"]


def test_the_openers_seed_becomes_the_rooms_picture(client: TestClient, source: str) -> None:
    """(029 FR-001) The opener's own values reach a guest who is there and one who joins later."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"layout": "gv-neato"}})
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"disabled_kinds": ["dictionary"]}})
        heard = [_expect(boris, "setting"), _expect(boris, "setting")]
        vera = stack.enter_context(_connect(client, room_id, "vera"))
        settings = _expect(vera, "welcome")["room"]["settings"]

    assert [(e["name"], e["value"], e["by"]) for e in heard] == [("layout", "gv-neato", "anna"), ("disabled_kinds", ["dictionary"], "anna")]
    assert settings == {_ALL_DOMAINS: {"layout": "gv-neato", "disabled_kinds": ["dictionary"]}}


def test_a_seed_never_overwrites_what_the_room_holds(client: TestClient, source: str) -> None:
    """(029 FR-001) A value set in the room before the seed arrives wins; an unaccepted value is skipped."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        anna.send_json({"type": "setting", "page": _ALL_DOMAINS, "name": "layout", "value": "gv-circo"})
        _expect(anna, "setting")
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"layout": "gv-neato"}})
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"colour": "red"}})
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"one_hop": False}})
        added = _expect(anna, "setting")
        room = _rooms(client).room(room_id)
        assert room is not None

    assert (added["name"], added["value"]) == ("one_hop", False)
    assert room.page_settings[_ALL_DOMAINS] == {"layout": "gv-circo", "one_hop": False}


def test_a_guest_cannot_seed(client: TestClient, source: str, capsys: pytest.CaptureFixture[str]) -> None:
    """(029 FR-001) Only the room's creator seeds; a guest's seed changes nothing and is logged as security."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        _expect(anna, "joined")
        boris.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"layout": "gv-neato"}})
        assert _wait_for(lambda: "did not open it" in capsys.readouterr().out)
        room = _rooms(client).room(room_id)
        assert room is not None

    assert room.page_settings.get(_ALL_DOMAINS, {}) == {}


def test_a_seed_over_the_message_limit_closes_with_4413(client: TestClient, source: str) -> None:
    """(029 FR-001) A seed is a room message like any other: over 4 KB it is refused, so the client never sends one."""
    with ExitStack() as stack:
        anna, _ = _open(stack, client, source)
        anna.send_json({"type": "seed", "page": _ALL_DOMAINS, "settings": {"disabled_entities": ["x" * 60] * 80}})
        code, _ = _closed(anna)

    assert code == 4413


def test_fifty_messages_a_second_pass_and_more_than_eighty_close(client: TestClient, source: str) -> None:
    """(029 FR-016) Pointer 20 + screen 20 + focus 10 a second fit the rooms route; a flood is closed with 4429."""
    with ExitStack() as stack:
        anna, _ = _open(stack, client, source)
        for i in range(50):
            anna.send_json({"type": "pointer", "kind": "mouse", "x": float(i), "y": 0.0})
        anna.send_json({"type": "rename", "name": "Anna"})
        assert "renamed" in _until(anna, "renamed")
        time.sleep(1.1)
        for i in range(90):
            anna.send_json({"type": "pointer", "kind": "mouse", "x": float(i), "y": 0.0})
        with pytest.raises(WebSocketDisconnect) as closed:
            while True:
                anna.receive_json()
    assert closed.value.code == 4429

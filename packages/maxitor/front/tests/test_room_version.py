# packages/maxitor/front/tests/test_room_version.py
"""In a room on a history the version is the room's (spec 037, FR-022a) — in Diff, the two compared (spec 038, FR-016): one pick moves everyone, the last pick wins, a bad pick moves nobody."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from tests.fixtures.stand_in_port import StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures


def _join(maxitor: TestClient, port: StandInPort, room: str, participant: str, version: str = "", version_a: str = "") -> Any:  # noqa: F811
    """A connection of ``participant`` to ``room`` (``new`` opens one on ``two``), with a fresh ticket."""
    ticket = open_history(maxitor, port, "two").json()["room_ticket"]
    query = {"participant": participant, "tab": f"{participant}-tab", "participant_name": participant.title(), "start_page": "view=full-graph", "ticket": ticket}
    if room == "new":
        query.update(history=port.name("two"), version=version, version_a=version_a)
    return maxitor.websocket_connect(f"/api/v1/rooms/{room}/live?{urlencode(query)}")


def _next(ws: Any, kind: str) -> dict[str, Any]:
    """The next event of ``kind``, skipping others."""
    for _ in range(30):
        event: dict[str, Any] = ws.receive_json()
        if event["type"] == kind:
            return event
    raise AssertionError(f"no {kind}")


def test_one_pick_moves_every_participant(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """SC-011: three participants; Anna picks the oldest version; all three hear it, and a newcomer gets it."""
    oldest = port.histories["two"].versions[0]["sha"][:12]
    with ExitStack() as stack:
        anna = stack.enter_context(_join(maxitor, port, "new", "anna"))
        room = anna.receive_json()["room"]["id"]
        boris = stack.enter_context(_join(maxitor, port, room, "boris"))
        vera = stack.enter_context(_join(maxitor, port, room, "vera"))
        for ws in (boris, vera):
            _next(ws, "welcome")
        anna.send_json({"type": "version", "b": oldest})
        for ws in (anna, boris, vera):
            assert _next(ws, "version")["b"] == oldest
        with _join(maxitor, port, room, "gleb") as gleb:
            assert _next(gleb, "welcome")["room"]["version"] == oldest


def test_the_last_of_two_picks_wins_for_everyone(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Two picks in a row: every participant ends on the second."""
    first, last = (port.histories["two"].versions[i]["sha"][:12] for i in (0, 2))
    with ExitStack() as stack:
        anna = stack.enter_context(_join(maxitor, port, "new", "anna"))
        room = anna.receive_json()["room"]["id"]
        boris = stack.enter_context(_join(maxitor, port, room, "boris"))
        _next(boris, "welcome")
        anna.send_json({"type": "version", "b": first})
        boris.send_json({"type": "version", "b": last})
        for ws in (anna, boris):
            seen = [_next(ws, "version")["b"], _next(ws, "version")["b"]]
            assert seen[-1] == last
        assert maxitor.app.state.rooms.room(room).version == last  # type: ignore[attr-defined]


def test_a_bad_pick_is_refused_to_its_sender_only(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A refused version, an unknown one and Live where there is none: an ``error`` to the picker; the room stays."""
    refused = port.histories["two"].versions[1]["sha"][:12]
    with ExitStack() as stack:
        anna = stack.enter_context(_join(maxitor, port, "new", "anna"))
        room = anna.receive_json()["room"]["id"]
        before = maxitor.app.state.rooms.room(room).version  # type: ignore[attr-defined]
        for bad in (refused, "0123456789ab", "live"):
            anna.send_json({"type": "version", "b": bad})
            assert "has no version" in _next(anna, "error")["reason"]
        assert maxitor.app.state.rooms.room(room).version == before  # type: ignore[attr-defined]


def test_a_room_opened_on_a_version_its_link_names(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A new room asked for the oldest version opens on it; asked for a refused one, on the default."""
    oldest, refused = (port.histories["two"].versions[i]["sha"][:12] for i in (0, 1))
    with _join(maxitor, port, "new", "anna", oldest) as anna:
        assert anna.receive_json()["room"]["version"] == oldest
    with _join(maxitor, port, "new", "boris", refused) as boris:
        assert boris.receive_json()["room"]["version"] == port.histories["two"].versions[2]["sha"][:12]


def test_a_range_moves_every_participant_and_a_newcomer_gets_it(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Diff in a room: A and B move as one value for everyone; a newcomer is told both."""
    oldest, newest = (port.histories["two"].versions[i]["sha"][:12] for i in (0, 2))
    with ExitStack() as stack:
        anna = stack.enter_context(_join(maxitor, port, "new", "anna"))
        room = anna.receive_json()["room"]["id"]
        boris = stack.enter_context(_join(maxitor, port, room, "boris"))
        _next(boris, "welcome")
        anna.send_json({"type": "version", "b": newest, "a": oldest})
        for ws in (anna, boris):
            event = _next(ws, "version")
            assert (event["a"], event["b"]) == (oldest, newest)
        with _join(maxitor, port, room, "vera") as vera:
            welcome = _next(vera, "welcome")["room"]
            assert (welcome["version_a"], welcome["version"]) == (oldest, newest)
        anna.send_json({"type": "version", "b": newest})
        assert _next(boris, "version")["a"] is None
        assert maxitor.app.state.rooms.room(room).version_a is None  # type: ignore[attr-defined]


def test_a_range_that_breaks_the_rules_is_refused_to_its_sender_only(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """The same version twice, Live as A, A after B, a refused A: an ``error`` to the picker; the room stays."""
    oldest, refused, newest = (port.histories["two"].versions[i]["sha"][:12] for i in (0, 1, 2))
    with ExitStack() as stack:
        anna = stack.enter_context(_join(maxitor, port, "new", "anna"))
        room = anna.receive_json()["room"]["id"]
        cases = [
            ({"b": newest, "a": newest}, "must differ"),
            ({"b": newest, "a": "live"}, "Live can only be the newer version"),
            ({"b": oldest, "a": newest}, "the older version must come first"),
            ({"b": newest, "a": refused}, "has no version"),
        ]
        for pick, words in cases:
            anna.send_json({"type": "version", **pick})
            assert words in _next(anna, "error")["reason"]
        assert maxitor.app.state.rooms.room(room).version_a is None  # type: ignore[attr-defined]


def test_a_room_opened_in_diff_keeps_its_pair_only_when_it_holds(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A new room asked for A and B opens on both; asked for them reversed, on B alone."""
    oldest, newest = (port.histories["two"].versions[i]["sha"][:12] for i in (0, 2))
    with _join(maxitor, port, "new", "anna", newest, oldest) as anna:
        room = anna.receive_json()["room"]
        assert (room["version_a"], room["version"]) == (oldest, newest)
    with _join(maxitor, port, "new", "boris", oldest, newest) as boris:
        assert boris.receive_json()["room"]["version_a"] is None

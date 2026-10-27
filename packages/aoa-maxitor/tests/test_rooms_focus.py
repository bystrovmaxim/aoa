# packages/aoa-maxitor/tests/test_rooms_focus.py
"""
What a followed person looks at reaches the people who follow them, and nobody else.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Spec 029, FR-010 and FR-011: a ``focus`` (the hovered element, the tooltip, the
selection, the open panels) is relayed — never run as an action, never logged — to
the tabs of the sender's followers only; a malformed one is dropped; a person who
starts following gets the target's last focus at once.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    unit:  focus_values(message) ──► checked fields | None
    app:   TestClient rooms ──► anna sends focus ──► boris (follows anna) gets it, vera does not
"""

from __future__ import annotations

import threading
from contextlib import ExitStack
from typing import Any

import pytest
from fastapi.testclient import TestClient

from aoa.maxitor.model.rooms.resources.room_registry import focus_values
from tests.test_rooms_server import _ALL_DOMAINS, _FULL_GRAPH, _connect, _expect, _open, _until, client, source

__all__ = ["client", "source"]

_PANELS = {"sidebar": ["domains"], "filter": "kinds", "legend": False}
_FOCUS: dict[str, Any] = {
    "type": "focus",
    "page": _FULL_GRAPH,
    "hover": {"kind": "node", "id": "Orders"},
    "tooltip": {"kind": "node", "id": "Orders"},
    "selection": None,
    "panels": _PANELS,
}


@pytest.mark.parametrize(
    ("change", "kept"),
    [
        ({}, True),
        ({"hover": {"kind": "planet", "id": "x"}}, False),
        ({"hover": {"kind": "node", "id": "x" * 513}}, False),
        ({"page": 7}, False),
        ({"panels": {**_PANELS, "sidebar": ["b"] * 201}}, False),
        ({"panels": {**_PANELS, "filter": "colours"}}, False),
        ({"panels": {**_PANELS, "legend": "yes"}}, False),
        ({"selection": {"kind": "row", "id": "Orders:id"}}, True),
    ],
)
def test_a_focus_is_checked_before_it_is_relayed(change: dict[str, Any], kept: bool) -> None:
    """Only the contract's kinds, lengths and sections pass; anything else drops the message."""
    assert (focus_values({**_FOCUS, **change}) is not None) is kept


def test_a_focus_reaches_followers_only(client: TestClient, source: str, capsys: pytest.CaptureFixture[str]) -> None:
    """Boris follows Anna and sees her focus; Vera, on the same page and not following, gets none; nothing is logged."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris"))
        _expect(boris, "welcome")
        vera = stack.enter_context(_connect(client, room_id, "vera"))
        _expect(vera, "welcome")
        boris.send_json({"type": "follow", "target": "anna"})
        _until(boris, "follows")
        _until(vera, "follows")
        anna.send_json(_FOCUS)
        boris.send_json({"type": "stop_following"})
        seen_by_boris = _events_until(boris, "follows")
        vera.send_json({"type": "rename", "name": "Vera"})
        seen_by_vera = _events_until(vera, "renamed")
    focus = [e for e in seen_by_boris if e["type"] == "focus"]
    assert focus and focus[0]["participant"] == "anna" and focus[0]["hover"] == {"kind": "node", "id": "Orders"}
    assert all(e["type"] != "focus" for e in seen_by_vera)
    assert "Orders" not in capsys.readouterr().out


def test_a_new_follower_gets_the_last_focus_at_once(client: TestClient, source: str) -> None:
    """Anna looked at something before Boris followed her: he sees it without her moving again."""
    with ExitStack() as stack:
        anna, room_id = _open(stack, client, source)
        boris = stack.enter_context(_connect(client, room_id, "boris", page=_ALL_DOMAINS))
        _expect(boris, "welcome")
        anna.send_json(_FOCUS)
        anna.send_json({"type": "rename", "name": "Anna"})
        _until(anna, "renamed")
        boris.send_json({"type": "follow", "target": "anna"})
        seen = _events_until(boris, "focus")
    assert seen[-1]["selection"] is None and seen[-1]["panels"] == _PANELS


def _events_until(ws: Any, kind: str, seconds: float = 3.0) -> list[dict[str, Any]]:
    """Every event up to and including the first of ``kind``; fails instead of waiting forever."""
    events: list[dict[str, Any]] = []
    while not events or events[-1]["type"] != kind:
        box: list[dict[str, Any]] = []
        reader = threading.Thread(target=lambda into=box: into.append(ws.receive_json()), daemon=True)
        reader.start()
        reader.join(seconds)
        if not box:
            pytest.fail(f"no {kind!r} within {seconds} s; got {[e['type'] for e in events]}")
        events.append(box[0])
    return events

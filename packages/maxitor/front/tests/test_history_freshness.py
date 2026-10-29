# packages/maxitor/front/tests/test_history_freshness.py
"""A held history stays current (spec 037, FR-006, FR-006a): an unchanged list costs a 304, a merge shows, a version is never rechecked, rooms follow."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from maxitor.front.model.core.actions.check_history_action import CheckHistoryAction, CheckHistoryParams
from maxitor.front.model.core.freshness import is_due
from maxitor.front.model.core.history_address import version_source
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY
from maxitor.front.model.core.resources.repo_graph_port_gateway import REPO_GRAPH_PORT_CONNECTION_KEY
from maxitor.front.model.rooms.resources.room_registry import ROOM_REGISTRY_KEY

from aoa.action_machine.context import Context
from tests.fixtures.stand_in_port import GRAPH_A, StandInPort, version
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures


def _check(maxitor: TestClient, history: str) -> str:  # noqa: F811
    """Run one ``CheckHistoryAction`` on the app's own resources; its status."""
    state = maxitor.app.state  # type: ignore[attr-defined]
    connections = {
        REPO_GRAPH_PORT_CONNECTION_KEY: state.history_connections[REPO_GRAPH_PORT_CONNECTION_KEY],
        HISTORY_STORE_CONNECTION_KEY: state.history_connections[HISTORY_STORE_CONNECTION_KEY],
        ROOM_REGISTRY_KEY: state.rooms,
    }
    result = maxitor.portal.call(state.machine.run, Context(), CheckHistoryAction(), CheckHistoryParams(history=history), connections)  # type: ignore[union-attr]
    return str(result.status)


def _room(maxitor: TestClient, port: StandInPort, history: str, participant: str = "anna") -> Any:  # noqa: F811
    """A room connection on ``history`` with a fresh ticket."""
    ticket = open_history(maxitor, port, history).json()["room_ticket"]
    query = {"participant": participant, "tab": f"{participant}-tab", "participant_name": participant.title(), "start_page": "view=full-graph", "history": port.name(history), "ticket": ticket}
    return maxitor.websocket_connect(f"/api/v1/rooms/new/live?{urlencode(query)}")


def _next(ws: Any, kind: str) -> dict[str, Any]:
    """The next event of ``kind``, skipping presence and the like."""
    for _ in range(20):
        event: dict[str, Any] = ws.receive_json()
        if event["type"] == kind:
            return event
    raise AssertionError(f"no {kind}")


def test_an_unchanged_list_costs_a_304(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A check of an unchanged history names its ETag, the port answers 304, nothing is replaced."""
    open_history(maxitor, port, "two")
    assert _check(maxitor, port.name("two")) == "unchanged"
    assert "If-None-Match" in port.headers[-2] or "If-None-Match" in port.headers[-1]


def test_a_merge_shows_after_one_check_and_nobody_moves(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """SC-012: a version the port starts listing is in the next answer to a polling tab; the chosen version is not moved."""
    key = port.histories["two"].key
    first = maxitor.get("/api/history/versions", params={"history": port.name("two")}, headers={"X-Maxitor-History-Key": key})
    merged = version(9, GRAPH_A)
    port.histories["two"].versions.append(merged)
    port.histories["two"].graphs[merged["sha"]] = GRAPH_A
    assert _check(maxitor, port.name("two")) == "changed"
    again = maxitor.get("/api/history/versions", params={"history": port.name("two")}, headers={"X-Maxitor-History-Key": key, "If-None-Match": first.headers["etag"]})
    assert again.status_code == 200 and [v["sha"] for v in again.json()["versions"]][-1] == merged["sha"]
    unchanged = maxitor.get("/api/history/versions", params={"history": port.name("two")}, headers={"X-Maxitor-History-Key": key, "If-None-Match": again.headers["etag"]})
    assert unchanged.status_code == 304


def test_a_version_is_never_due(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A version's held graph is never picked for a check, however old its last one."""
    sha = open_history(maxitor, port, "two").json()["versions"][0]["sha"]
    source = version_source(port.name("two"), None, sha)
    maxitor.get("/api/v1/full-graph", params={"source": source}, headers={"X-Maxitor-History-Key": port.histories["two"].key})
    held = maxitor.app.state.graph_store.peek(source)  # type: ignore[attr-defined]
    assert held.immutable and not is_due(held, held.last_checked + 10_000)


def test_a_room_hears_of_a_change_and_follows_a_version_gone(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """``history_changed`` reaches the room; when its version disappears, the room moves to the default one."""
    with _room(maxitor, port, "two") as ws:
        room = ws.receive_json()["room"]
        newest = port.histories["two"].versions[2]
        assert room["version"] == newest["sha"][:12]
        port.histories["two"].versions.remove(newest)
        assert _check(maxitor, port.name("two")) == "changed"
        assert _next(ws, "history_changed")["type"] == "history_changed"
        moved = _next(ws, "version")
        assert moved["b"] == port.histories["two"].versions[0]["sha"][:12] and moved["by"] is None


def test_live_removed_moves_a_room_on_live(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """M4 → M2: a room on Live moves to the newest unrefused version when ``live`` goes."""
    with _room(maxitor, port, "live") as ws:
        assert ws.receive_json()["room"]["version"] == "live"
        port.histories["live"].live = None
        assert _check(maxitor, port.name("live")) == "changed"
        moved = _next(ws, "version")
        assert moved["b"] == port.histories["live"].versions[2]["sha"][:12]

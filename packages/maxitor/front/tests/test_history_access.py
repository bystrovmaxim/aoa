# packages/maxitor/front/tests/test_history_access.py
"""Who may read a history: one "not found" for every refusal, the port's block passed on, one build shared by keys, a revoked key, a room's ticket."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from maxitor.front.model.core.history_address import version_source
from maxitor.front.model.core.resources import history_access
from starlette.websockets import WebSocketDisconnect

from tests.fixtures.stand_in_port import StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures

KEY = "X-Maxitor-History-Key"


def _read(maxitor: TestClient, port: StandInPort, key: str, sha: str) -> Any:  # noqa: F811
    """A diagram read of one version of ``two`` with ``key``."""
    return maxitor.get("/api/v1/full-graph", params={"source": version_source(port.name("two"), None, sha)}, headers={KEY: key})


def test_every_refusal_is_the_same_not_found(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A wrong key, no key, another history's key and an unknown history: the same ``404``."""
    asks = [
        {"params": {"history": port.name("two")}, "headers": {KEY: "wrong"}},
        {"params": {"history": port.name("two")}},
        {"params": {"history": port.name("two")}, "headers": {KEY: port.histories["one"].key}},
        {"params": {"history": port.name("nothing")}, "headers": {KEY: port.histories["two"].key}},
    ]
    for ask in asks:
        answer = maxitor.get("/api/history/open", **ask)
        assert (answer.status_code, answer.json()) == (404, {"detail": "not found"})


def test_the_ports_block_is_passed_on_and_not_retried(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """Once the port blocks: ``429`` with its words; Maxitor asked the port once for that request."""
    port.block_after = 0
    asked = len(port.requests)
    answer = maxitor.get("/api/history/open", params={"history": port.name("two")}, headers={KEY: "wrong"})
    assert (answer.status_code, answer.json()) == (429, {"detail": "Too many wrong keys for this history; try again in a minute"})
    assert len(port.requests) == asked + 1


def test_a_version_is_built_once_for_two_keys(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """SC-007: two readers with two keys, and the first again — the version's file is fetched from the port once."""
    port.histories["two"].more_keys.append("boris-key")
    sha = open_history(maxitor, port, "two").json()["versions"][0]["sha"]
    maxitor.get("/api/history/open", params={"history": port.name("two")}, headers={KEY: "boris-key"})
    for key in (port.histories["two"].key, "boris-key", port.histories["two"].key):
        assert _read(maxitor, port, key, sha).status_code == 200
    assert sum(1 for line in port.requests if line.endswith(f"/versions/{sha}")) == 1


def test_a_revoked_key_reads_no_version_held(maxitor: TestClient, port: StandInPort, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    """SC-013: once the acceptance is older than its window, a key the port revoked reads nothing — not even a held version."""
    old = port.histories["two"].key
    sha = open_history(maxitor, port, "two").json()["versions"][0]["sha"]
    assert _read(maxitor, port, old, sha).status_code == 200
    port.histories["two"].key = "a-new-key"
    monkeypatch.setattr(history_access, "ACCEPTED_FOR_SECONDS", -1.0)
    refused = _read(maxitor, port, old, sha)
    assert (refused.status_code, refused.json()) == (404, {"detail": "not found"})
    assert _read(maxitor, port, "wrong", sha).status_code == 404


def test_an_unknown_version_and_a_history_never_opened_are_not_found(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A commit the history does not list, and a version of a history nobody opened: ``404``."""
    open_history(maxitor, port, "two")
    assert _read(maxitor, port, port.histories["two"].key, "0" * 40).status_code == 404
    source = version_source(port.name("one"), None, port.histories["one"].versions[0]["sha"])
    assert maxitor.get("/api/v1/full-graph", params={"source": source}, headers={KEY: port.histories["one"].key}).status_code == 404


def _join(maxitor: TestClient, history: str, ticket: str) -> Any:  # noqa: F811
    """A room connection opening a room on ``history`` with ``ticket``."""
    query = {"participant": "anna", "tab": "anna-tab", "participant_name": "Anna", "start_page": "view=full-graph", "history": history, "ticket": ticket}
    return maxitor.websocket_connect(f"/api/v1/rooms/new/live?{urlencode(query)}")


@pytest.mark.parametrize("ticket", ["", "made-up", "used"])
def test_a_private_room_without_a_valid_ticket_learns_nothing(maxitor: TestClient, port: StandInPort, ticket: str) -> None:  # noqa: F811
    """No ticket, a made-up one, or one already used: closed with "not found" before ``welcome``."""
    issued = open_history(maxitor, port, "two").json()["room_ticket"]
    if ticket == "used":
        with _join(maxitor, port.name("two"), issued) as ws:
            assert ws.receive_json()["type"] == "welcome"
        ticket = issued
    with _join(maxitor, port.name("two"), ticket) as ws, pytest.raises(WebSocketDisconnect) as closed:
        ws.receive_json()
    assert (closed.value.code, closed.value.reason) == (4404, "not found")


def test_a_valid_ticket_opens_a_room_on_the_default_version(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """A fresh ticket: ``welcome`` names the history and its default version — the newest unrefused one in M2."""
    body = open_history(maxitor, port, "two").json()
    with _join(maxitor, port.name("two"), body["room_ticket"]) as ws:
        room = ws.receive_json()["room"]
    assert room["history"] == port.name("two") and room["version"] == body["versions"][2]["sha"][:12]
    assert port.histories["two"].key not in str(room)

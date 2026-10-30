# packages/maxitor/front/tests/test_history_modes.py
"""Every combination of Live and versions (spec 037, FR-009a, M1–M7) opens as its port describes it; a version reads as its graph."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.app import create_app
from maxitor.front.model.core.history_address import version_source

from tests.fixtures.stand_in_port import GRAPH_A, PUBLIC_LINK, StandInPort, counts
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures

#: Each private mode: the stand-in's history, how many versions, whether it has Live.
MODES = [("M2", "two", 3, False), ("M3", "one", 1, False), ("M4", "live", 3, True), ("M5", "live-one", 1, True), ("M6", "live-empty", 0, True), ("M7", "empty", 0, False)]


@pytest.mark.parametrize(("mode", "history", "count", "has_live"), MODES)
def test_each_private_mode_opens_as_its_port_says(maxitor: TestClient, port: StandInPort, mode: str, history: str, count: int, has_live: bool) -> None:  # noqa: F811
    """M2–M7: the count, the versions oldest first, Live or none, a room ticket; the name carries no key."""
    answer = open_history(maxitor, port, history)
    assert answer.status_code == 200, (mode, answer.text)
    body = answer.json()
    assert body["count"] == count and len(body["versions"]) == count
    assert [v["sha"] for v in body["versions"]] == [v["sha"] for v in port.histories[history].versions]
    assert (body["live"] is not None) == has_live
    assert body["title"] == history and body["host"] == "github" and body["room_ticket"]
    assert body["name"] == port.name(history) and port.histories[history].key not in answer.text
    assert [v["source"] for v in body["versions"]] == [version_source(port.name(history), None, v["sha"]) for v in body["versions"]]


def test_a_public_link_opens_through_maxitors_own_port(maxitor: TestClient) -> None:  # noqa: F811
    """A bare GitHub link: no key, no Live, no room ticket, its versions from Maxitor's own port."""
    body = maxitor.get("/api/history/open", params={"history": PUBLIC_LINK}).json()
    assert body["count"] == 3 and body["live"] is None and body["room_ticket"] is None
    assert body["title"] == "owner/service" and body["name"] == PUBLIC_LINK


def test_a_public_link_is_refused_when_maxitor_has_no_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``MAXITOR_PUBLIC_PORT``, a public link is refused with its words, nothing fetched."""
    monkeypatch.delenv("MAXITOR_PUBLIC_PORT", raising=False)
    with TestClient(create_app()) as client:
        answer = client.get("/api/history/open", params={"history": PUBLIC_LINK})
    assert (answer.status_code, answer.json()) == (400, {"detail": "Public histories are not set up on this Maxitor"})


def test_a_service_address_is_not_a_history(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """M1: a running service's address is not opened as a history, and its graph reads as today."""
    service = f"{port.base}/live/graph-json"
    assert maxitor.get("/api/history/open", params={"history": service}).status_code == 400
    assert maxitor.get("/api/v1/full-graph", params={"source": service}).status_code == 200


def _version_read(maxitor: TestClient, port: StandInPort, history: str, entry: dict[str, Any]) -> Any:  # noqa: F811
    """A diagram read of one version of ``history``, as the browser makes it."""
    source = version_source(port.name(history), None, entry["sha"])
    return maxitor.get("/api/v1/full-graph", params={"source": source}, headers={"X-Maxitor-History-Key": port.histories[history].key})


def test_every_version_reads_as_its_own_graph(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """SC-002: each listed, unrefused version of M2 and M4 is drawn from its own file, whose counts the port lists."""
    store = maxitor.app.state.graph_store  # type: ignore[attr-defined]
    for history in ("two", "live"):
        versions = open_history(maxitor, port, history).json()["versions"]
        for entry in versions:
            if entry.get("refused"):
                continue
            read = _version_read(maxitor, port, history, entry)
            assert read.status_code == 200, read.text
            graph = port.histories[history].graphs[entry["sha"]]
            held = store.peek(version_source(port.name(history), None, entry["sha"]))
            assert held.content_sha256 == hashlib.sha256(graph).hexdigest() and held.immutable
            assert counts(graph) == (entry["nodes"], entry["edges"])


def test_a_refused_version_is_refused_with_its_reason(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """The refused version answers ``422`` with the port's reason; the others still read."""
    versions = open_history(maxitor, port, "two").json()["versions"]
    refused = _version_read(maxitor, port, "two", versions[1])
    assert (refused.status_code, refused.json()) == (422, {"detail": "nodes[3]: 'id' is a required property"})
    assert _version_read(maxitor, port, "two", versions[2]).status_code == 200


def test_live_reads_as_a_running_service(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """M4's Live is its service's address, read like any service, with no key."""
    live = open_history(maxitor, port, "live").json()["live"]
    assert maxitor.get("/api/v1/full-graph", params={"source": live}).status_code == 200
    held = maxitor.app.state.graph_store.peek(live)  # type: ignore[attr-defined]
    assert held.content_sha256 == hashlib.sha256(GRAPH_A).hexdigest() and not held.immutable

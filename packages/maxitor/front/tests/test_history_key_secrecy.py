# packages/maxitor/front/tests/test_history_key_secrecy.py
"""A read key is never given away (spec 037, SC-004, SC-014): not in a log, an answer, a request line or a representation."""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from maxitor.front.api.access_log import WithoutQuery
from maxitor.front.api.history_key_auth_coordinator import HistoryKeyAuthCoordinator
from maxitor.front.model.core.history_address import parse_history, version_source
from maxitor.front.model.core.resources import history_access
from maxitor.front.model.core.resources.history_access import HISTORY_ACCESS_CONNECTION_KEY
from maxitor.front.model.core.resources.history_store import HISTORY_STORE_CONNECTION_KEY
from maxitor.front.model.core.resources.repo_graph_port_gateway import REPO_GRAPH_PORT_CONNECTION_KEY

from tests.fixtures.stand_in_port import PUBLIC_LINK, StandInPort
from tests.history_fixtures import maxitor, open_history, port  # noqa: F401 — fixtures
from tests.test_history_freshness import _check

KEY = "X-Maxitor-History-Key"


def test_a_session_over_every_mode_leaves_no_key_anywhere(maxitor: TestClient, port: StandInPort, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    """Every mode opened and polled, a version read, a room joined, wrong and revoked keys, checks run: no key in anything said."""
    said: list[str] = []
    for history in port.histories:
        answer = open_history(maxitor, port, history)
        said.append(answer.text)
        said.append(maxitor.get("/api/history/versions", params={"history": port.name(history)}, headers={KEY: port.histories[history].key}).text)
    said.append(maxitor.get("/api/history/open", params={"history": PUBLIC_LINK}).text)
    versions = open_history(maxitor, port, "two").json()["versions"]
    for entry in versions:
        source = version_source(port.name("two"), None, entry["sha"])
        said.append(maxitor.get("/api/v1/full-graph", params={"source": source}, headers={KEY: port.histories["two"].key}).text[:2000])
    ticket = open_history(maxitor, port, "two").json()["room_ticket"]
    query = {"participant": "anna", "tab": "t", "participant_name": "Anna", "start_page": "view=full-graph", "history": port.name("two"), "ticket": ticket}
    with maxitor.websocket_connect(f"/api/v1/rooms/new/live?{urlencode(query)}") as ws:
        said.append(str(ws.receive_json()))
    said.append(maxitor.get("/api/history/open", params={"history": port.name("one")}, headers={KEY: "wrong-key"}).text)
    old = port.histories["one"].key
    port.histories["one"].key = "renewed"
    monkeypatch.setattr(history_access, "ACCEPTED_FOR_SECONDS", -1.0)
    one = port.histories["one"].versions[0]["sha"]
    said.append(maxitor.get("/api/v1/full-graph", params={"source": version_source(port.name("one"), None, one)}, headers={KEY: old}).text)
    for history in port.histories:
        _check(maxitor, port.name(history))
    out = capsys.readouterr()
    state = maxitor.app.state  # type: ignore[attr-defined]
    held = state.history_connections[HISTORY_STORE_CONNECTION_KEY]
    reprs = [repr(held), repr(state.history_connections[HISTORY_ACCESS_CONNECTION_KEY]), repr(state.history_connections[REPO_GRAPH_PORT_CONNECTION_KEY]), repr(HistoryKeyAuthCoordinator())]
    reprs += [repr(held.peek(name)) for name in held.names()]
    reprs.append(repr(parse_history(port.address("two"))))
    everything = "\n".join([*said, out.out, out.err, *port.requests, *reprs])
    for key in [*port.keys(), old]:
        assert key not in everything
        assert hashlib.sha256(key.encode()).hexdigest() not in everything
    assert "refused the key from" in out.out


def test_the_key_reaches_the_port_only_in_its_header(maxitor: TestClient, port: StandInPort) -> None:  # noqa: F811
    """SC-014: the port saw every key it was sent in ``X-Maxitor-History-Key`` and in no request line."""
    open_history(maxitor, port, "two")
    assert any(f"X-Maxitor-History-Key: {port.histories['two'].key}" in headers for headers in port.headers)
    assert not any(port.histories["two"].key in line for line in port.requests)


def test_the_access_log_keeps_no_query() -> None:
    """uvicorn's request line, as the filter leaves it: method, path and status, never what follows ``?``."""
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d', ("127.0.0.1:5", "GET", "/api/v1/full-graph?source=https%3A%2F%2Fsecret", "1.1", 200), None)
    assert WithoutQuery().filter(record)
    assert record.getMessage() == '127.0.0.1:5 - "GET /api/v1/full-graph HTTP/1.1" 200'


def test_the_address_parser_never_shows_the_key() -> None:
    """A private history parsed from its address: the key is held, and shown in no representation or name."""
    history: Any = parse_history("https://port.example/api/v1/history/orders#key=the-secret-key")
    assert history.key == "the-secret-key"
    assert "the-secret-key" not in repr(history) and "the-secret-key" not in history.name

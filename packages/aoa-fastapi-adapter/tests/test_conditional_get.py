# packages/aoa-fastapi-adapter/tests/test_conditional_get.py
"""
Conditional GET — every successful ``GET`` answer of an adapter app carries an ``ETag`` of its
content, and a request that already holds that content gets ``304 Not Modified`` with no body.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A page that checks whether the graph it shows is still current asks the same ``GET`` again with
``If-None-Match``; an unchanged answer then costs a header, not a body (spec 028, FR-070,
contracts/http.md). The tag is a hash of the body, so two builds of the same app over the same
data — a restart — give the same tag.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    TestClient ── GET (If-None-Match?) ──► adapter app ──► action ──► 200 + ETag | 304
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.adapter import FastApiAdapter

from .support import PingAction, SimpleAction

_TAG = re.compile(r'^"[0-9a-f]{32}"$')


def _client() -> TestClient:
    """A fresh adapter app: ``GET /ping``, ``GET /simple?name=``, ``POST /ping``."""
    auth = AsyncMock()
    auth.process.return_value = Context()
    adapter = FastApiAdapter(machine=ActionProductMachine(loggers=[]), auth_coordinator=auth)
    adapter.get("/ping", PingAction)
    adapter.get("/simple", SimpleAction)
    adapter.post("/ping-post", PingAction)
    return TestClient(adapter.build())


def test_a_successful_get_carries_an_etag_of_its_content() -> None:
    """(1) A 200 to a GET carries ``ETag: "<32 hex>"``."""
    response = _client().get("/ping")
    assert response.status_code == 200
    assert _TAG.match(response.headers["etag"])


def test_the_same_tag_back_is_answered_304_without_a_body() -> None:
    """(2) Sending that tag back as ``If-None-Match`` gets 304, an empty body and the same tag."""
    client = _client()
    tag = client.get("/ping").headers["etag"]
    again = client.get("/ping", headers={"If-None-Match": tag})
    assert again.status_code == 304
    assert again.content == b""
    assert again.headers["etag"] == tag


def test_a_star_or_a_list_holding_the_tag_is_answered_304() -> None:
    """(3) ``*``, a list that holds the tag, and its weak form all match."""
    client = _client()
    tag = client.get("/ping").headers["etag"]
    for header in ("*", f'"0123", {tag}', f"W/{tag}"):
        assert client.get("/ping", headers={"If-None-Match": header}).status_code == 304, header


def test_another_tag_gets_the_body() -> None:
    """(4) A tag of other content gets the whole answer."""
    response = _client().get("/ping", headers={"If-None-Match": '"' + "0" * 32 + '"'})
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}


def test_a_post_and_a_refusal_carry_no_tag() -> None:
    """(5) Only a successful GET is tagged: a POST and a 4xx pass untouched."""
    client = _client()
    assert "etag" not in client.post("/ping-post", json={}).headers
    refused = client.get("/simple")
    assert refused.status_code == 422
    assert "etag" not in refused.headers


def test_the_tag_survives_a_restart() -> None:
    """(6) Two apps built the same way over the same data give the same tag."""
    first = _client().get("/simple", params={"name": "Alice"}).headers["etag"]
    second = _client().get("/simple", params={"name": "Alice"}).headers["etag"]
    assert first == second
    assert first != _client().get("/simple", params={"name": "Boris"}).headers["etag"]

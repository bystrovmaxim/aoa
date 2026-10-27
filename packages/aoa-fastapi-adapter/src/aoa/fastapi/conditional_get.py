# packages/aoa-fastapi-adapter/src/aoa/fastapi/conditional_get.py
"""
ConditionalGetMiddleware — an ``ETag`` on every successful ``GET``, and ``304`` when the client
already holds that content.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A client that checks whether what it shows is still current asks the same ``GET`` again with
``If-None-Match``. When nothing changed, the answer should cost a header, not a body (spec 028,
FR-070). The tag is the first 32 hex of the SHA-256 of the body the endpoint produced, so it
depends on the content alone: two builds of the same app over the same data — a restart — give
the same tag. This is transport work, like compression; it decides nothing about the domain.

Only a ``GET`` answered ``200`` is tagged. Every other method and status, and every WebSocket,
passes untouched.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET ──► endpoint ──► 200 + body (buffered) ──► ETag = "sha256(body)[:32]"
                                                   ├─ If-None-Match holds it ──► 304, no body
                                                   └─ otherwise              ──► 200 + ETag + body
"""

from __future__ import annotations

import hashlib
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Headers that describe a body; a ``304`` has none, so it does not carry them.
_BODY_HEADERS = frozenset({b"content-length", b"content-type", b"content-encoding"})


def entity_tag(body: bytes) -> str:
    """The strong ``ETag`` of ``body``: its SHA-256, first 32 hex, quoted."""
    return f'"{hashlib.sha256(body).hexdigest()[:32]}"'


def matches(if_none_match: str, tag: str) -> bool:
    """Whether an ``If-None-Match`` value names ``tag``: ``*``, or a list holding it, weak or strong."""
    for candidate in if_none_match.split(","):
        value = candidate.strip()
        if value == "*":
            return True
        if value.startswith("W/"):
            value = value[2:]
        if value == tag:
            return True
    return False


def _header(scope: Scope, name: bytes) -> str:
    """A request header of ``scope``, or ``""``."""
    for key, value in scope.get("headers", []):
        if key == name:
            return str(value.decode("latin-1"))
    return ""


class ConditionalGetMiddleware:
    """
    AI-CORE-BEGIN
    ROLE: Tag every successful GET answer with the hash of its body and answer 304 to a client that holds it.
    CONTRACT: Only GET with status 200 is buffered and tagged; everything else passes as it came.
    INVARIANTS: The tag depends on the body alone; a 304 carries the tag and no body.
    AI-CORE-END
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass anything but a GET through; buffer a GET's 200 answer and tag it."""
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return
        start: Message | None = None
        chunks: list[bytes] = []
        passthrough = False

        async def capture(message: Message) -> None:
            nonlocal start, passthrough
            if passthrough:
                await send(message)
            elif message["type"] == "http.response.start":
                if message["status"] == 200:
                    start = message
                else:
                    passthrough = True
                    await send(message)
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False) and start is not None:
                    await _answer(scope, start, b"".join(chunks), send)

        await self.app(scope, receive, capture)


async def _answer(scope: Scope, start: Message, body: bytes, send: Send) -> None:
    """Send the buffered 200 with its tag, or a 304 when the client already holds it."""
    tag = entity_tag(body)
    headers: list[Any] = [(key, value) for key, value in start.get("headers", []) if key != b"etag"]
    if matches(_header(scope, b"if-none-match"), tag):
        kept = [(key, value) for key, value in headers if key not in _BODY_HEADERS]
        await send({"type": "http.response.start", "status": 304, "headers": [*kept, (b"etag", tag.encode())]})
        await send({"type": "http.response.body", "body": b""})
        return
    await send({**start, "headers": [*headers, (b"etag", tag.encode())]})
    await send({"type": "http.response.body", "body": body})

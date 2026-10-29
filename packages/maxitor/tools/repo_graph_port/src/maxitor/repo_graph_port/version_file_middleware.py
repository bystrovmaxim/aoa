# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/version_file_middleware.py
"""
VersionFileMiddleware — a version's answer leaves the port as the graph file itself, cached for good.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``VersionAction`` answers ``{"graph": <the file's text>}``, as every action answers
a model. A reader wants the file — the very bytes that were committed — and, since a
version never changes, may keep it forever. This transport step unwraps the answer
into the file's bytes and marks it ``immutable``; it decides nothing about histories.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GET …/versions/<40 hex> ──► adapter ──► 200 {"graph": text} ──► body = text as UTF-8,
                                                                    Cache-Control: public, max-age=31536000, immutable

Every other path, method and status passes untouched — a ``304`` from the adapter's
conditional GET included.
"""

from __future__ import annotations

import json
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class VersionFileMiddleware:
    """
    AI-CORE-BEGIN
    ROLE: Send a version's answer as its graph file, cacheable forever.
    CONTRACT: Only a GET of ``/api/v1/history/…/versions/<sha>`` answered 200 is rewritten: body = the ``graph`` field's text, ``application/json``, ``Cache-Control: public, max-age=31536000, immutable``.
    AI-CORE-END
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass anything else through; buffer a version's 200 answer and send its file."""
        version_path = r"/api/v1/history/(?:public|[^/]+)/versions/[0-9a-f]{40}"
        if scope["type"] != "http" or scope["method"] != "GET" or re.fullmatch(version_path, scope["path"]) is None:
            await self.app(scope, receive, send)
            return
        started: Message = {}
        body = bytearray()

        async def capture(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = message
                if message["status"] != 200:
                    await send(message)
                return
            if started.get("status") != 200:
                await send(message)
                return
            body.extend(message.get("body", b""))
            if message.get("more_body"):
                return
            content = json.loads(body)["graph"].encode("utf-8")
            kept = [(k, v) for k, v in started["headers"] if k not in (b"content-length", b"content-type", b"cache-control")]
            headers = [*kept, (b"content-type", b"application/json"), (b"content-length", str(len(content)).encode()),
                       (b"cache-control", b"public, max-age=31536000, immutable")]
            await send({**started, "headers": headers})
            await send({"type": "http.response.body", "body": content})

        await self.app(scope, receive, capture)

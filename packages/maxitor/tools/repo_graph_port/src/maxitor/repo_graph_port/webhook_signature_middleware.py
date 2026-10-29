# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/webhook_signature_middleware.py
"""
WebhookSignatureMiddleware — only a body GitHub signed reaches the webhook's action.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

GitHub signs every webhook's raw body with the App's secret (``X-Hub-Signature-256``).
The signature must be checked over the bytes exactly as they arrived — before
anything parses them — so this transport step reads the body, checks it, and only
then hands the same bytes on. A body it cannot vouch for never reaches the action.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    POST /api/v1/history/events/github ──► the whole body read ──► verify(body, signature)
        ├─ false ──► 401 {"detail": "bad signature"}
        └─ true  ──► the same body replayed to the adapter ──► ReceiveHostEventAction

Every other path passes untouched.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class WebhookSignatureMiddleware:
    """
    AI-CORE-BEGIN
    ROLE: Let through to the webhook's route only a body whose signature checks.
    CONTRACT: ``verify(body, signature)`` decides; a POST to the webhook's path that fails it is answered ``401`` and goes no further.
    AI-CORE-END
    """

    def __init__(self, app: ASGIApp, verify: Callable[[bytes, str], bool]) -> None:
        self.app = app
        self.verify = verify

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Check a webhook's body; pass anything else through."""
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/v1/history/events/github":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            body.extend(message.get("body", b""))
            if not message.get("more_body"):
                break
        signature = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"x-hub-signature-256"), "")
        if not self.verify(bytes(body), signature):
            content = json.dumps({"detail": "bad signature"}).encode()
            headers = [(b"content-type", b"application/json"), (b"content-length", str(len(content)).encode())]
            await send({"type": "http.response.start", "status": 401, "headers": headers})
            await send({"type": "http.response.body", "body": content})
            return
        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                return await receive()
            sent = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, replay, send)

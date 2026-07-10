# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/bearer_credential_extractor.py
"""
BearerCredentialExtractor — pull a Bearer token out of the Authorization header.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``CredentialExtractor`` implementation for the ``Authorization: Bearer <jwt>``
scheme (RFC 6750). Returns ``{"token": "<jwt>"}`` when a well-formed Bearer
header is present, else an empty dict — "no credentials", not an error;
downstream ``AuthCoordinator.process()`` returns ``None`` in that case.

Duck-types ``request_data.headers`` as a case-insensitive ``Mapping``-like
object exposing ``.get(name)`` (true for Starlette's ``Request.headers`` and
similar ASGI request wrappers).

``request_data`` with no ``.headers`` at all (e.g. ``None``) is a *wiring*
error, not a missing-credentials case, and raises ``TypeError`` instead of
silently degrading to "no credentials". This is exactly what happens if this
extractor (via ``JwtAuthCoordinator``) is wired into ``aoa-mcp-adapter``:
``McpAdapter`` always calls ``auth_coordinator.process(None)`` regardless of
transport — there is no request object to read a header from. See
``docs/extensions/jwt_draft.md`` and
https://github.com/bystrovmaxim/aoa/issues/113.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.auth_coordinator import CredentialExtractor

_SCHEME = "bearer"


class BearerCredentialExtractor(CredentialExtractor):
    """
    AI-CORE-BEGIN
    ROLE: Extract a Bearer token from the Authorization header.
    CONTRACT: Missing header, wrong scheme, or empty token -> {} (no credentials). request_data with no .headers at all -> TypeError (wiring error, not a missing-credentials case).
    AI-CORE-END
    """

    async def extract(self, request_data: Any) -> dict[str, Any]:
        headers = getattr(request_data, "headers", None)
        if headers is None:
            raise TypeError(
                "BearerCredentialExtractor requires request_data exposing a `.headers` "
                f"mapping (e.g. a Starlette/FastAPI Request); got {request_data!r}. "
                "This coordinator cannot be used with an adapter that never forwards "
                "request data — e.g. aoa-mcp-adapter always calls process(None), "
                "regardless of transport (see docs/extensions/jwt_draft.md)."
            )
        header = headers.get("authorization")
        if not header:
            return {}
        scheme, _, token = header.partition(" ")
        token = token.strip()
        if scheme.lower() != _SCHEME or not token:
            return {}
        return {"token": token}

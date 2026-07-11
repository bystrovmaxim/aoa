# packages/aoa-action-machine/src/aoa/action_machine/auth/jwt_auth/cookie_credential_extractor.py
"""
CookieCredentialExtractor — pull a JWT out of an HTTP cookie.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``CredentialExtractor`` implementation for same-site SSO across subdomains: a
central login service sets a domain-wide, ``httpOnly`` session cookie
(``domain=.example.com``); browsers attach it automatically to every request
to every subdomain, but ``httpOnly`` makes it invisible to JavaScript, so the
frontend cannot copy the token into an ``Authorization`` header the way
``BearerCredentialExtractor`` expects. The JWT physically arrives in the
``Cookie:`` header instead.

Returns ``{"token": "<jwt>"}`` when the configured cookie is present and
non-blank, else an empty dict — "no credentials", not an error; downstream
``AuthCoordinator.process()`` returns ``None`` in that case.

Duck-types ``request_data.cookies`` as a plain ``dict[str, str]`` (true for
Starlette's ``Request.cookies`` and similar ASGI request wrappers) — no
Starlette import.

``request_data`` with no ``.cookies`` at all (e.g. ``None``) is a *wiring*
error, not a missing-credentials case, and raises ``TypeError`` instead of
silently degrading to "no credentials" — the same contract
``BearerCredentialExtractor`` uses for ``.headers``. This is exactly what
happens if this extractor (via ``JwtAuthCoordinator``) is wired into
``aoa-mcp-adapter``: ``McpAdapter`` always calls
``auth_coordinator.process(None)`` regardless of transport — there is no
request object to read a cookie from. See ``docs/extensions/jwt_draft.md``
and https://github.com/bystrovmaxim/aoa/issues/113.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.auth.auth_coordinator import CredentialExtractor


class CookieCredentialExtractor(CredentialExtractor):
    """
    AI-CORE-BEGIN
    ROLE: Extract a JWT from a named HTTP cookie.
    CONTRACT: Missing, empty, or whitespace-only cookie -> {} (no credentials). request_data with no .cookies at all -> TypeError (wiring error, not a missing-credentials case). The error message never echoes a cookie value.
    AI-CORE-END
    """

    def __init__(self, cookie_name: str) -> None:
        self._cookie_name = cookie_name

    async def extract(self, request_data: Any) -> dict[str, Any]:
        cookies = getattr(request_data, "cookies", None)
        if cookies is None:
            raise TypeError(
                "CookieCredentialExtractor requires request_data exposing a `.cookies` "
                f"mapping (e.g. a Starlette/FastAPI Request); got {request_data!r}. "
                "This coordinator cannot be used with an adapter that never forwards "
                "request data — e.g. aoa-mcp-adapter always calls process(None), "
                "regardless of transport (see docs/extensions/jwt_draft.md)."
            )
        value = cookies.get(self._cookie_name)
        if not value:
            return {}
        token = value.strip()
        if not token:
            return {}
        return {"token": token}

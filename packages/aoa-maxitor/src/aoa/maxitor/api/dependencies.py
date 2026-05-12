# packages/aoa-maxitor/src/aoa/maxitor/api/dependencies.py
"""
FastAPI dependencies for Maxitor runtime state.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provide typed access to the app-scoped :class:`MaxitorApiSession` created during
ASGI lifespan startup.
"""

from __future__ import annotations

from fastapi import Request

from aoa.maxitor.api.session import MaxitorApiSession


def get_maxitor_session(request: Request) -> MaxitorApiSession:
    """
    Return the app-scoped Maxitor API session.

    AI-CORE-BEGIN
    ROLE: Bridge FastAPI request state to typed route handlers.
    FAILURES: Raises ``RuntimeError`` when called before lifespan startup completes.
    AI-CORE-END
    """
    session = getattr(request.app.state, "maxitor_session", None)
    if not isinstance(session, MaxitorApiSession):
        msg = "Maxitor API session is not initialized."
        raise RuntimeError(msg)
    return session


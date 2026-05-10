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
from aoa.maxitor.model.core.resources.service_graph_resource import ServiceGraphResource


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


def get_interchange_nx_resource(request: Request) -> ServiceGraphResource:
    """
    Return a resource wrapper around the app-scoped interchange ``nx_graph``.

    AI-CORE-BEGIN
    ROLE: Same graph instance as ActionMachine ``connections["ServiceGraph"]`` for manual routes.
    CONTRACT: Builds a fresh resource shell per request; inner ``DiGraph`` is shared from session.
    AI-CORE-END
    """
    return ServiceGraphResource(get_maxitor_session(request).nx_graph)

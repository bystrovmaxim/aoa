# packages/aoa-maxitor/src/aoa/maxitor/api/maxitor_connection_holder.py
"""
MaxitorConnectionHolder — session-scoped ``ServiceGraphResource`` for diagram routes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Filled during ASGI ``lifespan`` with the same ``MaxitorApiSession`` as the rest
of the app. It is not an adapter-level connections factory: diagram routes pass
``PerCallConnection(holder.service_graph_resource)`` in their own ``connections``
mapping. Each request invokes that factory so actions receive a
``ServiceGraphResource`` bound to the current ``nx_graph``.
"""

from __future__ import annotations

from aoa.maxitor.api.session import MaxitorApiSession
from aoa.maxitor.model.core.resources.service_graph_resource import ServiceGraphResource


class MaxitorConnectionHolder:
    """Attach session after lifespan startup; expose ``ServiceGraphResource`` for routes."""

    def __init__(self) -> None:
        self._session: MaxitorApiSession | None = None

    @property
    def session(self) -> MaxitorApiSession | None:
        """Current app session, or ``None`` before ``lifespan`` completes."""
        return self._session

    def set_session(self, session: MaxitorApiSession) -> None:
        """Bind the app-scoped session (call once from lifespan)."""
        self._session = session

    def service_graph_resource(self) -> ServiceGraphResource:
        """Return a ``ServiceGraphResource`` for the live interchange graph."""
        if self._session is None:
            msg = "MaxitorConnectionHolder has no session; lifespan did not run."
            raise RuntimeError(msg)
        return ServiceGraphResource(self._session.nx_graph)

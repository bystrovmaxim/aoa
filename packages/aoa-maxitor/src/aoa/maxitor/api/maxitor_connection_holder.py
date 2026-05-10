# packages/aoa-maxitor/src/aoa/maxitor/api/maxitor_connection_holder.py
"""
MaxitorConnectionHolder — builds ActionMachine ``connections`` for FastApiAdapter.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``FastApiAdapter`` calls ``connections_factory()`` with no request context.
This holder is filled during ASGI lifespan with the same ``MaxitorApiSession``
that manual routes use, so every adapter run receives the shared nx graph
resource instance.
"""

from __future__ import annotations

from aoa.action_machine.resources.base_resource import BaseResource
from aoa.maxitor.api.resources.maxitor_interchange_nx_resource import MaxitorInterchangeNxResource
from aoa.maxitor.api.session import MaxitorApiSession


class MaxitorConnectionHolder:
    """Lazily attach session after lifespan startup; ``__call__`` is the adapter factory."""

    def __init__(self) -> None:
        self._session: MaxitorApiSession | None = None

    def set_session(self, session: MaxitorApiSession) -> None:
        """Bind the app-scoped session (call once from lifespan)."""
        self._session = session

    def __call__(self) -> dict[str, BaseResource]:
        """Return ActionMachine ``connections`` for diagram actions."""
        if self._session is None:
            msg = "MaxitorConnectionHolder has no session; lifespan did not run."
            raise RuntimeError(msg)
        return {"interchange_nx": MaxitorInterchangeNxResource(self._session.nx_graph)}

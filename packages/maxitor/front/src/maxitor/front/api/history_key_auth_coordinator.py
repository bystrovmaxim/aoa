# packages/maxitor/front/src/maxitor/front/api/history_key_auth_coordinator.py
"""
HistoryKeyAuthCoordinator — give a history request its context, with the key it sent.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor does not check a read key: the port that serves the history does. The history
routes still need the key, to pass it on, and the reader's address, to name it in a
security warning (spec 037, FR-011e). This coordinator reads both from the request and
lets every request through, a guest without a key — a public history needs none, and a
private one is refused by its port, not here.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    request ──X-Maxitor-History-Key──► HistoryKeyHolder(history_key)
            └──► RequestInfo(client_ip, request_path, request_method)
                                            └──► Context(user, request)
"""

from __future__ import annotations

from typing import Any

from maxitor.front.model.core.history_key_holder import HistoryKeyHolder

from aoa.action_machine.context import Context, RequestInfo
from aoa.action_machine.runtime.base_coordinator import BaseCoordinator

#: The one header a read key travels in.
HISTORY_KEY_HEADER = "x-maxitor-history-key"


class HistoryKeyAuthCoordinator(BaseCoordinator):
    """
    AI-CORE-BEGIN
    ROLE: Build the context of a history request: the key it sent and where it came from.
    CONTRACT: ``process`` never returns ``None``; ``user.history_key`` is the header's trimmed value or ``""``.
    INVARIANTS: Checks nothing and logs nothing; reads no key from the path or the query.
    AI-CORE-END
    """

    def __repr__(self) -> str:
        """Name the coordinator only."""
        return "HistoryKeyAuthCoordinator()"

    async def process(self, request_data: Any) -> Context:
        """The request's context: its key, if any, and its metadata."""
        key = request_data.headers.get(HISTORY_KEY_HEADER, "").strip()
        # Read here rather than through the JWT extra's assembler, which Maxitor's image does not install.
        client = getattr(request_data, "client", None)
        request = RequestInfo(
            request_path=request_data.url.path,
            request_method=request_data.method,
            client_ip=client.host if client else None,
        )
        return Context(user=HistoryKeyHolder(history_key=key), request=request)

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
            └──HttpContextAssembler──► RequestInfo(client_ip, request_path, …)
                                            └──► Context(user, request)
"""

from __future__ import annotations

from typing import Any

from maxitor.front.model.core.history_key_holder import HistoryKeyHolder

from aoa.action_machine.auth.jwt_auth.http_context_assembler import HttpContextAssembler
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

    def __init__(self) -> None:
        self._assembler = HttpContextAssembler()

    def __repr__(self) -> str:
        """Name the coordinator only."""
        return "HistoryKeyAuthCoordinator()"

    async def process(self, request_data: Any) -> Context:
        """The request's context: its key, if any, and its metadata."""
        key = request_data.headers.get(HISTORY_KEY_HEADER, "").strip()
        request = RequestInfo(**await self._assembler.assemble(request_data))
        return Context(user=HistoryKeyHolder(history_key=key), request=request)

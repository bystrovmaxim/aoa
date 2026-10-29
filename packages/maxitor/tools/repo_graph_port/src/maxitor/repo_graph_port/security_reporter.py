# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/security_reporter.py
"""
SecurityReporter — hand a security event from outside an action to the action that logs it.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The auth coordinator and the webhook's middleware refuse before any action runs, but
their refusals belong in the log like any other event, written through a ``box``. This
object runs ``ReportSecurityEventAction`` on the port's machine for them.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    HistoryKeyAuthCoordinator ─┐
                               ├─► report(kind, client, history, count) ──► machine.run(ReportSecurityEventAction)
    WebhookSignatureMiddleware ┘
"""

from __future__ import annotations

from maxitor.repo_graph_port.actions.report_security_event_action import (
    ReportSecurityEventAction,
    ReportSecurityEventParams,
    SecurityEventKind,
)

from aoa.action_machine.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class SecurityReporter:
    """
    AI-CORE-BEGIN
    ROLE: Run the action that logs a security event, for code that is not an action.
    CONTRACT: ``report`` writes one event and returns when it is written; it is given no key, hash or signature.
    AI-CORE-END
    """

    def __init__(self, machine: ActionProductMachine) -> None:
        self._machine = machine

    def __repr__(self) -> str:
        """Name the reporter only."""
        return "SecurityReporter()"

    async def report(self, kind: SecurityEventKind, client: str, history: str = "", count: int = 0) -> None:
        """Write one security event: ``wrong_key``, ``bad_signature`` or ``blocked``."""
        params = ReportSecurityEventParams(kind=kind, client=client or "unknown", history=history, count=count)
        await self._machine.run(Context(), ReportSecurityEventAction(), params)

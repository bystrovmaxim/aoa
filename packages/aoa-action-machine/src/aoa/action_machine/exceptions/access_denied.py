# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_denied.py
"""
AccessDenied — carry a refused execution decision to the caller.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Expose the refusal's gate and optional developer-supplied reason when execution
cannot proceed. A preliminary access query returns the verdict directly.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Refused → machine.run → AccessDenied.verdict → caller
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control.refused import Refused


class AccessDenied(Exception):
    """
    Carry the verdict that refused execution.

    AI-CORE-BEGIN
    ROLE: Execution exception exposing the refused decision through ``verdict``.
    CONTRACT: ``gate`` is one of ``AUTH_COORDINATOR``, ``CHECK_ROLES``, ``ACCESS_DECIDE``; an optional ``reason`` carries the developer's text.
    INVARIANTS: The message names the gate and includes the reason only when present; no numeric authorization level is added.
    AI-CORE-END
    """

    def __init__(self, verdict: Refused) -> None:
        super().__init__(self._message(verdict))
        self.verdict = verdict

    @staticmethod
    def _message(verdict: Refused) -> str:
        """Name the step that refused, and repeat the developer's reason when there is one."""
        if verdict.reason is None:
            return f"Access denied by {verdict.gate.value}."
        return f"Access denied by {verdict.gate.value}: {verdict.reason}"

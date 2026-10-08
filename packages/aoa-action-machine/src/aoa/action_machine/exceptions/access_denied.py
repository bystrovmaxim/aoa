# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_denied.py
"""AccessDenied."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control.refused import Refused


class AccessDenied(Exception):
    """
    Raised when a call must not proceed, carrying the decision that stopped it.

    The verdict is the exception: ``gate`` names the step that refused — one of the five
    published words — and ``reason`` carries the developer's text when they declared one
    beside the condition that refused. There is nothing else: no level vocabulary beside
    the words, and no text the framework wrote of its own.
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

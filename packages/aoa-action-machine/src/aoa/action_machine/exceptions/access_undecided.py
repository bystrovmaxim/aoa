# packages/aoa-action-machine/src/aoa/action_machine/exceptions/access_undecided.py
"""AccessUndecided."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.intents.access_control.undecided import Undecided


class AccessUndecided(Exception):
    """
    Raised when a gate could not complete, so the call is neither allowed nor refused.

    The verdict names the step that could not tell. The failure that stopped it is the
    exception's cause — raised ``from`` it, so the traceback keeps what really happened —
    and the failure's text reaches neither an answer nor an event (FR-005, FR-015).
    """

    def __init__(self, verdict: Undecided) -> None:
        super().__init__(f"Access could not be decided by {verdict.gate.value}.")
        self.verdict = verdict

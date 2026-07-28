# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/allowed_verdict.py
"""Yes: nothing objected, the call may go ahead."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.access_control.base_verdict import BaseVerdict


class AllowedVerdict(BaseVerdict):
    """
    AI-CORE-BEGIN
        ROLE: The "yes" of the three access-check answers, and the one an action gives
              unless it says otherwise.
        CONTRACT: Takes no arguments; kind is "AllowedVerdict". Nothing accompanies it.
        INVARIANTS: No reason field exists here, so an allow cannot carry one.
    AI-CORE-END

    An allow has no reason field. It does not need one -- nothing was wrong, so there is
    nothing to name. Attaching one anyway is refused, not ignored.
    """

    def __init__(self, kind: str = "AllowedVerdict", **kwargs: Any) -> None:
        super().__init__(kind=kind, **kwargs)

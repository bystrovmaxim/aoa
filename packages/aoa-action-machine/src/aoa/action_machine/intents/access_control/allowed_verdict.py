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

    There is nothing to explain when nothing objected, which is why this is the only one
    of the three with no reason: the field is absent rather than empty. Anything reading
    a batch of answers can tell an allow from a refusal without looking further than the
    class.
    """

    def __init__(self, kind: str = "AllowedVerdict", **kwargs: Any) -> None:
        super().__init__(kind=kind, **kwargs)

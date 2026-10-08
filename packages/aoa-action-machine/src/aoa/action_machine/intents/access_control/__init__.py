# packages/aoa-action-machine/src/aoa/action_machine/intents/access_control/__init__.py
"""
Access control — the three answers a decision can end in, and the words of the steps that decide.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One decision mechanism serves both the execution path and the question path, and
it ends in exactly one of three answers: ``Allowed``, ``Refused`` or
``Undecided``. Each answer carries the published word a caller branches on, and a
refusal or an undecided answer also names the step it came from — one of the five
words of ``Gate``.

The framework publishes those words and invents no reason text: a ``reason``
belongs to the developer who declared a condition, and ``FORBIDDEN_OBJECT`` is
the one shared refusal an object-scoped check returns.

The package no longer carries the old batch answer, the answer the question path returns
while the change is in progress; it is replaced once the machine answers with the
three answers above.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Verdict  (the base: kind, frozen, extra="forbid")
      ├── Allowed    kind="allowed"
      ├── Refused    kind="refused"    gate, reason?
      └── Undecided  kind="undecided"  gate, private cause

    Gate
      ├── AUTH_COORDINATOR   the credentials were rejected
      ├── CHECK_ROLES        no listed role is held
      ├── WHEN               a role is held, but the condition its grant declared refused
      ├── GUARD              the operation's shared condition refused
      └── ACCESS_DECIDE      the object may not be touched

    decide() ──▶ an answer ──▶ decision event ──▶ whoever reads it

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.access_decide import access_decide
    from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Refused

    @access_decide("Refuse an order that is not the caller's")
    async def cancel_order_access_decide(
        self,
        params: CancelOrderAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        order = await connections["db"].get(params.order_id)
        if order is None or order.owner_id != context.user.user_id:
            return FORBIDDEN_OBJECT                    # one branch, one answer
        if order.status == "cancelled":
            return Refused("ORDER_ALREADY_CANCELLED")  # the developer's own reason
        return Allowed()
"""

from __future__ import annotations

from aoa.action_machine.intents.access_control.allowed import Allowed
from aoa.action_machine.intents.access_control.cascade import (
    GATES,
    GATES_AT_OBJECT,
    GATES_BEFORE_RUN,
    Step,
    StepAnswer,
    decide,
)
from aoa.action_machine.intents.access_control.gate import Gate
from aoa.action_machine.intents.access_control.refused import FORBIDDEN_OBJECT, Refused
from aoa.action_machine.intents.access_control.undecided import Undecided
from aoa.action_machine.intents.access_control.verdict import Verdict

__all__ = [
    "FORBIDDEN_OBJECT",
    "GATES",
    "GATES_AT_OBJECT",
    "GATES_BEFORE_RUN",
    "Allowed",
    "Gate",
    "Refused",
    "Step",
    "StepAnswer",
    "Undecided",
    "Verdict",
    "decide",
]

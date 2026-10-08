# packages/aoa-action-machine/src/aoa/action_machine/intents/access_decide/__init__.py
"""
Access decide — the operation's own answer about the object it is called on.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The object check is a declaration: an operation writes one method, marks it, and
the assembled graph carries it. Declaring nothing is a legitimate choice — such
an operation has no object check at all.

Three rules come with the declaration, and all three are checked before a call
is served:

- **at most one** per operation — two answers to the same question leave nobody
  able to say which one decided (:exc:`~aoa.action_machine.exceptions.DuplicateAccessDecideError`);
- **never inherited** — a subclass does not take over the decision its parent
  made about a different object (the lookup reads the operation's own namespace);
- the method's name carries the required suffix, and the method is ``async``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @access_decide                     mark the method (this package)
          │
    AccessDecideIntentResolver         find it in the operation's own namespace
          │
    ActionGraphNode.properties[…]      the assembled graph carries it
          │
    object step of the cascade         call it, judge the answer

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from aoa.action_machine.intents.access_decide import access_decide

    @meta(description="Cancel an order", domain=ShopDomain)
    @check_roles(ManagerRole)
    class CancelOrderAction(BaseAction["CancelOrderAction.Params", "CancelOrderAction.Result"]):
        @access_decide("Refuse an order that is not the caller's, or one that is locked")
    async def cancel_order_access_decide(self, params, context, box, connections):
            return Allowed()
"""

from __future__ import annotations

from aoa.action_machine.intents.access_decide.access_decide_decorator import access_decide
from aoa.action_machine.intents.access_decide.access_decide_intent import AccessDecideIntent
from aoa.action_machine.intents.access_decide.access_decide_intent_resolver import AccessDecideIntentResolver

__all__ = [
    "AccessDecideIntent",
    "AccessDecideIntentResolver",
    "access_decide",
]

"""
03_guard.py — guard=: one condition over any role

guard= is a single condition on @check_roles, shared by every grant — it runs
once, after a grant has already matched (role, and that grant's own when=, if
any). Unlike grant(role, when=...) it does not vary per role: the same
condition applies no matter which grant let the caller in.

This example uses one minimal role (not the AdminRole/ManagerRole hierarchy
from 01_roles.py — a guard= demo doesn't need it) and a guard= that blocks a
locked order regardless of who is asking, as long as they hold the role at all.

Tutorial: ../../docs/index_draft.md  ·  topic: Authorization and roles

Run:
    uv run python examples/step_03_authorization_and_roles/03_guard.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.authorization_error import AuthorizationError
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


# ---------------------------------------------------------------------------
# One minimal role — this example is about guard=, not about role hierarchies.
# ---------------------------------------------------------------------------

class StaffRole(ApplicationRole):
    name = "staff"
    description = "Store staff"


# ---------------------------------------------------------------------------
# Params / Result
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    action: str = Field(description="What was performed")


# ---------------------------------------------------------------------------
# guard= is shared by every grant on this action (here, just the one bare
# StaffRole) — a locked order is refused no matter who holds the role.
# ---------------------------------------------------------------------------

@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(
    StaffRole,
    guard=lambda user, params: not params.order_id.startswith("LOCKED-"),
    reason="order is locked",
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, action="cancelled")


# ---------------------------------------------------------------------------
# Runner — same principal, two orders: guard= depends on the call, not on who
# is calling. The anonymous row shows the role gate still runs first: guard=
# is never even evaluated for a caller without StaffRole.
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()
    staff = Context(user=UserInfo(user_id="s1", roles=(StaffRole,)))

    cases = [
        ("anonymous, regular order", Context(), "ord-001"),
        ("staff, regular order", staff, "ord-001"),
        ("staff, locked order", staff, "LOCKED-002"),
    ]

    for label, ctx, order_id in cases:
        try:
            await machine.run(ctx, CancelOrderAction(), OrderParams(order_id=order_id))
            print(f"{label:<28} -> allowed")
        except AuthorizationError:
            print(f"{label:<28} -> denied")


asyncio.run(main())

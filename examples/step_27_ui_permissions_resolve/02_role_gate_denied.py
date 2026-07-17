"""
02_role_gate_denied.py — an honest "no", with a reason for developers only

Same action as 01_role_gate_allowed.py, different caller: a plain user, not a
manager. The role check rejects the call, and this time scope really is
"role" (AccessVerdict.level is set to whichever cascade level rejected —
here, level 1, the role check itself).

reason carries developer-facing text ("not a manager" style), not something
to show the end user as-is. reason_code — the stable, translatable code a
frontend could safely switch on — is still None here: that taxonomy is
Chapter 2's job, not this one's.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/02_role_gate_denied.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.permissions import to_wire


class StoreDomain(BaseDomain):
    name = "store"
    description = "Store domain"


class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Can manage orders"


class UserRole(ApplicationRole):
    name = "user"
    description = "Standard user — cannot manage orders"


class OrderParams(BaseParams):
    order_id: int = Field(description="Order identifier")


class OrderResult(BaseResult):
    status: str = Field(description="New order status")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        return OrderResult(status="cancelled")


async def main() -> None:
    machine = ActionProductMachine()
    user = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))

    verdict = await machine.check_access_decide(user, CancelOrderAction, OrderParams(order_id=7))
    wire_verdict = to_wire(verdict)

    print(f"allowed     = {wire_verdict.allowed}")
    print(f"scope       = {wire_verdict.scope!r}")  # "role" — level 1 rejected the call
    print(f"level       = {wire_verdict.level!r}")
    print(f"reason      = {wire_verdict.reason!r}")  # developer-facing text
    print(f"reason_code = {wire_verdict.reason_code!r}")  # None — taxonomy is Chapter 2's job


asyncio.run(main())

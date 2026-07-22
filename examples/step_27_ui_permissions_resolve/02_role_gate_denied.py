"""
02_role_gate_denied.py — an honest "no", with a reason for developers only

Same action as 01_role_gate_allowed.py, different caller: a plain user, not a
manager. The role check rejects the call, and this time the result is a
FailSecurityVerdict, not an AllowedVerdict — a denial through the role-gate
channel.

reason carries developer-facing text, not something to show the end user
as-is. No role matched at all here (a bare @check_roles(ManagerRole), no
when=), so reason is the fixed "FORBIDDEN_ROLE" — not declared by the
developer. Compare with 05_guest_gated_by_event.py, where a grant(when=...,
reason=...) rejects for a developer-declared reason instead.

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

    print(f"kind   = {verdict.kind!r}")
    print(f"reason = {verdict.reason!r}")  # "FORBIDDEN_ROLE" — no role matched, not developer-declared


asyncio.run(main())

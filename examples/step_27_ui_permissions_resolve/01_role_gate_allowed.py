"""
01_role_gate_allowed.py — the happy path: a manager can cancel an order

machine.check_access_decide answers "can this user do X?" without executing
the action — the same role -> guard -> access_decide cascade that machine.run
enforces, just without running any aspect. The AccessVerdict it returns *is*
a ResolveItemResult (a subclass adding one internal-only field, `action`,
never serialized, plus a derived diagnostic field, `action_name`) — the same
flat {kind, reason} (+ action_name) shape that POST /permissions/resolve
actually returns over HTTP, no conversion step.

Watch kind/reason here: a SUCCESS result always carries reason="" — there is
nothing more to say when nothing rejected the call. Compare with
02_role_gate_denied.py, where kind=SECURITY and reason is a real string.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/01_role_gate_allowed.py
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
    manager = Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))

    verdict = await machine.check_access_decide(manager, CancelOrderAction, OrderParams(order_id=7))

    print(f"kind   = {verdict.kind!r}")
    print(f"reason = {verdict.reason!r}")  # "" — SUCCESS never has more to say


asyncio.run(main())

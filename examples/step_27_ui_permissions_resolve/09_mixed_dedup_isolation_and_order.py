"""
09_mixed_dedup_isolation_and_order.py — dedup, per-item isolation and order together

A realistic batch mixes all three mechanics at once: some items repeat an
earlier question, one item names an action the server does not recognize, and
the rest are genuinely different questions. None of the three mechanics gets
in the other's way — the response is still the same length and order as the
request, duplicates still copy their first occurrence's verdict, and the
unknown item still only affects its own position.

Six items: position 0 and position 4 repeat the same question (the book's own
"position 1 / position 5" example, chapter 2), position 2 is unknown, the rest
are distinct.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/09_mixed_dedup_isolation_and_order.py
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
from aoa.fastapi.permissions import resolve_verdicts
from aoa.fastapi.permissions_schema import ResolveItem


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
    action_index = {"CancelOrderAction": CancelOrderAction}

    items = [
        ResolveItem(operation="CancelOrderAction", params={"order_id": 1}),  # 0: AAA
        ResolveItem(operation="CancelOrderAction", params={"order_id": 2}),  # 1: BBB
        ResolveItem(operation="RenamedOrDeletedAction", params={}),  # 2: unknown
        ResolveItem(operation="CancelOrderAction", params={"order_id": 3}),  # 3: CCC
        ResolveItem(operation="CancelOrderAction", params={"order_id": 1}),  # 4: AAA again
    ]

    outcome = await resolve_verdicts(manager, items, action_index, machine)

    print(f"items sent      = {len(items)}")
    print(f"verdicts back   = {len(outcome.verdicts)}")  # still 5
    print(f"real_call_count = {outcome.real_call_count}")  # 3 distinct keys: AAA, BBB, CCC
    print(f"position 0 == position 4 (both AAA) = {outcome.verdicts[0] == outcome.verdicts[4]}")
    print(f"position 2 (unknown) reason_code    = {outcome.verdicts[2].reason_code!r}")


asyncio.run(main())

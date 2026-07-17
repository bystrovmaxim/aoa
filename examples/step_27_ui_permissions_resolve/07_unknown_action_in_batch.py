"""
07_unknown_action_in_batch.py — an unknown operation fails its own item, not the batch

Before this chapter, an operation name the server did not recognize (a typo, a
stale frontend build asking about an action that got renamed) would fail the
whole POST /permissions/resolve request. resolve_verdicts() now isolates that
one item instead: it gets reason_code="UNKNOWN_ACTION" at its own position, and
every other item in the same batch still gets its normal, honest verdict.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/07_unknown_action_in_batch.py
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
    # "RenamedOrDeletedAction" is not in the index — a stale frontend build, say.
    action_index = {"CancelOrderAction": CancelOrderAction}

    items = [
        ResolveItem(operation="CancelOrderAction", params={"order_id": 1}),
        ResolveItem(operation="RenamedOrDeletedAction", params={}),
        ResolveItem(operation="CancelOrderAction", params={"order_id": 2}),
    ]

    outcome = await resolve_verdicts(manager, items, action_index, machine)

    for position, verdict in enumerate(outcome.verdicts):
        print(f"position {position}: allowed={verdict.allowed} reason_code={verdict.reason_code!r}")
    print(f"real_call_count = {outcome.real_call_count}")  # 2 — the unknown item never reaches access_decide


asyncio.run(main())

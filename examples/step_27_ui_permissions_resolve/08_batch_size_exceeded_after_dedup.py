"""
08_batch_size_exceeded_after_dedup.py — the size cap counts distinct keys, not raw items

max_check_access_decide_batch_size (ActionProductMachine's constructor argument)
caps how many DISTINCT (operation, params) keys one POST /permissions/resolve
batch may ask for — not the raw number of items sent. A batch that repeats the
same question many times costs one real call no matter how many times it is
repeated, so it must not be rejected just because it is long on paper.

This example proves both halves: the same cap of 1 rejects two genuinely
different questions (CheckAccessDecideBatchSizeExceededError, HTTP 413 at the
adapter layer), but lets two copies of the very same question through, because
after deduplication there is only one distinct key to check.

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/08_batch_size_exceeded_after_dedup.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.check_access_decide_batch_size_exceeded_error import (
    CheckAccessDecideBatchSizeExceededError,
)
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
    manager = Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))
    action_index = {"CancelOrderAction": CancelOrderAction}
    machine = ActionProductMachine(max_check_access_decide_batch_size=1)

    two_different_questions = [
        ResolveItem(operation="CancelOrderAction", params={"order_id": 1}),
        ResolveItem(operation="CancelOrderAction", params={"order_id": 2}),
    ]
    try:
        await resolve_verdicts(manager, two_different_questions, action_index, machine)
    except CheckAccessDecideBatchSizeExceededError as exc:
        print(f"two different questions, cap=1 -> rejected: {exc}")

    two_copies_of_one_question = [
        ResolveItem(operation="CancelOrderAction", params={"order_id": 7}),
        ResolveItem(operation="CancelOrderAction", params={"order_id": 7}),
    ]
    outcome = await resolve_verdicts(manager, two_copies_of_one_question, action_index, machine)
    print(f"two copies of one question, cap=1 -> accepted, real_call_count={outcome.real_call_count}")


asyncio.run(main())

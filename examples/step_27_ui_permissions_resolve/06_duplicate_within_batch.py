"""
06_duplicate_within_batch.py — two identical questions in one batch cost one real call

resolve_verdicts() (aoa-fastapi-adapter, aoa.fastapi.permissions) deduplicates a
POST /permissions/resolve batch before calling machine.check_access_decide: items
sharing the same (operation, params) key are grouped, and only the first
occurrence of a key triggers a real call — every later occurrence of the same
key just copies that same verdict onto its own position.

The response never shrinks: two items in, two verdicts out, in the same order.
What shrinks is the number of real calls to access_decide (the field
ResolveOutcome.real_call_count reports it) — the wire protocol never exposes
which positions were "real" and which were "copied"; the client sees two
independent-looking answers either way (chapter 2, "Кто на чём стоит").

Tutorial: ../../docs/tutorials/step-27-ui-permissions-resolve_draft.md

Run:
    uv run python examples/step_27_ui_permissions_resolve/06_duplicate_within_batch.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.auth.auth_coordinator import NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.fastapi.execution_plan import PreparedEndpointContext, build_execution_plan_index
from aoa.fastapi.permissions import build_route_index, resolve_verdicts
from aoa.fastapi.permissions_schema import ResolveItem
from aoa.fastapi.route_record import FastApiRouteRecord


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

    route_index = build_route_index(
        [FastApiRouteRecord(action_class=CancelOrderAction, method="post", path="/actions/cancel-order")]
    )
    plan_index = build_execution_plan_index(route_index, lambda record: NoAuthCoordinator(context=manager))
    prepared_by_operation = {
        operation: PreparedEndpointContext(context=manager, connections=None) for operation in route_index
    }

    items = [
        ResolveItem(operation="POST /actions/cancel-order", params={"order_id": 7}),
        ResolveItem(operation="POST /actions/cancel-order", params={"order_id": 7}),  # exact duplicate
    ]

    outcome = await resolve_verdicts(items, plan_index, prepared_by_operation, machine)

    print(f"items sent       = {len(items)}")
    print(f"results back     = {len(outcome.results)}")  # still 2 — the response never shrinks
    print(f"real_call_count  = {outcome.real_call_count}")  # 1 — the duplicate was never re-checked
    print(f"results[0] == results[1] = {outcome.results[0] == outcome.results[1]}")


asyncio.run(main())

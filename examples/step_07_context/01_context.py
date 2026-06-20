"""
01_context.py — Context as a declared slice (@context_requires)

A call carries an environment: who invokes it, request trace, source. An aspect
must not read it freely — that would couple business logic to transport. Instead
an aspect declares exactly the context fields it needs with @context_requires,
and receives a ContextView (parameter `ctx`) that exposes only those fields.

Reading a field that was NOT declared raises ContextAccessError — even when the
field is present in the context. The aspect never sees the full Context.

Tutorial: ../../docs/index_draft.md  ·  topic: Context

Run:
    uv run python examples/step_07_context/01_context.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context, Ctx
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.context_access_error import ContextAccessError
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class AuditDomain(BaseDomain):
    name = "audit"
    description = "Audit domain"


class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    status: str = Field(description="Execution status")


@meta(description="Place an order with an audit step", domain=AuditDomain)
@check_roles(GuestRole)
class PlaceOrderAction(BaseAction[OrderParams, OrderResult]):

    # The aspect declares the two context fields it needs. The machine injects a
    # ContextView as the 6th parameter `ctx`, restricted to exactly these keys.
    @regular_aspect("Audit who placed the order and from which trace")
    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        trace_id = ctx.get(Ctx.Request.trace_id)
        await box.info(
            Channel.business,
            "audit: order={%var.order} user={%var.user} trace={%var.trace}",
            order=params.order_id, user=user_id, trace=trace_id,
        )

        # client_ip IS present in the context below, but this aspect did not
        # declare it — reading it is refused.
        try:
            ctx.get(Ctx.Request.client_ip)
        except ContextAccessError:
            await box.info(Channel.business, "  client_ip not declared -> access refused")
        return {}

    @summary_aspect("Confirm the order")
    async def confirm_summary(self, params, state, box, connections):
        return OrderResult(order_id=params.order_id, status="placed")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    # The same aspect runs identically whether this context came from HTTP, MCP,
    # CLI, or a test — it only ever reads the fields it declared.
    ctx = Context(
        user=UserInfo(user_id="u-42"),
        request=RequestInfo(trace_id="trace-abc", client_ip="10.0.0.7"),
    )
    result = await machine.run(ctx, PlaceOrderAction(), OrderParams(order_id="ord-001"))
    print(f"\nResult: order_id={result.order_id}, status={result.status}")


asyncio.run(main())

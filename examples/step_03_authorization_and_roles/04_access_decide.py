"""A manager may cancel only their own order."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

# %% Setup


class StoreDomain(BaseDomain):
    """Group the order operations."""

    name = "store"
    description = "Order management"


class ManagerRole(ApplicationRole):
    """Permit order management."""

    name = "manager"
    description = "Can manage orders"


class OrderParams(BaseParams):
    """Identify the order to cancel."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the cancelled order."""

    order_id: str = Field(description="Cancelled order identifier")


OWNERS = {"ord-001": "m-1", "ord-002": "m-2"}


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Allow cancellation of the caller's own order")
    @context_requires("user.user_id")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        ctx: ContextView,
    ) -> Verdict:
        """Decide access before cancelling the order."""
        if OWNERS.get(params.order_id) != ctx.get("user.user_id"):
            return FORBIDDEN_OBJECT
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A manager may cancel only their own order."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    result = await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    print("own order:", result.model_dump())
    for order_id in ("ord-002", "missing"):
        try:
            await machine.run(caller, CancelOrderAction(), OrderParams(order_id=order_id))
        except AccessDenied as exc:
            print(order_id + ":", exc.verdict.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

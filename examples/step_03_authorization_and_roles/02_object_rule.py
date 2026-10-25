"""A condition on one role becomes a branch of the object rule."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.context_view import ContextView
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
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


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse a manager whose account is not in the EU team")
    @context_requires("user.user_id")
    async def cancel_order_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: Connections,
        ctx: ContextView,
    ) -> Verdict:
        """The role admits any manager; only the EU team passes the object rule."""
        if ctx.get("user.user_id").startswith("eu-"):
            return Allowed()
        return Refused("EU_TEAM_ONLY")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A condition on one role becomes a branch of the object rule."""
    machine = ActionProductMachine(cache_coordinator=None)
    eu = Context(user=UserInfo(user_id="eu-m1", roles=(ManagerRole,)))
    us = Context(user=UserInfo(user_id="us-m1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(eu, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("EU manager:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(us, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("US manager:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

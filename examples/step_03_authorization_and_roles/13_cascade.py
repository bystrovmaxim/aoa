"""A refusal stops the remaining checks."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
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


TRACE = []


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse every cancellation while the service is paused")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """Refuse, recording that the object step was reached."""
        TRACE.append("object")
        return Refused("CANCELLATIONS_PAUSED")

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections) -> OrderResult:
        """Return the cancellation result."""
        TRACE.append("summary")
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A refusal stops the remaining checks."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    stranger = Context(user=UserInfo(user_id="x-1", roles=()))

    TRACE.clear()
    try:
        await machine.run(manager, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        print("manager refused at:", exc.verdict.gate.value)
    print("manager called:", TRACE)

    TRACE.clear()
    try:
        await machine.run(stranger, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        print("stranger refused at:", exc.verdict.gate.value)
    print("stranger called:", TRACE)


if __name__ == "__main__":
    asyncio.run(main())

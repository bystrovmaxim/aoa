"""A refusal stops the remaining checks."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions import AccessDenied
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
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


TRACE = []


def in_team(user):
    """Record the role condition being evaluated."""
    TRACE.append("when")
    return True


def cancellations_open(user, params):
    """Record the shared condition refusing."""
    TRACE.append("guard")
    return False


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(
    grant(ManagerRole, when=in_team, reason="TEAM_REQUIRED"),
    guard=cancellations_open,
    guard_reason="CANCELLATIONS_PAUSED",
)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Check whether the order can be cancelled")
    async def cancel_access_decide(
        self,
        params: OrderParams,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Decide access before cancelling the order."""
        TRACE.append("object")
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        TRACE.append("summary")
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A refusal stops the remaining checks."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    try:
        await machine.run(caller, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        print("refused at:", exc.verdict.gate.value)
    print("called:", TRACE)


if __name__ == "__main__":
    asyncio.run(main())

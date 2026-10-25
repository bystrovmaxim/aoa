"""A shared condition becomes the object rule itself.
Run: .venv/bin/python examples/step_03_authorization_and_roles/03_shared_object_rule.py
"""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Refused, Verdict
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


class CancellationParams(OrderParams):
    """Add the requested cancellation amount."""

    amount: int = Field(description="Requested amount")


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[CancellationParams, OrderResult]):
    """Cancel an order after checking access."""

    @access_decide("Refuse a cancellation above the amount limit")
    async def cancel_order_access_decide(
        self,
        params: CancellationParams,
        box: ToolsBox,
        connections: Connections,
    ) -> Verdict:
        """The shared limit on every caller is now a branch of the object rule."""
        if params.amount <= 100:
            return Allowed()
        return Refused("AMOUNT_LIMIT")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: CancellationParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A shared condition becomes the object rule itself."""
    machine = ActionProductMachine(cache_coordinator=None)
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=50)
    )
    assert answer.model_dump(mode="json") == {"kind": "allowed"}
    print("amount 50:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(
        caller, CancelOrderAction, CancellationParams(order_id="ord-001", amount=150)
    )
    assert answer.model_dump(mode="json") == {"kind": "refused", "gate": "ACCESS_DECIDE", "reason": "AMOUNT_LIMIT"}
    print("amount 150:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

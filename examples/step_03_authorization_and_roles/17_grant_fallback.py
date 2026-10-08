"""A later grant may allow a caller."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

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


class AdminRole(ManagerRole):
    """Include manager permissions with an additional grant."""

    name = "admin"
    description = "Global administrator"


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(grant(ManagerRole, when=lambda user: user.user_id.startswith("eu-"), reason="EU_TEAM_ONLY"), AdminRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A later grant may allow a caller."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="us-m1", roles=(ManagerRole,)))
    admin = Context(user=UserInfo(user_id="us-a1", roles=(AdminRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(manager, CancelOrderAction, params)
    print("US manager:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(admin, CancelOrderAction, params)
    print("US admin:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

"""A silenced role grants no access."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.role_mode import RoleMode, role_mode
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


@role_mode(RoleMode.SILENCED)
class TemporaryManagerRole(ManagerRole):
    """Suspend temporary manager permissions."""

    name = "temporary_manager"
    description = "Temporary manager access"


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
class CancelOrderAction(BaseAction[OrderParams, OrderResult]):
    """Cancel an order after checking access."""

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A silenced role grants no access."""
    machine = ActionProductMachine(cache_coordinator=None)
    active = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    suspended = Context(user=UserInfo(user_id="t-1", roles=(TemporaryManagerRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(active, CancelOrderAction, params)
    print("active:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(suspended, CancelOrderAction, params)
    print("silenced:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

"""GuestRole and AnyRole express different requirements."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import AnyRole, ApplicationRole, GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
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
    """Identify the order to view."""

    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    """Report the requested order."""

    order_id: str = Field(description="Requested order identifier")


@meta(description="View an order", domain=StoreDomain)
@check_roles(GuestRole)
class PublicAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


@meta(description="View an order", domain=StoreDomain)
@check_roles(AnyRole)
class ProfileAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """GuestRole and AnyRole express different requirements."""
    machine = ActionProductMachine(cache_coordinator=None)
    anonymous = Context()
    member = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(anonymous, PublicAction, params)
    print("guest, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(anonymous, ProfileAction, params)
    print("any, anonymous:", answer.model_dump(mode="json"))
    answer = await machine.check_access_decide(member, ProfileAction, params)
    print("any, manager:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

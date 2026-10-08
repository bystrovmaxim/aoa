"""Either listed role is sufficient."""

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


class AuditorRole(ApplicationRole):
    """Permit reviewing order operations."""

    name = "auditor"
    description = "Can review orders"


@meta(description="View an order", domain=StoreDomain)
@check_roles([ManagerRole, AuditorRole])
class ViewOrderAction(BaseAction[OrderParams, OrderResult]):
    """View an order after checking access."""

    @summary_aspect("View the order")
    async def view_summary(self, params, state, box, connections):
        """Return the order identifier."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """Either listed role is sufficient."""
    machine = ActionProductMachine(cache_coordinator=None)
    manager = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    auditor = Context(user=UserInfo(user_id="a-1", roles=(AuditorRole,)))
    params = OrderParams(order_id="ord-001")

    answer = await machine.check_access_decide(manager, ViewOrderAction, params)
    print("manager:", answer.kind)
    answer = await machine.check_access_decide(auditor, ViewOrderAction, params)
    print("auditor:", answer.kind)
    answer = await machine.check_access_decide(Context(), ViewOrderAction, params)
    print("anonymous:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

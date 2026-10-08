"""A preliminary check publishes its own events."""

from __future__ import annotations

import asyncio

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on import on
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.core.events import AfterAccessDecideAspectEvent, BeforeAccessDecideAspectEvent
from aoa.action_machine.plugin.core.plugin import Plugin
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


@meta(description="Cancel an order", domain=StoreDomain)
@check_roles(ManagerRole)
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
        return Allowed()

    @summary_aspect("Cancel the order")
    async def cancel_summary(self, params, state, box, connections):
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


class AccessPrinter(Plugin):
    """Print the declared check's boundaries."""

    plugin_name = "access_printer"
    plugin_version = "1"

    async def get_initial_state(self):
        """Use no persistent plugin state."""
        return None

    @on(BeforeAccessDecideAspectEvent)
    async def on_before_check(self, state, event, log):
        """Report the check starting."""
        print("before:", event.aspect_name)

    @on(AfterAccessDecideAspectEvent)
    async def on_after_check(self, state, event, log):
        """Report the check finishing."""
        print("after:", event.aspect_name)


# %% Run


async def main() -> None:
    """A preliminary check publishes its own events."""
    machine = ActionProductMachine(cache_coordinator=None, plugins=[AccessPrinter()])
    caller = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))

    answer = await machine.check_access_decide(caller, CancelOrderAction, OrderParams(order_id="ord-001"))
    print("answer:", answer.model_dump(mode="json"))


if __name__ == "__main__":
    asyncio.run(main())

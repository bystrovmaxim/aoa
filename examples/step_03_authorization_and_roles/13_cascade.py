"""A refusal stops the remaining checks.
Run: .venv/bin/python examples/step_03_authorization_and_roles/13_cascade.py
"""

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
from aoa.action_machine.intents.on import on
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core.events import BeforeAccessDecideAspectEvent, BeforeSummaryAspectEvent
from aoa.action_machine.plugin.core.plugin import Plugin
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


class AccessTrace(Plugin):
    """Record reached steps without action globals."""

    plugin_name = "access_trace"
    plugin_version = "1"

    def __init__(self) -> None:
        """Start with an empty observation list."""
        self.called: list[str] = []

    async def get_initial_state(self):
        """Use no persistent plugin state."""
        return None

    @on(BeforeAccessDecideAspectEvent)
    async def on_object(self, state, event, log):
        """Record entry to the object rule."""
        self.called.append("object")

    @on(BeforeSummaryAspectEvent)
    async def on_summary(self, state, event, log):
        """Record entry to the summary."""
        self.called.append("summary")


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
        return Refused("CANCELLATIONS_PAUSED")

    @summary_aspect("Cancel the order")
    async def cancel_summary(
        self, params: OrderParams, state: BaseState, box: ToolsBox, connections: Connections
    ) -> OrderResult:
        """Return the cancellation result."""
        return OrderResult(order_id=params.order_id)


# %% Run


async def main() -> None:
    """A refusal stops the remaining checks."""
    trace = AccessTrace()
    machine = ActionProductMachine(cache_coordinator=None, plugins=[trace])
    manager = Context(user=UserInfo(user_id="m-1", roles=(ManagerRole,)))
    stranger = Context(user=UserInfo(user_id="x-1", roles=()))

    trace.called.clear()
    try:
        await machine.run(manager, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        assert exc.verdict.gate.value == "ACCESS_DECIDE"
        assert str(exc) == "Access denied by ACCESS_DECIDE: CANCELLATIONS_PAUSED"
        print("manager refused at:", exc.verdict.gate.value)
    else:
        raise AssertionError("The object rule must refuse.")
    assert trace.called == ["object"]
    print("manager called:", trace.called)

    trace.called.clear()
    try:
        await machine.run(stranger, CancelOrderAction(), OrderParams(order_id="ord-001"))
    except AccessDenied as exc:
        assert exc.verdict.gate.value == "CHECK_ROLES"
        assert str(exc) == "Access denied by CHECK_ROLES."
        print("stranger refused at:", exc.verdict.gate.value)
    else:
        raise AssertionError("The role requirement must refuse.")
    assert trace.called == []
    print("stranger called:", trace.called)


if __name__ == "__main__":
    asyncio.run(main())

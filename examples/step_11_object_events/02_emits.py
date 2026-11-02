"""
Scenario: @emits turns one method into a typed zone (mode 2).

Demonstrates:
  1. a listed event is delivered
  2. an event that is not listed is refused
  3. a line with kwargs is refused in that method
  4. a line with no variables is refused in that method
  5. another method of the action keeps its kwargs: the domain has no events

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/02_emits.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- Two facts, and an action with one typed method
class OrderCompletedEvent(BaseEvent):
    """An order was completed."""

    order_id: str


class CouponUsedEvent(BaseEvent):
    """A coupon was used. No method lists it."""


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"


class Params(BaseParams):
    case: str = Field(description="What the typed method writes")


class Result(BaseResult):
    done: bool = Field(description="The run finished")


@meta(description="Create an order", domain=StoreDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[Params, Result]):
    @regular_aspect("Check stock")
    async def check_stock_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        # no @emits here: this method writes as it always did
        await box.info(Channel.debug, "Stock checked: {%var.sku}", sku="pen")
        return {}

    @summary_aspect("Finalize the order")
    @emits(OrderCompletedEvent)
    async def finalize_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        if params.case == "listed":
            await box.info(Channel.business, "Order {%var.order_id} completed", OrderCompletedEvent(order_id="o1"))
        elif params.case == "not listed":
            await box.info(Channel.business, "Coupon used", CouponUsedEvent())
        elif params.case == "kwargs":
            await box.info(Channel.business, "Order {%var.order_id} completed", order_id="o1")
        elif params.case == "no variables":
            await box.info(Channel.business, "Order completed")
        return Result(done=True)


class ShowLogger(BaseLogger):
    """Prints each line and what var is."""

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        print(f"  {scope.aspect}: {message!r} ({type(var).__name__})")


# -- Run every case
async def main() -> None:
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[ShowLogger()]))
    for case in ("listed", "not listed", "kwargs", "no variables"):
        print(f"{case}:")
        try:
            await machine.run(Context(), CreateOrderAction(), Params(case=case))
        except Exception as error:
            print(f"  {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())

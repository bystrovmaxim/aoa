"""
Scenario: when to emit, and how to take a fact back.

Demonstrates:
  1. rule 1: a fact emitted in the summary aspect goes out only if every step succeeded
  2. rule 2: a published event is never withdrawn; a compensator emits a new fact
  3. an error handler reports what went wrong in the same way

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/05_rollback.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- The facts of an order
class StockReservedEvent(BaseEvent):
    """Stock was reserved for an order."""

    order_id: str


class OrderCompletedEvent(BaseEvent):
    """An order was completed."""

    order_id: str


class OrderCancelledEvent(BaseEvent):
    """A reservation was released, so the order is off."""

    order_id: str


class CheckoutFailedEvent(BaseEvent):
    """The card was declined."""

    order_id: str


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"
    events = (StockReservedEvent, OrderCompletedEvent, OrderCancelledEvent, CheckoutFailedEvent)


class Params(BaseParams):
    order_id: str = Field(description="The order")
    card_declined: bool = Field(default=False, description="Whether the later step fails")


class Result(BaseResult):
    outcome: str = Field(description="How the order ended")


class PaymentDeclinedError(Exception):
    """The card was declined."""


# -- The later step fails after the reserving step succeeded
@meta(description="Create an order", domain=StoreDomain)
@check_roles(GuestRole)
class CreateOrderAction(BaseAction[Params, Result]):
    @regular_aspect("Reserve stock")
    @emits(StockReservedEvent)
    async def reserve_stock_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        await box.info(
            Channel.business, "Stock reserved for {%var.order_id}", StockReservedEvent(order_id=params.order_id)
        )
        return {}

    @compensate(reserve_stock_aspect, "Release the reserved stock")
    @emits(OrderCancelledEvent)
    async def release_stock_compensate(
        self,
        params: Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        await box.info(
            Channel.business, "Order {%var.order_id} cancelled", OrderCancelledEvent(order_id=params.order_id)
        )

    @regular_aspect("Charge the card")
    async def charge_card_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        if params.card_declined:
            raise PaymentDeclinedError("card declined")
        return {}

    @summary_aspect("Finalize the order")
    @emits(OrderCompletedEvent)
    async def finalize_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        # every step that can fail is behind us: this is now true
        await box.info(
            Channel.business, "Order {%var.order_id} completed", OrderCompletedEvent(order_id=params.order_id)
        )
        return Result(outcome="completed")

    @on_error(PaymentDeclinedError, description="The card was declined")
    @emits(CheckoutFailedEvent)
    async def declined_on_error(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections, error: PaymentDeclinedError
    ) -> Result:
        await box.info(
            Channel.business, "Checkout failed for {%var.order_id}", CheckoutFailedEvent(order_id=params.order_id)
        )
        return Result(outcome="failed")


class ShowLogger(BaseLogger):
    """Prints the event of each line."""

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        print(f"  {type(var).__name__}: {message!r}")


# -- A good run, then a declined card
async def main() -> None:
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[ShowLogger()]))

    print("the card is accepted:")
    result = await machine.run(Context(), CreateOrderAction(), Params(order_id="o1"))
    print(f"  the run answered: {result.outcome}")

    print("the card is declined:")
    result = await machine.run(Context(), CreateOrderAction(), Params(order_id="o2", card_declined=True))
    print(f"  the run answered: {result.outcome}")


if __name__ == "__main__":
    asyncio.run(main())

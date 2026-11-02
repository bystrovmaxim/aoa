"""
Scenario: a log line whose variables are a typed fact.

Demonstrates:
  1. a line with an event: the text stays yours, and the logger receives the event
  2. a line with kwargs: the form that stays, and its var is a dictionary
  3. a line with no variables
  4. an event together with kwargs: refused in every mode
  5. a dump of an event holds the fact's own fields

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/01_event_line.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
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


# -- The fact, the action and a logger that shows what it receives
class OrderCompletedEvent(BaseEvent):
    """An order was completed."""

    order_id: str
    total: float


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"


class Params(BaseParams):
    case: str = Field(description="Which line to write")


class Result(BaseResult):
    done: bool = Field(description="The run finished")


@meta(description="Write one line", domain=StoreDomain)
@check_roles(GuestRole)
class WriteLineAction(BaseAction[Params, Result]):
    @summary_aspect("Write the line the case asks for")
    async def write_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        event = OrderCompletedEvent(order_id="o1", total=9.5)
        if params.case == "event":
            await box.info(Channel.business, "Order {%var.order_id} total {%var.total}", event)
        elif params.case == "kwargs":
            await box.info(Channel.business, "Order {%var.order_id} total {%var.total}", order_id="o1", total=9.5)
        elif params.case == "no variables":
            await box.info(Channel.business, "Order saved")
        elif params.case == "event and kwargs":
            await box.info(Channel.business, "Order {%var.order_id}", event, extra=1)
        return Result(done=True)


class ShowLogger(BaseLogger):
    """Prints the line, what var is, and the level it read by key."""

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        print(f"  line: {message!r}, var: {type(var).__name__}, level: {var['level'].name}")
        if isinstance(var, OrderCompletedEvent):
            print(f"  dump: {var.model_dump()}")


# -- Run every case
async def main() -> None:
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[ShowLogger()]))
    for case in ("event", "kwargs", "no variables", "event and kwargs"):
        print(f"{case}:")
        try:
            await machine.run(Context(), WriteLineAction(), Params(case=case))
        except Exception as error:
            print(f"  {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())

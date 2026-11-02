"""
Scenario: events in a domain types the whole domain (mode 3).

Demonstrates:
  1. a declared event from the vocabulary is delivered
  2. a line with no event is refused, with @emits and without it
  3. a method without @emits writes nothing, not even an event from the vocabulary
  4. events = () is a domain that emits nothing
  5. a nested action answers to its own domain
  6. @emits outside the vocabulary fails the build

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/03_domain_events.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.intents.aspects import summary_aspect
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


# -- Facts and domains
class OrderCompletedEvent(BaseEvent):
    """An order was completed."""

    order_id: str


class CouponUsedEvent(BaseEvent):
    """A coupon was used. No vocabulary here lists it."""


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"
    events = (OrderCompletedEvent,)


class ArchiveDomain(BaseDomain):
    name = "archive"
    description = "A domain that emits nothing"
    events = ()


class LegacyDomain(BaseDomain):
    name = "legacy"
    description = "A domain with no vocabulary"


class Params(BaseParams):
    case: str = Field(default="", description="What the method writes")


class Result(BaseResult):
    done: bool = Field(description="The run finished")


# -- One action for each row
async def write(box: ToolsBox, case: str) -> None:
    """Write what the case asks for."""
    if case == "event":
        await box.info(Channel.business, "Order {%var.order_id} completed", OrderCompletedEvent(order_id="o1"))
    elif case == "kwargs":
        await box.info(Channel.business, "Order {%var.order_id}", order_id="o1")
    elif case == "no variables":
        await box.info(Channel.business, "Order saved")


@meta(description="Write as an old action does", domain=LegacyDomain)
@check_roles(GuestRole)
class LegacyAction(BaseAction[Params, Result]):
    @summary_aspect("Write")
    async def write_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        await box.info(Channel.business, "Legacy line {%var.x}", x=1)
        return Result(done=True)


@meta(description="A method with @emits in a typed domain", domain=StoreDomain)
@check_roles(GuestRole)
class DeclaredAction(BaseAction[Params, Result]):
    @summary_aspect("Write")
    @emits(OrderCompletedEvent)
    async def write_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        await write(box, params.case)
        if params.case == "nested":
            await box.run(LegacyAction, Params())
        return Result(done=True)


@meta(description="A method without @emits in a typed domain", domain=StoreDomain)
@check_roles(GuestRole)
class UndeclaredAction(BaseAction[Params, Result]):
    @summary_aspect("Write")
    async def write_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        await write(box, params.case)
        return Result(done=True)


@meta(description="A method in a domain that emits nothing", domain=ArchiveDomain)
@check_roles(GuestRole)
class ArchiveAction(BaseAction[Params, Result]):
    @summary_aspect("Write")
    async def write_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        await write(box, params.case)
        return Result(done=True)


class ShowLogger(BaseLogger):
    """Prints each line."""

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        print(f"  delivered: {message!r} ({type(var).__name__})")


# -- Run every row, then break the build
async def main() -> None:
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[ShowLogger()]))
    rows: list[tuple[str, BaseAction[Any, Any], str]] = [
        ("@emits, a listed event", DeclaredAction(), "event"),
        ("@emits, kwargs", DeclaredAction(), "kwargs"),
        ("@emits, no variables", DeclaredAction(), "no variables"),
        ("no @emits, an event", UndeclaredAction(), "event"),
        ("no @emits, kwargs", UndeclaredAction(), "kwargs"),
        ("events = (), kwargs", ArchiveAction(), "kwargs"),
        ("a nested action from a domain with no events", DeclaredAction(), "nested"),
    ]
    for title, action, case in rows:
        print(f"{title}:")
        try:
            await machine.run(Context(), action, Params(case=case))
        except Exception as error:
            print(f"  {type(error).__name__}: {error}")

    @meta(description="Declares an event the domain does not allow", domain=StoreDomain)
    @check_roles(GuestRole)
    class OutsideAction(BaseAction[Params, Result]):
        @summary_aspect("Write")
        @emits(CouponUsedEvent)
        async def write_summary(
            self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
        ) -> Result:
            return Result(done=True)

    print("@emits outside the vocabulary, at build:")
    try:
        create_node_graph_coordinator()
    except Exception as error:
        print(f"  {type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())

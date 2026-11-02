"""
Scenario: everything refused before a line is written, and everything refused in a call.

Demonstrates:
  1. a name without the Event suffix
  2. a reserved field name
  3. an author setting a system field
  4. @emits with nothing, with a non-event, with BaseEvent, with a repeated event
  5. @emits written twice on one method
  6. invalid events on a domain
  7. a class, a dictionary and a bare BaseEvent in the event's place

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/06_refused_declarations.py
"""
import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- One fact, and a way to show each refusal
class OrderCompletedEvent(BaseEvent):
    """An order was completed."""

    order_id: str


def show(title: str, step: Callable[[], Any]) -> None:
    """Run ``step`` and print what refused it."""
    try:
        step()
        print(f"{title}: accepted")
    except Exception as error:
        print(f"{title}: {type(error).__name__}")


# -- Refused when a class is defined
def no_suffix() -> None:
    type("OrderCompleted", (BaseEvent,), {"__annotations__": {"order_id": str}})


def reserved_system_name() -> None:
    type("BadLevelEvent", (BaseEvent,), {"__annotations__": {"level": str}, "level": "high"})


def reserved_read_method() -> None:
    type("BadItemsEvent", (BaseEvent,), {"__annotations__": {"items": list}, "items": []})


def invalid_events(events: Any) -> Callable[[], None]:
    def define() -> None:
        type("BadDomain", (BaseDomain,), {"name": "bad", "description": "Bad", "events": events})

    return define


# -- Refused when @emits is applied
def twice() -> None:
    @emits(OrderCompletedEvent)
    @emits(OrderCompletedEvent)
    async def method() -> None:
        pass


# -- Refused in a call, with no switch on
async def call(value: Any) -> str:
    log = ScopedLogger(LogCoordinator(loggers=[]), 0, "ShopAction", "pay_aspect", Context())
    box = ToolsBox(run_child=MagicMock(), resources=None, log=log, nested_level=0, factory=MagicMock())
    try:
        await box.info(Channel.business, "text", value)
        return "accepted"
    except Exception as error:
        return type(error).__name__


async def main() -> None:
    show("a name without the suffix", no_suffix)
    show("a field named level", reserved_system_name)
    show("a field named items", reserved_read_method)
    show("an author setting level", lambda: OrderCompletedEvent(order_id="o1", level=None))
    show("@emits with nothing", emits)
    show("@emits with a non-event", lambda: emits(str))
    show("@emits with BaseEvent", lambda: emits(BaseEvent))
    show("@emits with a repeated event", lambda: emits(OrderCompletedEvent, OrderCompletedEvent))
    show("@emits written twice", twice)
    show("events as a list", invalid_events([OrderCompletedEvent]))
    show("events holding a non-event", invalid_events((str,)))
    show("events holding BaseEvent", invalid_events((BaseEvent,)))
    show("events repeating a class", invalid_events((OrderCompletedEvent, OrderCompletedEvent)))
    print(f"a class in the event's place: {await call(OrderCompletedEvent)}")
    print(f"a dictionary in the event's place: {await call({'order_id': 'o1'})}")
    print(f"a bare BaseEvent in the event's place: {await call(BaseEvent())}")


if __name__ == "__main__":
    asyncio.run(main())

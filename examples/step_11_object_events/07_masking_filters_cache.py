"""
Scenario: three things an event shares with any line, and one it does not.

Demonstrates:
  1. a @sensitive property of an event is masked, and a plain field is printed as it is
  2. a subscription filters an event like any line
  3. a result from the cache delivers no events

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/07_masking_filters_cache.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, sensitive
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_entry import CacheEntry
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- A fact with a card, and a cached action
class CardChargedEvent(BaseEvent):
    """A card was charged."""

    card: str

    @property
    @sensitive(True, max_chars=2, char="*", max_percent=100)
    def card_shown(self) -> str:
        return self.card


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"


class Params(BaseParams):
    pass


class Result(BaseResult):
    source: str = Field(description="Who answered")


@meta(description="Charge a card, cached", domain=StoreDomain)
@check_roles(GuestRole)
class ChargeAction(BaseAction[Params, Result]):
    def cache_key(self, params: Params) -> str | None:
        return "fixed"

    async def on_cache_write(self, result: Result, params: Params, duration_ms: float) -> list[CacheTag] | None:
        return [CacheTag(key="fixed")]

    async def read_cache(self, params: Params, entry: CacheEntry) -> Result | None:
        return Result(source="cache")

    @summary_aspect("Charge")
    @emits(CardChargedEvent)
    async def charge_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        event = CardChargedEvent(card="4111222233334444")
        await box.info(Channel.business, "masked {%var.card_shown}, plain {%var.card}", event)
        return Result(source="method")


class ShowLogger(BaseLogger):
    """Prints each line with its name."""

    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        print(f"  {self.label}: {message!r}")


# -- Two subscriptions, two calls
async def main() -> None:
    business = ShowLogger("subscribed to business").subscribe("rule", channels=Channel.business)
    debug = ShowLogger("subscribed to debug").subscribe("rule", channels=Channel.debug)
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[business, debug]), cache_coordinator=CacheCoordinator()
    )
    print("the first call:")
    print(f"  answered by: {(await machine.run(Context(), ChargeAction(), Params())).source}")
    print("the second call:")
    print(f"  answered by: {(await machine.run(Context(), ChargeAction(), Params())).source}")


if __name__ == "__main__":
    asyncio.run(main())

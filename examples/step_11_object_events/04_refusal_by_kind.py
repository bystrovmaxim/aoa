"""
Scenario: what a refused emission does in each kind of method.

Demonstrates:
  1. a regular aspect: the error reaches the caller
  2. a summary aspect: the same
  3. a compensator: it counts as failed, and the run goes on to the handler
  4. an error handler: OnErrorHandlerError
  5. @access_decide: Undecided from check_access_decide, AccessUndecided from a run

Tutorial: ../../docs/tutorials/step-11-object-events.md

Run:
    uv run python examples/step_11_object_events/04_refusal_by_kind.py
"""
import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.access_control import Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.emits import emits
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on_error import on_error
from aoa.action_machine.logging import Channel
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox


# -- An action whose every method declares one event and may break it
class OrderCompletedEvent(BaseEvent):
    """The only fact the action declares."""


class StoreDomain(BaseDomain):
    name = "store"
    description = "Storefront operations"


class Params(BaseParams):
    breaker: str = Field(default="", description="The kind of method that breaks its @emits")


class Result(BaseResult):
    outcome: str = Field(description="Who answered")


async def maybe_break(box: ToolsBox, params: Params, kind: str) -> None:
    """Write a line with no event, when this kind is the one that breaks the rule."""
    if params.breaker == kind:
        await box.info(Channel.business, "a line with no event")


@meta(description="All five kinds of method", domain=StoreDomain)
@check_roles(GuestRole)
class AllKindsAction(BaseAction[Params, Result]):
    @access_decide("Allow")
    @emits(OrderCompletedEvent)
    async def all_kinds_access_decide(self, params: Params, box: ToolsBox, connections: Connections) -> Verdict:
        await maybe_break(box, params, "access decision")
        return Allowed()

    @regular_aspect("First step")
    @emits(OrderCompletedEvent)
    async def first_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        await maybe_break(box, params, "regular aspect")
        return {}

    @compensate(first_aspect, "Undo the first step")
    @emits(OrderCompletedEvent)
    async def first_compensate(
        self,
        params: Params,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: Connections,
        error: Exception,
    ) -> None:
        await maybe_break(box, params, "compensator")

    @regular_aspect("Second step")
    async def second_aspect(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections
    ) -> dict[str, Any]:
        if params.breaker in ("compensator", "error handler"):
            raise ValueError("a later step failed")
        return {}

    @summary_aspect("Finish")
    @emits(OrderCompletedEvent)
    async def finish_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: Connections) -> Result:
        await maybe_break(box, params, "summary aspect")
        return Result(outcome="summary")

    @on_error(ValueError, description="Answer for the failed step")
    @emits(OrderCompletedEvent)
    async def failed_on_error(
        self, params: Params, state: BaseState, box: ToolsBox, connections: Connections, error: ValueError
    ) -> Result:
        await maybe_break(box, params, "error handler")
        return Result(outcome="handler")


# -- Break each kind in turn
async def main() -> None:
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[]))
    for kind in ("regular aspect", "summary aspect", "compensator", "error handler", "access decision"):
        print(f"{kind}:")
        try:
            result = await machine.run(Context(), AllKindsAction(), Params(breaker=kind))
            print(f"  the run answered: {result.outcome}")
        except Exception as error:
            print(f"  {type(error).__name__}")

    verdict = await machine.check_access_decide(Context(), AllKindsAction, Params(breaker="access decision"))
    print(f"check_access_decide: {type(verdict).__name__}")


if __name__ == "__main__":
    asyncio.run(main())

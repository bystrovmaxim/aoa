"""
# 04_inheritance.py — Inheritance: aspects are not inherited

In AOA the Action pipeline must be readable from the class itself — without
diving into the parent chain. This is the explicit declaration principle.

Therefore, aspects (@regular_aspect, @summary_aspect) declared in a parent class
do NOT automatically enter the child's pipeline. If the child declares its own
@summary_aspect, the machine builds the pipeline only from the aspects explicitly
declared in it — parent steps are invisible.

If the parent aspect's logic is still needed — declare the aspect explicitly in
the right position and call super().

Three Actions in this example:
  1. BaseOrderAction     — parent: validate_aspect → base_summary
  2. ChildOrderAction    — child with its own summary; validate_aspect does NOT run
  3. ExtendedOrderAction — the right way: explicit declaration + super()

Self-study experiment:
  1. Run the example, verify: the ChildOrderAction output has no "validate" step.
  2. Add your own validate_aspect to ChildOrderAction with @regular_aspect (no super()).
  3. Now it will run — because it is explicitly declared.

What's new (in addition to examples 01–03):
  - Inheriting BaseAction
  - Aspect behavior under inheritance
  - The correct reuse pattern via super()
  - result_instance — checker for objects and collections (here for list)

Run:
    uv run python examples/step_01_Action_and_pipeline/04_inheritance.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_instance
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class OrderDomain(BaseDomain):
    name = "order"
    description = "Order domain"


# ---------------------------------------------------------------------------
# Params and Result
# ---------------------------------------------------------------------------

class OrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class OrderResult(BaseResult):
    order_id: str = Field(description="Processed order identifier")
    steps: list[str] = Field(description="Names of the steps that actually executed")


# ---------------------------------------------------------------------------
# 1. Base Action
#
# Two aspects: validate_aspect → base_summary.
# When run directly, both execute in this order.
# ---------------------------------------------------------------------------

@meta(description="Base order operation", domain=OrderDomain)
@check_roles(NoneRole)
class BaseOrderAction(BaseAction[OrderParams, OrderResult]):

    @regular_aspect("Validate order identifier")
    @result_instance("steps", list, required=True)
    async def validate_aspect(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[BaseOrderAction.validate_aspect] order_id={%var.oid|cyan}",
            oid=params.order_id,
        )
        return {"steps": ["validate"]}

    @summary_aspect("Assemble base result")
    async def base_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[BaseOrderAction.base_summary] done",
        )
        return OrderResult(
            order_id=params.order_id,
            steps=state.get("steps", []),
        )


# ---------------------------------------------------------------------------
# 2. Child — parent aspects are NOT inherited
#
# ChildOrderAction inherits BaseOrderAction but declares its own @summary_aspect.
# Result: the machine sees only child_summary.
# validate_aspect and base_summary from the parent will NOT enter the pipeline.
#
# The output will NOT contain "[BaseOrderAction.validate_aspect] ..."
# The steps list will contain only ["child_only"]
# ---------------------------------------------------------------------------

@meta(description="Child operation — parent aspects do not run", domain=OrderDomain)
@check_roles(NoneRole)
class ChildOrderAction(BaseOrderAction):

    @summary_aspect("Child result — only this aspect will execute")
    async def child_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[ChildOrderAction.child_summary] order_id={%var.oid|yellow}",
            oid=params.order_id,
        )
        return OrderResult(
            order_id=params.order_id,
            steps=["child_only"],
        )


# ---------------------------------------------------------------------------
# 3. Extended child — the right way to reuse logic
#
# If you need the parent aspect's logic:
#   1. Declare the aspect with the same name explicitly — now it enters the pipeline.
#   2. Call super() inside to execute the parent's logic.
#
# The position in the class body determines when the step runs.
# The position in the parent class doesn't matter.
#
# result_instance("steps", list, required=True):
#   - Like result_string, but for arbitrary types (here: list)
#   - Guarantees that state["steps"] exists and is an instance of list
# ---------------------------------------------------------------------------

@meta(description="Extended operation with explicit super() call", domain=OrderDomain)
@check_roles(NoneRole)
class ExtendedOrderAction(BaseOrderAction):

    @regular_aspect("Validate order identifier")   # explicitly declared — enters the pipeline
    @result_instance("steps", list, required=True)
    async def validate_aspect(self, params, state, box, connections):
        # Execute parent aspect logic
        result = await super().validate_aspect(params, state, box, connections)
        # Add our own step on top
        steps = [*result.get("steps", []), "extended_validate"]
        await box.info(
            Channel.business,
            "[ExtendedOrderAction.validate_aspect] steps: {%var.steps}",
            steps=steps,
        )
        return {"steps": steps}

    @summary_aspect("Assemble extended result")
    async def extended_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "[ExtendedOrderAction.extended_summary] done",
        )
        return OrderResult(
            order_id=params.order_id,
            steps=state.get("steps", []),
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_action(
    machine: ActionProductMachine,
    label: str,
    action: BaseAction,
    params: OrderParams,
) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")
    result = await machine.run(Context(), action, params)
    print(f"  → steps executed: {result.steps}")


async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    params = OrderParams(order_id="ord-001")

    await run_action(machine, "1. BaseOrderAction (direct parent run)", BaseOrderAction(), params)
    await run_action(machine, "2. ChildOrderAction (parent aspects are NOT inherited)", ChildOrderAction(), params)
    await run_action(machine, "3. ExtendedOrderAction (explicit declaration + super())", ExtendedOrderAction(), params)


asyncio.run(main())

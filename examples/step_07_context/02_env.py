"""
02_env.py — Declarative environment providers via @env

Configuration values and feature flags belong on Context — not in module-level
globals or scattered os.environ calls. @env registers lazy providers directly on
a Context subclass. Each provider is called once on first access (or re-called
when its TTL expires). The aspect reads env values exactly like user or request
fields: via @context_requires("env.<key>") and ctx.get(...).

Tutorial: ../../docs/tutorials/step-07-context_draft.md  ·  topic: @env

Run:
    uv run python examples/step_07_context/02_env.py
"""

import asyncio
import os

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context, env
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires.context_requires_decorator import context_requires
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# ---------------------------------------------------------------------------
# Application Context with @env providers
# ---------------------------------------------------------------------------

def _read_flag(name: str) -> bool:
    return os.environ.get(name, "false").lower() == "true"


@env("feature_flag", lambda: _read_flag("MY_FEATURE"), ttl=30)
@env("region", "eu-west-1")       # constant — auto-wrapped in lambda
@env("max_retries", 3)            # constant — auto-wrapped in lambda
class AppContext(Context):
    """Application context with declarative environment providers."""


# ---------------------------------------------------------------------------
# Domain, Params, Result
# ---------------------------------------------------------------------------

class ShippingDomain(BaseDomain):
    name = "shipping"
    description = "Shipping domain"


class ShipOrderParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class ShipOrderResult(BaseResult):
    order_id: str = Field(description="Order identifier")
    status: str = Field(description="Execution status")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Ship an order using regional configuration", domain=ShippingDomain)
@check_roles(GuestRole)
class ShipOrderAction(BaseAction[ShipOrderParams, ShipOrderResult]):

    # @context_requires("env.<key>") works identically to "user.*" or "request.*".
    # An undeclared "env.*" key raises ContextAccessError; an unregistered key
    # returns the default (None).
    @regular_aspect("Read shipping configuration from env")
    @context_requires("env.region", "env.max_retries", "env.feature_flag")
    async def config_aspect(self, params, state, box, connections, ctx):
        region = ctx.get("env.region")
        max_retries = ctx.get("env.max_retries")
        feature_flag = ctx.get("env.feature_flag")
        await box.info(
            Channel.business,
            "shipping config: region={%var.r}  max_retries={%var.n}  feature_flag={%var.f}",
            r=region, n=max_retries, f=feature_flag,
        )
        return {}

    @summary_aspect("Confirm shipment")
    async def ship_summary(self, params, state, box, connections):
        return ShipOrderResult(order_id=params.order_id, status="shipped")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    ctx = AppContext()  # carries @env providers
    result = await machine.run(ctx, ShipOrderAction(), ShipOrderParams(order_id="ord-007"))
    print(f"\nResult: order_id={result.order_id}  status={result.status}")


asyncio.run(main())

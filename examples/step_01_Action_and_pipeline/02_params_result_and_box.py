"""
# 02_params_result_and_box.py — Params, Result, and box.info

Typed input parameters and output result.
Logging via box.info() with variable substitution and color.

What's new (in addition to example 01):
  - BaseParams              — base class for typed input parameters
  - BaseResult              — base class for typed output result
  - Field(description=...)  — Pydantic field with a description
  - box.info(Channel, template, **kwargs) — structured aspect logger
  - Channel.business        — semantic tag: this is a business event
  - {%var.key}              — substitutes a kwargs value into the log template
  - {%var.key|cyan}         — same, but with ANSI color
  - LogCoordinator + ConsoleLogger — where box events are written

Why box.info and not print?
  - print writes a string to stdout: no context, no filtering, nothing.
  - box.info(...) — a structured event: carries channel, level, domain,
    aspect name, operation name. Can be filtered on any dimension,
    routed to multiple sinks, written to an OCEL log.
  - print — only in the outer runner for quick demos.
  - box — always inside aspects.

Run:
    uv run python examples/step_01_Action_and_pipeline/02_params_result_and_box.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


# ---------------------------------------------------------------------------
# Params and Result
#
# BaseParams — Pydantic model for operation input data.
# BaseResult — Pydantic model for operation output data.
#
# Each field is described via Field(description=...).
# The description is not a comment: it goes into OpenAPI, MCP schema, and Maxitor.
#
# Field access inside the aspect: params.name (typed, with autocomplete)
# ---------------------------------------------------------------------------

class GreetParams(BaseParams):
    name: str = Field(description="Name of the person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Assembled greeting message")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Greet a person by name", domain=GreetingDomain)
@check_roles(NoneRole)
class GreetPersonAction(BaseAction[GreetParams, GreetResult]):

    # -----------------------------------------------------------------------
    # @summary_aspect — the single exit point
    #
    # box.info(channel, template, **kwargs):
    #   - channel: Channel.business — this is a business event
    #   - template: string with {%var.key} placeholders
    #   - kwargs: substitution values (name=params.name makes {%var.name} available)
    #
    # {%var.name|cyan} — substitutes params.name and colors it cyan.
    # Available colors: red, green, yellow, blue, cyan, magenta, white, grey, orange
    # and their bright_ variants (bright_green, bright_cyan, etc.)
    # Background colors: bg_red, bg_green, etc.
    #
    # Without LogCoordinator, box.info events are simply ignored.
    # With ConsoleLogger (see main()) — printed to stdout with level-based colors.
    # -----------------------------------------------------------------------

    @summary_aspect("Build greeting and return result")
    async def greet_summary(self, params, state, box, connections):
        await box.info(
            Channel.business,
            "Greeting: Hello, {%var.name|cyan}!",
            name=params.name,
        )
        return GreetResult(message=f"Hello, {params.name}!")


# ---------------------------------------------------------------------------
# Runner
#
# LogCoordinator — bus for all logging events.
# ConsoleLogger — built-in sink, writes to stdout.
# Without LogCoordinator, box.info/warning/critical calls are no-ops.
#
# ConsoleLogger colors lines by level:
#   info     → white
#   warning  → yellow
#   critical → red
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    result = await machine.run(
        Context(),
        GreetPersonAction(),
        GreetParams(name="Alice"),
    )
    print(f"\nResult: {result.message}")


asyncio.run(main())

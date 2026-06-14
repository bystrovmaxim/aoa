"""
# 01_hello_world.py — Minimal Action

The simplest Action: a single @summary_aspect, stubs instead of params and result.

Goal: show a working structure with a minimum of new concepts.
Every line here is required — nothing extra, nothing optional.

What's new:
  - BaseDomain       — logical grouping of operations in the system
  - @meta            — required class decorator: description and domain
  - @check_roles     — required access declaration (NoneRole = open to everyone)
  - BaseAction[P, R] — base class for all operations
  - ParamsStub       — input data stub (no fields)
  - ResultStub       — result stub (no fields)
  - @summary_aspect  — the single exit point of an Action, returns Result
  - ActionProductMachine — the machine that runs the pipeline
  - Context()        — call context (user, metadata, etc.; empty here)

Run:
    uv run python examples/step_01_Action_and_pipeline/01_hello_world.py
"""

import asyncio

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, ParamsStub, ResultStub
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

# ---------------------------------------------------------------------------
# Step 1 — Declare the domain
#
# BaseDomain — a logical group for operations of one subject area.
# Every Action must belong to a domain via @meta(domain=...).
#
# NAMING RULE: the class name must end with "Domain".
# Try renaming to "Greeting" — you'll get NamingSuffixError immediately,
# before the application even starts.
# ---------------------------------------------------------------------------

class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


# ---------------------------------------------------------------------------
# Step 2 — Declare the Action
#
# BaseAction[ParamsStub, ResultStub]:
#   - ParamsStub means "the operation takes no input data"
#   - ResultStub means "the operation returns no fields in the result"
#
# Two required decorators (the machine refuses to run without them):
#   @meta(description=..., domain=...)  — what this operation is and where it lives
#   @check_roles(NoneRole)              — who can call it (NoneRole = everyone)
#
# NAMING RULE: the class name must end with "Action".
# Try writing "SayHello" — you'll get NamingSuffixError at class declaration.
# ---------------------------------------------------------------------------

@meta(description="Say hello to the world", domain=GreetingDomain)
@check_roles(NoneRole)
class SayHelloAction(BaseAction[ParamsStub, ResultStub]):

    # -----------------------------------------------------------------------
    # Step 3 — Declare the single aspect: @summary_aspect
    #
    # @summary_aspect — the final step of the pipeline.
    # Every Action must have exactly one such method — no more, no less.
    # It returns a typed Result. Here — an empty ResultStub.
    #
    # NAMING RULE: the method name must end with "_summary".
    # Try writing "output" — you'll get NamingSuffixError when the decorator is applied.
    #
    # DESCRIPTION RULE: the description string cannot be empty.
    # Try @summary_aspect("") — you'll get ValueError.
    #
    # Method parameters are always the same:
    #   self, params, state, box, connections
    # We don't need them in this example, but they cannot be removed.
    #
    # We use print here — the simplest way to produce output.
    # Starting from the next example we'll switch to box.info().
    # -----------------------------------------------------------------------

    @summary_aspect("Print greeting and return stub")
    async def output_summary(self, params, state, box, connections):
        print("Hello, world!")
        return ResultStub()


# ---------------------------------------------------------------------------
# Step 4 — Run
#
# ActionProductMachine — the central execution machine.
# Created once, reused for all calls.
#
# machine.run(context, action_instance, params) → typed Result
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine()
    await machine.run(Context(), SayHelloAction(), ParamsStub())


asyncio.run(main())

"""
# 03_multiple_aspects.py — Multiple aspects and execution order

Three pipeline steps: two @regular_aspect and one @summary_aspect.
Data is passed between them via state.

What's new (in addition to examples 01–02):
  - @regular_aspect("description") — intermediate pipeline step, returns dict
  - state                          — accumulator dict, passed from step to step
  - Execution order                — strictly top to bottom, in declaration order
  - @result_string("key", required=True) — contract: a string must appear in state

How state works:
  - Pipeline starts with empty state = {}
  - Each @regular_aspect returns a dict → that dict COMPLETELY REPLACES state
  - Keys from the previous step are NOT copied automatically — pass them explicitly
  - @summary_aspect reads state, but returns a typed Result, not a dict

Self-study experiment:
  1. Swap validate_aspect and enrich_aspect (just move the methods).
  2. Run again.
  3. Observe: enrich_aspect tries to read state["cleaned"], which doesn't exist yet → KeyError.
  This proves: declaration order = execution order.

Run:
    uv run python examples/step_01_Action_and_pipeline/03_multiple_aspects.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, ConsoleLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------

class ProcessingDomain(BaseDomain):
    name = "processing"
    description = "Input data processing domain"


# ---------------------------------------------------------------------------
# Params and Result
# ---------------------------------------------------------------------------

class ProcessParams(BaseParams):
    raw_input: str = Field(description="Raw input string")


class ProcessResult(BaseResult):
    cleaned: str = Field(description="Cleaned string (stripped and lowercased)")
    enriched: str = Field(description="Enriched version of the cleaned string")
    final: str = Field(description="Final human-readable result description")


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

@meta(description="Process input string through multiple steps", domain=ProcessingDomain)
@check_roles(NoneRole)
class ProcessInputAction(BaseAction[ProcessParams, ProcessResult]):

    # -----------------------------------------------------------------------
    # Step 1 — @regular_aspect
    #
    # @regular_aspect("description"):
    #   - Intermediate pipeline step
    #   - Method name MUST end with "_aspect"
    #   - Must be async def
    #   - Returns dict → becomes new state
    #
    # @result_string("cleaned", required=True):
    #   - After this aspect, state["cleaned"] must contain a string
    #   - If the key is missing or the type is wrong → error immediately, before Step 2
    #   - This is a contract: "what I promise to leave in state"
    #
    # state on entry: {}
    # state after return: {"cleaned": "..."}
    # -----------------------------------------------------------------------

    @regular_aspect("Step 1: Strip whitespace and lowercase")
    @result_string("cleaned", required=True)
    async def validate_aspect(self, params, state, box, connections):
        cleaned = params.raw_input.strip().lower()
        await box.info(
            Channel.business,
            "[Step 1] cleaned={%var.cleaned|green}",
            cleaned=cleaned,
        )
        return {"cleaned": cleaned}

    # -----------------------------------------------------------------------
    # Step 2 — @regular_aspect
    #
    # state on entry: {"cleaned": "..."}  (from Step 1)
    #
    # We read state["cleaned"] and add the "enriched" key.
    # We also explicitly forward "cleaned" — otherwise Step 3 won't see it.
    #
    # @result_string stacks: both keys must be present in the returned dict.
    #
    # state after return: {"cleaned": "...", "enriched": "..."}
    # -----------------------------------------------------------------------

    @regular_aspect("Step 2: Enrich data")
    @result_string("cleaned", required=True)
    @result_string("enriched", required=True)
    async def enrich_aspect(self, params, state, box, connections):
        enriched = f"enriched::{state['cleaned']}"
        await box.info(
            Channel.business,
            "[Step 2] enriched={%var.enriched|yellow}",
            enriched=enriched,
        )
        return {
            "cleaned": state["cleaned"],   # explicitly forwarded from Step 1
            "enriched": enriched,
        }

    # -----------------------------------------------------------------------
    # Step 3 — @summary_aspect
    #
    # state on entry: {"cleaned": "...", "enriched": "..."}  (from Step 2)
    #
    # @summary_aspect — the single exit point.
    # Does not return a dict — returns a typed Result.
    # Method name MUST end with "_summary".
    # -----------------------------------------------------------------------

    @summary_aspect("Step 3: Assemble final result")
    async def assemble_summary(self, params, state, box, connections):
        final = f"{state['cleaned']} → {state['enriched']}"
        await box.info(
            Channel.business,
            "[Step 3] final={%var.final|cyan}",
            final=final,
        )
        return ProcessResult(
            cleaned=state["cleaned"],
            enriched=state["enriched"],
            final=final,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    machine = ActionProductMachine(
        log_coordinator=LogCoordinator(loggers=[ConsoleLogger()]),
    )
    result = await machine.run(
        Context(),
        ProcessInputAction(),
        ProcessParams(raw_input="  Hello World  "),
    )
    print(f"\nResult:")
    print(f"  cleaned  = {result.cleaned!r}")
    print(f"  enriched = {result.enriched!r}")
    print(f"  final    = {result.final!r}")


asyncio.run(main())

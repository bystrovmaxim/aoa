"""
04_field_mapping.py — params_mapper and response_mapper

By default LangGraphController maps AgentState fields to Action Params by
name.  When the graph's state field names differ from the Action's Param
field names, use ``params_mapper`` and ``response_mapper``.

``params_mapper(state) → Params``
    Called instead of the automatic name-matching.  Receives the current
    AgentState; returns a Params instance for the Action.

``response_mapper(result) → dict``
    Called instead of ``result.model_dump()``.  Receives the Action's Result;
    returns a dict to merge into state.  Only the keys in the returned dict
    are written — other state fields are untouched.

This example uses a graph whose state fields use generic names
(``user_query``, ``ticket_class``) that differ from the Action's field names
(``note``, ``category``).

What's new (vs 03):
  - .node(Action, params_mapper=...)   — custom state→params conversion
  - .node(Action, response_mapper=...) — custom result→state conversion
  - Both mappers are optional and independent of each other

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/04_field_mapping.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.langgraph import LangGraphController

# ─── Domain ───────────────────────────────────────────────────────────────────


class SupportDomain(BaseDomain):
    name = "support"
    description = "Support ticket processing"


# ─── Params / Results — Action-side field names ───────────────────────────────
#
# These are the "native" names used by each Action.
# The graph state uses different names — mapping is defined in .node(...).


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket text to classify")  # ← "note" in Action


class ClassifyResult(BaseResult):
    category: str = Field(description="Ticket category: bug | feature | billing")  # ← "category"


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


# ─── Actions ──────────────────────────────────────────────────────────────────


@meta(description="Classify ticket by content", domain=SupportDomain)
@check_roles(GuestRole)
class ClassifyTicketAction(BaseAction[ClassifyParams, ClassifyResult]):
    @summary_aspect("Classify ticket")
    async def classify_summary(self, params, state, box, connections):
        text = params.note.lower()
        if "billing" in text or "invoice" in text or "payment" in text:
            cat = "billing"
        elif "crash" in text or "error" in text or "bug" in text:
            cat = "bug"
        else:
            cat = "feature"
        return ClassifyResult(category=cat)


@meta(description="Route ticket to engineering", domain=SupportDomain)
@check_roles(GuestRole)
class EngineeringAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to engineering")
    async def resolve_summary(self, params, state, box, connections):
        tag = params.category.upper()
        return ResolveResult(
            resolved=True,
            resolution_note=f"[{tag}] #{params.ticket_id} → engineering",
        )


@meta(description="Route ticket to billing team", domain=SupportDomain)
@check_roles(GuestRole)
class BillingAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to billing")
    async def resolve_summary(self, params, state, box, connections):
        return ResolveResult(
            resolved=True,
            resolution_note=f"[BILLING] #{params.ticket_id} → billing team",
        )


# ─── Host Action ──────────────────────────────────────────────────────────────


class ProcessParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    user_query: str = Field(description="Raw user input (maps to 'note' in the graph)")


class ProcessResult(BaseResult):
    ticket_class: str = Field(description="Ticket class (maps from 'category' in graph)")
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process ticket with field mapping", domain=SupportDomain)
@check_roles(GuestRole)
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run graph with field mapping")
    async def run_summary(self, params, state, box, connections):
        ctrl = (
            LangGraphController()
            # State fields: user_query and ticket_id as inputs, ticket_class as output
            .inp("ticket_id", str, "Ticket identifier")
            .inp("user_query", str, "Raw user query (state name differs from Action param)")
            .mid("ticket_class", str, "Ticket class: bug | feature | billing")
            .mid("resolved", bool, "Resolution flag")
            .mid("resolution_note", str, "Resolution note")
            .out("ticket_class")
            .out("resolved")
            .out("resolution_note")
            # params_mapper: state.user_query → ClassifyParams.note
            # response_mapper: ClassifyResult.category → state.ticket_class
            .node(
                ClassifyTicketAction,
                params_mapper=lambda s: ClassifyParams(
                    ticket_id=s.ticket_id,
                    note=s.user_query,  # rename: state.user_query → params.note
                ),
                response_mapper=lambda r: {"ticket_class": r.category},  # rename output
            )
            # EngineeringAction / BillingAction: params_mapper for ticket_class → category
            .node(
                EngineeringAction,
                params_mapper=lambda s: ResolveParams(
                    ticket_id=s.ticket_id,
                    category=s.ticket_class,  # rename: state.ticket_class → params.category
                ),
            )
            .node(
                BillingAction,
                params_mapper=lambda s: ResolveParams(
                    ticket_id=s.ticket_id,
                    category=s.ticket_class,
                ),
            )
            .start(ClassifyTicketAction)
            .route(
                ClassifyTicketAction,
                on=lambda s: s.ticket_class,
                paths={
                    "bug": EngineeringAction,
                    "feature": EngineeringAction,
                    "billing": BillingAction,
                },
            )
            .finish(EngineeringAction)
            .finish(BillingAction)
            .build()
        )
        result = await ctrl.ainvoke(
            {"ticket_id": params.ticket_id, "user_query": params.user_query},
            box,
        )
        return ProcessResult(
            ticket_class=result["ticket_class"],
            resolved=result["resolved"],
            resolution_note=result["resolution_note"],
        )


# ─── Main ─────────────────────────────────────────────────────────────────────


async def main() -> None:
    machine = ActionProductMachine()

    tickets = [
        ("T-1", "App crashes on login"),
        ("T-2", "Wrong invoice total"),
        ("T-3", "Add dark mode to the UI"),
    ]

    print("=== Field mapping: user_query → note, category → ticket_class ===")
    for ticket_id, user_query in tickets:
        result = await machine.run(
            Context(),
            ProcessTicketAction(),
            ProcessParams(ticket_id=ticket_id, user_query=user_query),
        )
        flag = "✓" if result.resolved else "✗"
        print(f"  {ticket_id}  [{result.ticket_class:8}]  {flag}  {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())

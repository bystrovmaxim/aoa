"""
03_function_node.py — Mixing plain async functions with Action nodes

LangGraph nodes can be plain async functions, not just Actions.  A function
node receives the current AgentState and returns a dict that LangGraph merges
back into state.  Use function nodes for lightweight transformations that
don't need the full Action pipeline (no auth, no resources, no aspects).

This example inserts an ``enrich_ticket`` function node before the
ClassifyTicketAction.  The function rewrites the note, then the Action
reads the updated state field.

What's new (vs 02):
  - .node(fn, name="enrich")   — register an async function as a named node
  - .edge("enrich", NextAction) — explicit sequential edge from function to Action
  - .start("enrich")           — start the graph at a function node by name
  - Function node signature: async def fn(state: Any) -> dict

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/03_function_node.py
"""

import asyncio
from typing import Any

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


# ─── Params / Results ─────────────────────────────────────────────────────────


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(default="", description="Ticket content")


class ClassifyResult(BaseResult):
    category: str = Field(description="Ticket category: bug | feature | billing")


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


# ─── Function node ────────────────────────────────────────────────────────────
#
# A plain async function node receives the current AgentState object.
# Fields are accessible as attributes: state.note, state.ticket_id, etc.
# The returned dict is merged into state by LangGraph; keys must be declared
# in the controller (inp or mid fields).


async def enrich_ticket(state: Any) -> dict:
    """Add a system prefix to the note before classification."""
    raw_note: str = getattr(state, "note", "")
    return {"note": f"[SYSTEM] {raw_note}"}


# ─── Actions ──────────────────────────────────────────────────────────────────


@meta(description="Classify ticket by content", domain=SupportDomain)
@check_roles(GuestRole)
class ClassifyTicketAction(BaseAction[ClassifyParams, ClassifyResult]):
    @summary_aspect("Classify ticket")
    async def classify_summary(self, params, state, box, connections):
        # params.note is the enriched note produced by the function node above
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
    note: str = Field(description="Ticket content")


class ProcessResult(BaseResult):
    category: str = Field(description="Ticket category")
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process ticket with pre-processing function node", domain=SupportDomain)
@check_roles(GuestRole)
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run graph with function pre-processing")
    async def run_summary(self, params, state, box, connections):
        ctrl = (
            LangGraphController()
            .inp("ticket_id", str, "Ticket identifier")
            .inp("note", str, "Ticket content (overwritten by enrich step)")
            .mid("category", str, "Ticket category: bug | feature | billing")
            .mid("resolved", bool, "Resolution flag")
            .mid("resolution_note", str, "Resolution note")
            .out("category")
            .out("resolved")
            .out("resolution_note")
            # Register the function node under the name "enrich"
            .node(enrich_ticket, name="enrich")
            .node(ClassifyTicketAction)
            .node(EngineeringAction)
            .node(BillingAction)
            # Graph flow: enrich → classify → route → engineering/billing
            .start("enrich")
            .edge("enrich", ClassifyTicketAction)
            .route(
                ClassifyTicketAction,
                on=lambda s: s.category,
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
            {"ticket_id": params.ticket_id, "note": params.note},
            box,
        )
        return ProcessResult(
            category=result["category"],
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

    print("=== Function node: enrich → classify → route ===")
    for ticket_id, note in tickets:
        result = await machine.run(
            Context(),
            ProcessTicketAction(),
            ProcessParams(ticket_id=ticket_id, note=note),
        )
        flag = "✓" if result.resolved else "✗"
        print(f"  {ticket_id}  [{result.category:8}]  {flag}  {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())

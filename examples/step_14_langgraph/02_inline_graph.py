"""
02_inline_graph.py — LangGraphController built inline per call

Build and run a LangGraphController directly inside a @summary_aspect.
No @connection, no module-level graph.  Useful for actions that own their
own graph and don't share it with other actions.

Compared to example 01, the graph is built inside the action.  .build()
validates topology eagerly; .ainvoke() compiles a fresh LangGraph on every
call.  Both builds and compiles are cheap, so inline usage is fine for most
cases.

What's new (vs 01):
  - Build the graph inside @summary_aspect instead of at module level
  - No @connection decorator needed — the action is self-contained
  - Shows the same topology but wired differently

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/02_inline_graph.py
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


# ─── Inner Actions (graph nodes) ──────────────────────────────────────────────


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


# ─── Host Action — builds and runs the graph inline ───────────────────────────
#
# The graph is built once (at first call or at module load if desired, but here
# we build it fresh inside @summary_aspect to show the inline pattern).
# .build() validates topology at call time; .ainvoke() compiles and runs.


class ProcessParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket content")


class ProcessResult(BaseResult):
    category: str = Field(description="Ticket category")
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process a support ticket (inline graph)", domain=SupportDomain)
@check_roles(GuestRole)
class InlineProcessAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run inline ticket graph")
    async def run_summary(self, params, state, box, connections):
        ctrl = (
            LangGraphController()
            .inp("ticket_id", str, "Ticket identifier")
            .inp("note", str, "Ticket content")
            .mid("category", str, "Ticket category: bug | feature | billing")
            .mid("resolved", bool, "Resolution flag")
            .mid("resolution_note", str, "Resolution note")
            .out("category")
            .out("resolved")
            .out("resolution_note")
            .node(ClassifyTicketAction)
            .node(EngineeringAction)
            .node(BillingAction)
            .start(ClassifyTicketAction)
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

    print("=== Inline graph: ticket routing ===")
    for ticket_id, note in tickets:
        result = await machine.run(
            Context(),
            InlineProcessAction(),
            ProcessParams(ticket_id=ticket_id, note=note),
        )
        flag = "✓" if result.resolved else "✗"
        print(f"  {ticket_id}  [{result.category:8}]  {flag}  {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())

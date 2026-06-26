"""
01_external_connection.py — LangGraphController as a @connection resource

Build a LangGraphController once at startup and inject it into any Action via
@connection.  The graph is validated eagerly at .build() time; the compiled graph
is recreated on every ainvoke() call with a fresh box so node functions are always
bound to the current request's resource pool.

What's new:
  - LangGraphController             — fluent builder: .inp/.mid/.out → .node → topology → .build()
  - @connection(LangGraphController) — supply the built controller per request
  - ctrl.ainvoke(data, box)          — run the graph; box carries the resource pool
  - .route(src, on=fn, paths={})     — content-based routing across Action nodes

Install:  pip install aoa-action-machine langgraph

Run:
    uv run python examples/step_14_langgraph/01_external_connection.py
"""

import asyncio

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
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


# ─── Graph — built once at startup ────────────────────────────────────────────
#
# .inp()  — required input fields supplied by the caller via ainvoke()
# .mid()  — intermediate fields produced/consumed by graph nodes
# .out()  — fields returned from ainvoke() (declared before .finish())
# .build() validates topology and data-contract statically; no box needed here.


ticket_graph: LangGraphController = (
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


# ─── Host Action ──────────────────────────────────────────────────────────────
#
# @connection(LangGraphController, key="graph") declares that this Action expects
# a LangGraphController to be supplied under the key "graph" at call time.
# The machine validates the connection at startup; the controller is injected
# into every @summary_aspect call as connections["graph"].


class ProcessParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket content")


class ProcessResult(BaseResult):
    category: str = Field(description="Ticket category")
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process a support ticket via the ticket graph", domain=SupportDomain)
@check_roles(GuestRole)
@connection(LangGraphController, key="graph", description="Ticket processing graph")
class ProcessTicketAction(BaseAction[ProcessParams, ProcessResult]):
    @summary_aspect("Run ticket graph")
    async def run_summary(self, params, state, box, connections):
        result = await connections["graph"].ainvoke(
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

    print("=== External connection: ticket routing ===")
    for ticket_id, note in tickets:
        result = await machine.run(
            Context(),
            ProcessTicketAction(),
            ProcessParams(ticket_id=ticket_id, note=note),
            connections={"graph": ticket_graph},
        )
        flag = "✓" if result.resolved else "✗"
        print(f"  {ticket_id}  [{result.category:8}]  {flag}  {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())

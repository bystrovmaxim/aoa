"""
02_langgraph.py — LangGraphController: AOA actions as the nodes of a LangGraph graph

LangGraph connects steps into a graph; AOA runs each step as an action, with
its roles, checks and connections. LangGraphController declares the graph's
fields (.inp/.mid/.out), registers action classes as nodes, wires them with
.start/.edge/.route/.finish, and validates topology and data contract at
.build(). An action then runs the graph with .ainvoke(data, box): each node goes
through the same machine as any other action.

Install:  pip install aoa-action-machine aoa-langgraph langgraph

Run:
    uv run python examples/extensions/02_langgraph.py
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
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.langgraph import LangGraphController


class SupportDomain(BaseDomain):
    name = "support"
    description = "Support ticket processing domain"


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket content")


class ClassifyResult(BaseResult):
    category: str = Field(description="bug | feature | billing")


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolution_note: str = Field(description="Resolution note")


@meta(description="Classify a support ticket by content", domain=SupportDomain)
@check_roles(GuestRole)
class ClassifyTicketAction(BaseAction[ClassifyParams, ClassifyResult]):
    @summary_aspect("Classify ticket")
    async def classify_summary(self, params: ClassifyParams, state: BaseState, box: ToolsBox, connections: Connections) -> ClassifyResult:
        text = params.note.lower()
        if "invoice" in text or "payment" in text:
            return ClassifyResult(category="billing")
        if "crash" in text or "error" in text:
            return ClassifyResult(category="bug")
        return ClassifyResult(category="feature")


@meta(description="Route ticket to engineering", domain=SupportDomain)
@check_roles(GuestRole)
class EngineeringAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to engineering")
    async def resolve_summary(self, params: ResolveParams, state: BaseState, box: ToolsBox, connections: Connections) -> ResolveResult:
        return ResolveResult(resolution_note=f"[{params.category.upper()}] #{params.ticket_id} → engineering")


@meta(description="Route ticket to billing", domain=SupportDomain)
@check_roles(GuestRole)
class BillingAction(BaseAction[ResolveParams, ResolveResult]):
    @summary_aspect("Assign to billing")
    async def resolve_summary(self, params: ResolveParams, state: BaseState, box: ToolsBox, connections: Connections) -> ResolveResult:
        return ResolveResult(resolution_note=f"[BILLING] #{params.ticket_id} → billing team")


ticket_graph = (
    LangGraphController()
    .inp("ticket_id", str, "Ticket identifier")
    .inp("note", str, "Ticket content")
    .mid("category", str, "Ticket category")
    .mid("resolution_note", str, "Resolution note")
    .out("category")
    .out("resolution_note")
    .node(ClassifyTicketAction)
    .node(EngineeringAction)
    .node(BillingAction)
    .start(ClassifyTicketAction)
    .route(
        ClassifyTicketAction,
        on=lambda s: s.category,
        paths={"bug": EngineeringAction, "feature": EngineeringAction, "billing": BillingAction},
    )
    .finish(EngineeringAction)
    .finish(BillingAction)
    .build()
)


class TicketParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket content")


class TicketResult(BaseResult):
    category: str = Field(description="Ticket category")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Process a support ticket through the graph", domain=SupportDomain)
@check_roles(GuestRole)
class ProcessTicketAction(BaseAction[TicketParams, TicketResult]):
    @summary_aspect("Run the ticket graph")
    async def run_summary(self, params: TicketParams, state: BaseState, box: ToolsBox, connections: Connections) -> TicketResult:
        result = await ticket_graph.ainvoke({"ticket_id": params.ticket_id, "note": params.note}, box)
        return TicketResult(category=result["category"], resolution_note=result["resolution_note"])


async def main() -> None:
    machine = ActionProductMachine()
    for ticket_id, note in [("T-1", "App crashes on login"), ("T-2", "Wrong invoice total"), ("T-3", "Add dark mode")]:
        result = await machine.run(Context(), ProcessTicketAction(), TicketParams(ticket_id=ticket_id, note=note))
        print(f"{ticket_id} [{result.category:8}] {result.resolution_note}")


if __name__ == "__main__":
    asyncio.run(main())

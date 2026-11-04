"""
01_langgraph.py — the mistakes LangGraphController catches, and when

A LangGraphController is declared, built and run. Each step catches its own
mistakes: a reference to a node that was never registered fails where it is
declared, a broken topology or data contract fails at .build(), and a routing
key the paths do not cover fails when the graph runs.

Install:  pip install aoa-action-machine aoa-langgraph langgraph

Run:
    uv run python examples/step_16_langgraph/01_langgraph.py
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
from aoa.langgraph import (
    FieldHasNoProducerError,
    LangGraphController,
    NoFinishPointError,
    RouteKeyError,
    UnregisteredNodeError,
)

# ─── Domain, params, results ──────────────────────────────────────────────────


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
    resolved: bool = Field(description="Resolution flag")
    resolution_note: str = Field(description="Resolution note")


# ─── Actions ──────────────────────────────────────────────────────────────────


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
        return ResolveResult(resolved=True, resolution_note=f"[{params.category.upper()}] #{params.ticket_id} → engineering")


def _fields(ctrl: LangGraphController) -> LangGraphController:
    """Declare the ticket fields every graph of this example shares."""
    return (
        ctrl.inp("ticket_id", str, "Ticket identifier")
        .inp("note", str, "Ticket content")
        .mid("category", str, "Ticket category")
        .mid("resolved", bool, "Resolution flag")
        .mid("resolution_note", str, "Resolution note")
    )


# ─── A graph whose routes cover bugs only ─────────────────────────────────────


bugs_only = (
    _fields(LangGraphController())
    .out("category")
    .out("resolution_note")
    .node(ClassifyTicketAction)
    .node(EngineeringAction)
    .start(ClassifyTicketAction)
    .route(ClassifyTicketAction, on=lambda s: s.category, paths={"bug": EngineeringAction})
    .finish(EngineeringAction)
    .build()
)


class TicketParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(description="Ticket content")


class TicketResult(BaseResult):
    category: str = Field(description="Ticket category")
    resolution_note: str = Field(description="Resolution note")


@meta(description="Run the bugs-only graph", domain=SupportDomain)
@check_roles(GuestRole)
class BugsOnlyAction(BaseAction[TicketParams, TicketResult]):
    @summary_aspect("Run the graph")
    async def run_summary(self, params: TicketParams, state: BaseState, box: ToolsBox, connections: Connections) -> TicketResult:
        result = await bugs_only.ainvoke({"ticket_id": params.ticket_id, "note": params.note}, box)
        return TicketResult(category=result["category"], resolution_note=result["resolution_note"])


async def main() -> None:
    # 1. A node referenced before it is registered fails where it is declared.
    print("1. Declaring an edge to an unregistered node")
    try:
        _fields(LangGraphController()).node(ClassifyTicketAction).edge(ClassifyTicketAction, EngineeringAction)
    except UnregisteredNodeError as exc:
        print(f"   UnregisteredNodeError: {exc}")

    # 2. A graph with no finish node fails at .build().
    print("2. Building a graph with no finish node")
    try:
        (
            _fields(LangGraphController())
            .out("category")
            .node(ClassifyTicketAction)
            .node(EngineeringAction)
            .start(ClassifyTicketAction)
            .edge(ClassifyTicketAction, EngineeringAction)
            .build()
        )
    except NoFinishPointError as exc:
        print(f"   NoFinishPointError: {exc}")

    # 3. A Params field that nothing produces fails at .build().
    print("3. Building a graph that starts where `category` is not yet known")
    try:
        (
            _fields(LangGraphController())
            .out("resolution_note")
            .node(EngineeringAction)
            .start(EngineeringAction)
            .finish(EngineeringAction)
            .build()
        )
    except FieldHasNoProducerError as exc:
        print(f"   FieldHasNoProducerError: {exc}")

    # 4. A routing key the paths do not cover fails when the graph runs.
    machine = ActionProductMachine()
    print("4. Running the bugs-only graph")
    bug = await machine.run(Context(), BugsOnlyAction(), TicketParams(ticket_id="T-1", note="App crashes on login"))
    print(f"   T-1 [{bug.category}] {bug.resolution_note}")
    try:
        await machine.run(Context(), BugsOnlyAction(), TicketParams(ticket_id="T-2", note="Wrong invoice total"))
    except RouteKeyError as exc:
        print(f"   T-2 RouteKeyError: {exc}")


if __name__ == "__main__":
    asyncio.run(main())

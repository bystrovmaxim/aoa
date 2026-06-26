"""
01_langgraph.py — AOA Actions as LangGraph nodes via LangGraphAdapter

LangGraph wires components into graphs; AOA wraps each step with roles,
connections, and context. LangGraphAdapter bridges the two: register Actions
with .node(), declare edges with .edge(), .conditional_edge(), or .route(),
then call .compile() — you get a standard LangGraph CompiledGraph with
ainvoke(), astream(), and get_graph().draw_mermaid().

Key properties:
- Topology errors are caught at build time: .edge() raises UnregisteredNodeError
  immediately if a node was never registered — no waiting for ainvoke().
- Connection pool is filtered per-Action by @connection keys — no manual plumbing.
- .build_graph() returns a raw StateGraph for native LangGraph continuation.

Extension: ../../docs/extensions/langgraph.md  ·  topic: LangGraphAdapter

Install:  pip install "aoa-langgraph" langgraph

Run:
    uv run python examples/step_14_langgraph/01_langgraph.py
"""

import asyncio

from langgraph.graph import END
from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.langgraph import AgentState, LangGraphAdapter, RouteKeyError, StateFieldMismatchError, UnregisteredNodeError

# ─── State ────────────────────────────────────────────────────────────────────
# TypedDict becomes the LangGraph state schema.
# Each Action node receives the full state; result.model_dump() is merged back in.


class TicketState(AgentState):
    ticket_id: str
    category: str = ""      # filled by ClassifyTicketAction
    resolved: bool = False
    note: str = ""


# ─── Domain ───────────────────────────────────────────────────────────────────


class SupportDomain(BaseDomain):
    name = "support"
    description = "Support ticket processing domain"


# ─── Params / Results ─────────────────────────────────────────────────────────


class ClassifyParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    note: str = Field(default="", description="Ticket description")


class ClassifyResult(BaseResult):
    category: str = Field(description="bug | feature | billing")


class ResolveParams(BaseParams):
    ticket_id: str = Field(description="Ticket identifier")
    category: str = Field(description="Ticket category")


class ResolveResult(BaseResult):
    resolved: bool = Field(description="Resolved flag")
    note: str = Field(description="Resolution note")


# ─── Actions ──────────────────────────────────────────────────────────────────
# Action.Params fields are extracted from the LangGraph state by name.
# Result fields are merged back into the state after the node returns.


@meta(description="Classify a support ticket by content", domain=SupportDomain)
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


@meta(description="Route ticket to engineering team", domain=SupportDomain)
@check_roles(GuestRole)
class EngineeringAction(BaseAction[ResolveParams, ResolveResult]):

    @summary_aspect("Assign to engineering")
    async def resolve_summary(self, params, state, box, connections):
        tag = params.category.upper()
        return ResolveResult(
            resolved=True,
            note=f"[{tag}] #{params.ticket_id} → engineering",
        )


@meta(description="Route ticket to billing team", domain=SupportDomain)
@check_roles(GuestRole)
class BillingAction(BaseAction[ResolveParams, ResolveResult]):

    @summary_aspect("Assign to billing")
    async def resolve_summary(self, params, state, box, connections):
        return ResolveResult(
            resolved=True,
            note=f"[BILLING] #{params.ticket_id} → billing team",
        )


# ─── Plain async function node ────────────────────────────────────────────────
# Plain async fns can be mixed in — they receive the full state dict directly.


async def close_ticket(state: TicketState) -> dict:
    return {"note": state["note"] + " [closed]"}


# ─── Graph assembly ───────────────────────────────────────────────────────────


async def main() -> None:
    machine = ActionProductMachine()
    context = Context()

    # --- Part 1: early error detection --- #
    #
    # .edge() validates that both endpoints are registered with .node().
    # A typo in a node name raises UnregisteredNodeError immediately —
    # long before ainvoke() is ever called.
    #
    try:
        (
            LangGraphAdapter(machine=machine, context=context, agentstate=TicketState)
            .node(ClassifyTicketAction())
            .edge(ClassifyTicketAction, "typo_node")  # "typo_node" not registered
        )
    except UnregisteredNodeError as exc:
        print(f"[UnregisteredNodeError] {exc}\n")

    # --- Part 2: multi-path routing with .route() --- #
    #
    # .route(source, on=fn, paths={key: target}) routes to a different node
    # based on a function that returns a key from the current state.
    # Targets can be Action classes, instances, or plain strings.
    #
    compiled = (
        LangGraphAdapter(machine=machine, context=context, agentstate=TicketState)
        .node(ClassifyTicketAction())
        .node(EngineeringAction())
        .node(BillingAction())
        .node(close_ticket, name="close_ticket")
        .start(ClassifyTicketAction)
        .route(
            ClassifyTicketAction,
            on=lambda s: s.get("category"),
            paths={
                "bug":     EngineeringAction,   # bugs and features both go
                "feature": EngineeringAction,   # to the engineering node
                "billing": BillingAction,
            },
        )
        .edge(EngineeringAction, "close_ticket")
        .edge(BillingAction,     "close_ticket")
        .edge("close_ticket",    END)
        .compile()
    )

    tickets = [
        TicketState(ticket_id="T-1", note="App crashes on startup"),
        TicketState(ticket_id="T-2", note="Wrong invoice amount"),
        TicketState(ticket_id="T-3", note="Add support for dark mode"),
        TicketState(ticket_id="T-4", note="Payment failed on checkout"),
    ]
    print("=== Ticket routing ===")
    for t in tickets:
        r = await compiled.ainvoke(t)
        print(f"  {r['ticket_id']}  [{r['category']:8}]  {r['note']}")

    # --- Part 3: RouteKeyError — ключ не найден в paths --- #
    #
    # .route(on=..., paths={...}) бросает RouteKeyError если on() вернул ключ,
    # которого нет в paths. Ошибка возникает в момент ainvoke() — не при сборке
    # графа — потому что значение on() зависит от состояния конкретного запуска.
    #
    # Здесь paths покрывает только "bug", а billing-тикет даёт category="billing".
    #
    print("\n=== RouteKeyError demo ===")
    incomplete_compiled = (
        LangGraphAdapter(machine=machine, context=context, agentstate=TicketState)
        .node(ClassifyTicketAction())
        .node(EngineeringAction())
        .start(ClassifyTicketAction)
        .route(
            ClassifyTicketAction,
            on=lambda s: s.get("category"),
            paths={"bug": EngineeringAction},   # "billing" и "feature" не покрыты!
        )
        .edge(EngineeringAction, END)
        .compile()
    )
    try:
        await incomplete_compiled.ainvoke(
            TicketState(ticket_id="ERR-1", note="Wrong invoice amount")  # → "billing"
        )
    except RouteKeyError as exc:
        print(f"[RouteKeyError] {exc}\n")

    # --- Part 4: StateFieldMismatchError — поле Result отсутствует в AgentState --- #
    #
    # .compile() проверяет, что каждое поле Result-типа каждого Action объявлено
    # в AgentState. Пропущенное поле молча исчезает при мёрдже — адаптер обнаруживает
    # это до первого запуска.
    #
    # EngineeringAction возвращает resolved=bool и note=str.
    # _IncompleteState объявляет только ticket_id и category — resolved и note забыты.
    #
    print("=== StateFieldMismatchError demo ===")

    class _IncompleteState(AgentState):
        ticket_id: str
        category: str = ""
        # resolved: bool и note: str не объявлены — EngineeringAction их вернёт!

    try:
        (
            LangGraphAdapter(machine=machine, context=context, agentstate=_IncompleteState)
            .node(ClassifyTicketAction())
            .node(EngineeringAction())
            .start(ClassifyTicketAction)
            .compile()   # ← StateFieldMismatchError здесь, до первого ainvoke()
        )
    except StateFieldMismatchError as exc:
        print(f"[StateFieldMismatchError] {exc}\n")

    # --- Part 5: native continuation via build_graph() --- #
    #
    # .build_graph() returns the StateGraph before .compile().
    # You can add more nodes or edges with the native LangGraph API,
    # then call .compile() yourself.
    #
    print("\n=== Native continuation ===")
    graph = (
        LangGraphAdapter(machine=machine, context=context, agentstate=TicketState)
        .node(ClassifyTicketAction())
        .start(ClassifyTicketAction)
        .build_graph()          # ← returns StateGraph, not CompiledGraph
    )
    graph.add_edge("classify_ticket", END)   # native LangGraph API
    native_compiled = graph.compile()
    r = await native_compiled.ainvoke(TicketState(ticket_id="T-5", note="billing question"))
    print(f"  T-5 classified as: {r['category']}")

    # --- Graph structure (Mermaid) --- #
    print("\n=== Graph (Mermaid) ===")
    print(compiled.get_graph().draw_mermaid())


if __name__ == "__main__":
    asyncio.run(main())

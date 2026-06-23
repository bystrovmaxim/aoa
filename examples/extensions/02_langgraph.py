"""
02_langgraph.py — LangGraphAdapter: AOA Actions as LangGraph nodes

LangGraph connects components into graphs; AOA wraps each step with metadata
(roles, checkers, connections, context). LangGraphAdapter bridges the two:
register actions with .node(), declare edges with .edge() or
.conditional_edge(), and call .compile() — you get a standard LangGraph
CompiledGraph with ainvoke(), astream(), and get_graph().draw_mermaid().

Key advantages of the adapter form:
- Nodes are typed Python objects, not strings — typos become immediate
  UnregisteredNodeError at graph build time, not silent runtime failures.
- Connection pool is filtered per Action by declared @connection keys — no
  manual plumbing.
- .build_graph() returns a raw StateGraph for native LangGraph continuation
  when you need low-level control.

Install:  pip install "aoa-langgraph-adapter"

Run:
    uv run python examples/extensions/02_langgraph.py
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
from aoa.langgraph import AgentState, LangGraphAdapter

# ─── State ────────────────────────────────────────────────────────────────────
# TypedDict becomes the LangGraph state schema.
# node_fn(agentstate) receives this dict; result.model_dump() is merged back in.


class OrderState(AgentState):
    order_id: str
    valid: bool = False
    status: str = ""


# LegacyState uses different field names than Action Params/Results.
# params_mapper and response_mapper bridge the gap.
class LegacyState(AgentState):
    ref: str           # Action expects "order_id"
    checked: bool = False  # Action returns "valid"


# ─── Domain ───────────────────────────────────────────────────────────────────


class OrderDomain(BaseDomain):
    name = "orders"
    description = "Order processing domain"


# ─── Params / Results ─────────────────────────────────────────────────────────


class ValidateParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class ValidateResult(BaseResult):
    valid: bool = Field(description="True if order_id has valid format")


class ConfirmParams(BaseParams):
    order_id: str = Field(description="Order identifier")


class ConfirmResult(BaseResult):
    status: str = Field(description="Confirmation token")


# ─── Actions ──────────────────────────────────────────────────────────────────
# Action.Params fields are extracted from the LangGraph state by name.
# Result fields are merged back into the state after the node returns.


@meta(description="Validate order format", domain=OrderDomain)
@check_roles(GuestRole)
class ValidateOrderAction(BaseAction[ValidateParams, ValidateResult]):
    @summary_aspect("Check order_id format")
    async def validate_summary(self, params, state, box, connections):
        return ValidateResult(valid=params.order_id.startswith("ORD-"))


@meta(description="Confirm a valid order", domain=OrderDomain)
@check_roles(GuestRole)
class ConfirmOrderAction(BaseAction[ConfirmParams, ConfirmResult]):
    @summary_aspect("Issue confirmation token")
    async def confirm_summary(self, params, state, box, connections):
        return ConfirmResult(status=f"confirmed:{params.order_id}")


# ─── Plain async function node ────────────────────────────────────────────────
# Plain async fns can be mixed in — they receive the full state dict.


async def reject_order(state: OrderState) -> dict:
    return {"status": f"rejected:{state['order_id']}"}


# ─── Graph assembly ───────────────────────────────────────────────────────────


async def main() -> None:
    machine = ActionProductMachine()
    context = Context()

    # --- Variant A: AOA adapter --- #
    #
    # .node() accepts Action instances or plain async functions (name= required).
    # .edge() / .conditional_edge() accept Action classes, instances, or strings.
    # Referencing an unregistered node raises UnregisteredNodeError immediately —
    # graph topology errors surface at build time, not at ainvoke() time.
    #
    compiled = (
        LangGraphAdapter(machine=machine, context=context, agentstate=OrderState)
        .node(ValidateOrderAction())
        .node(ConfirmOrderAction())
        .node(reject_order, name="reject_order")
        .start(ValidateOrderAction)
        .conditional_edge(
            ValidateOrderAction,
            when=lambda s: s.get("valid"),
            if_true=ConfirmOrderAction,
            if_false="reject_order",
        )
        .edge(ConfirmOrderAction, END)
        .edge("reject_order", END)
        .compile()  # → standard LangGraph CompiledGraph
    )

    print("=== Valid order ===")
    result = await compiled.ainvoke(OrderState(order_id="ORD-001"))
    print(f"  status={result['status']}  valid={result['valid']}")

    print("\n=== Invalid order ===")
    result = await compiled.ainvoke(OrderState(order_id="inv-002"))
    print(f"  status={result['status']}  valid={result['valid']}")

    # --- Variant B: native LangGraph continuation via build_graph() --- #
    #
    # build_graph() returns a StateGraph — add more nodes/edges, then compile.
    # Useful when you need low-level LangGraph control after the AOA portion.
    #
    print("\n=== Native continuation ===")
    graph = (
        LangGraphAdapter(machine=machine, context=context, agentstate=OrderState)
        .node(ValidateOrderAction())
        .start(ValidateOrderAction)
        .build_graph()  # → StateGraph (not yet compiled)
    )
    # Add the rest with the native LangGraph API:
    graph.add_edge("validate_order", END)
    native_compiled = graph.compile()
    result = await native_compiled.ainvoke(OrderState(order_id="ORD-003"))
    print(f"  valid={result['valid']}")

    # --- Variant C: params_mapper / response_mapper --- #
    #
    # When your LangGraph state field names differ from Action Params/Result field
    # names, pass mapper lambdas to .node():
    #
    #   params_mapper(agentstate) → Params instance   (replaces auto-extraction)
    #   response_mapper(result)   → dict | Pydantic   (replaces result.model_dump())
    #
    # Here LegacyState uses "ref"/"checked"; ValidateOrderAction uses "order_id"/"valid".
    #
    print("\n=== Mapper example ===")
    mapper_compiled = (
        LangGraphAdapter(machine=machine, context=context, agentstate=LegacyState)
        .node(
            ValidateOrderAction(),
            params_mapper=lambda s: ValidateParams(order_id=s["ref"]),
            response_mapper=lambda r: {"checked": r.valid},
        )
        .start(ValidateOrderAction)
        .edge(ValidateOrderAction, END)
        .compile()
    )
    result = await mapper_compiled.ainvoke(LegacyState(ref="ORD-005"))
    print(f"  ref={result['ref']}  checked={result['checked']}")
    result = await mapper_compiled.ainvoke(LegacyState(ref="inv-006"))
    print(f"  ref={result['ref']}  checked={result['checked']}")

    # --- Mermaid diagram (works because compile() returns a real CompiledGraph) --- #
    print("\n=== Graph structure ===")
    print(compiled.get_graph().draw_mermaid())


if __name__ == "__main__":
    asyncio.run(main())

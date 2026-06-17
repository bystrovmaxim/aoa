"""
08_custom_intent.py — Write your own intent (a rule that lands in the graph)

This is the meta-extension point. An intent turns a convention ("mark critical
operations") into a first-class graph object you can query — the same move every
shipped intent (@meta, @check_roles, @connection) makes. Four pieces:

  1. a DECORATOR that records the rule on the host class;
  2. a NODE (`BaseGraphNode`) — how the rule looks in the graph, with optional
     edges to other nodes;
  3. an INSPECTOR (`BaseGraphNodeInspector[Axis]`) — walks the axis (here every
     BaseAction) and emits a node for hosts that carry the rule;
  4. REGISTRATION — add the inspector to a `NodeGraphCoordinator` and inject it
     into the machine.

Here `@criticality("high")` annotates an operation; the inspector emits a
`Criticality` node linked to the Action node. After build, the graph can answer
"which operations are high-criticality?" — a question the plain code can't.

How-to: ../../docs/how-to/authoring-intent_draft.md

Run:
    uv run python examples/how_to/08_custom_intent.py
"""

import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.node_graph_coordinator_factory import all_axis_graph_node_inspectors
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

_CRITICALITY_ATTR = "_criticality_level"


# ── 1. The decorator: record the rule on the host class ──────────────────────
def criticality(level: str):
    def decorator(cls: type) -> type:
        setattr(cls, _CRITICALITY_ATTR, level)
        return cls
    return decorator


# ── 2. The node: how the rule looks in the graph (+ edge to the Action) ──────
class CriticalityGraphNode(BaseGraphNode[type]):
    NODE_TYPE = "Criticality"

    def __init__(self, action_cls: type, level: str) -> None:
        action_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=f"{action_id}#criticality",
            node_type=CriticalityGraphNode.NODE_TYPE,
            label=level,
            properties={"level": level},
            node_obj=action_cls,
        )
        # an edge to the existing Action node (its id is the action's full qualname)
        self._edges = [AssociationGraphEdge(edge_name="annotates", is_dag=False, target_node_id=action_id)]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return list(self._edges)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.node_id, "type": self.node_type, "label": self.label,
                "properties": {"level": self.properties["level"]}}


# ── 3. The inspector: emit a node for every Action carrying the rule ─────────
class CriticalityInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        level = cls.__dict__.get(_CRITICALITY_ATTR)        # own-class only, not inherited
        return CriticalityGraphNode(cls, level) if level else None


# ── Normal actions; one opts into the rule ───────────────────────────────────
class PaymentsDomain(BaseDomain):
    name = "payments"
    description = "Payments domain"


class ChargeParams(BaseParams):
    amount: float = Field(description="Amount")


class ChargeResult(BaseResult):
    ok: bool = Field(description="Charged")


@criticality("high")
@meta(description="Charge a card", domain=PaymentsDomain)
@check_roles(NoneRole)
class ChargeCardAction(BaseAction[ChargeParams, ChargeResult]):
    @summary_aspect("Charge")
    async def charge_summary(self, params, state, box, connections):
        return ChargeResult(ok=True)


@meta(description="Ping", domain=PaymentsDomain)
@check_roles(NoneRole)
class PingAction(BaseAction[ChargeParams, ChargeResult]):
    @summary_aspect("Ping")
    async def ping_summary(self, params, state, box, connections):
        return ChargeResult(ok=True)


async def main() -> None:
    # ── 4. Registration: standard inspectors + ours, injected into the machine ──
    coordinator = NodeGraphCoordinator()
    coordinator.build([*all_axis_graph_node_inspectors(), CriticalityInspector()])
    machine = ActionProductMachine(graph_coordinator=coordinator)

    # The rule is now a graph object — query it like any other node:
    crit_nodes = [n for n in machine.graph_coordinator.get_all_nodes()
                  if n.node_type == "Criticality"]
    print("Criticality nodes in the graph:")
    for n in crit_nodes:
        target = n.get_all_edges()[0].target_node_id.rsplit(".", 1)[-1]
        print(f"  level={n.properties['level']:<5} annotates -> {target}")

    # Self-audit style: which operations are high-criticality?
    high = [n.get_all_edges()[0].target_node_id.rsplit(".", 1)[-1]
            for n in crit_nodes if n.properties["level"] == "high"]
    print("high-criticality operations:", high)

    # The operation still runs normally — the intent only added knowledge:
    result = await machine.run(Context(), ChargeCardAction(), ChargeParams(amount=10.0), {})
    print("ChargeCardAction ran ->", result.ok)


if __name__ == "__main__":
    asyncio.run(main())

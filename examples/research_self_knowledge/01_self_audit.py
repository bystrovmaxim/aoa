"""
01_self_audit.py — The system audits itself from its own formal graph

Because every operation, role, dependency, step and compensator is a declared,
typed node in the machine's graph, the system can answer questions ABOUT ITSELF
that ordinary code cannot even pose — without running a single business call.

Two detections shown here are computable from the graph today:

  1. Dead role     — a Role declared but required by no operation (@check_roles
                     has no edge into it): a capability that grants access to nothing.
  2. Rollback gap  — an operation with regular (state-changing) steps but no
                     compensator: at a later failure there is no declared undo.

This is not a shipped linter — it is a few graph queries, to show the substrate
exists. The research note (../../docs/research/self-knowledge_draft.md) catalogs
the wider set of gaps, risks and suggestions this makes well-posed.

Run:
    uv run python examples/research_self_knowledge/01_self_audit.py
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import regular_aspect, summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.compensate import compensate
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class ShopDomain(BaseDomain):
    name = "shop"
    description = "Shop domain"


class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Store manager"


class AuditorRole(ApplicationRole):
    name = "auditor"
    description = "Declared, but no operation requires it"


class ChargeParams(BaseParams):
    order_id: str = Field(description="Order id")


class ChargeResult(BaseResult):
    txn_id: str = Field(description="Transaction id")


# Good: a state-changing step WITH a compensator (declared rollback).
@meta(description="Charge an order", domain=ShopDomain)
@check_roles(ManagerRole)
class ChargeAction(BaseAction[ChargeParams, ChargeResult]):
    @regular_aspect("Charge")
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        return {"txn_id": f"txn-{params.order_id}"}

    @compensate("charge_aspect", "Refund the charge")
    async def charge_compensate(self, params, state_before, state_after, box, connections, error):
        pass

    @summary_aspect("Done")
    async def done_summary(self, params, state, box, connections):
        return ChargeResult(txn_id=state["txn_id"])


# Gap: a state-changing step with NO compensator (no declared rollback).
@meta(description="Ship an order", domain=ShopDomain)
@check_roles(ManagerRole)
class ShipAction(BaseAction[ChargeParams, ChargeResult]):
    @regular_aspect("Ship")
    @result_string("txn_id", required=True)
    async def ship_aspect(self, params, state, box, connections):
        return {"txn_id": f"ship-{params.order_id}"}

    @summary_aspect("Done")
    async def done_summary(self, params, state, box, connections):
        return ChargeResult(txn_id=state["txn_id"])


def main() -> None:
    nodes = list(ActionProductMachine().graph_coordinator.get_all_nodes())

    # --- 1. Dead roles: a Role with no inbound @check_roles edge ---------------
    required_role_ids: set[str] = set()
    for n in nodes:
        for e in n.get_all_edges():
            if e.edge_name == "@check_roles":
                required_role_ids.add(e.target_node_id)
    dead_roles = [
        n.node_id.split(".")[-1]
        for n in nodes
        if n.node_type == "Role"
        and not n.node_id.startswith("aoa.action_machine.auth.")   # skip framework roles
        and n.node_id not in required_role_ids
    ]

    # --- 2. Rollback gap: regular steps but no compensator ---------------------
    gaps, ok = [], []
    for n in nodes:
        if n.node_type != "Action":
            continue
        ec = Counter(e.edge_name for e in n.get_all_edges())
        regular, comp = ec.get("@regular_aspect", 0), ec.get("@compensate", 0)
        name = n.node_id.split(".")[-1]
        (gaps if regular and not comp else ok).append((name, regular, comp))

    print("Self-audit of the declared graph (no business call executed):\n")
    print("Dead roles — declared, but required by no operation:")
    for r in dead_roles:
        print(f"  ⚠ {r}")
    print("\nRollback gaps — regular (state-changing) steps without a compensator:")
    for name, reg, comp in gaps:
        print(f"  ⚠ {name:<14} regular={reg} compensate={comp}")
    print("Has a declared rollback:")
    for name, reg, comp in ok:
        if reg:
            print(f"  ✓ {name:<14} regular={reg} compensate={comp}")


if __name__ == "__main__":
    main()

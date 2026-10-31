"""
19_changed_inside.py — what changed inside an action, which a use-case diagram does not draw

A use-case diagram draws actions, roles and their links, not an action's parts. When a part changes, the action is
marked changed and its card lists the parts. This example runs the function Maxitor's server calls over a small graph
and prints what the card reads.

The cases, with the real output at the bottom:

  1. a new result field: the action, and another action sharing the result;
  2. a changed field and an aspect, with both values;
  3. a link the diagram does not draw, to a resource;
  4. what the diagram draws is no part: a role, another action;
  5. an entity a field points at is not entered;
  6. an added action keeps its own status.

Output:

    1. A new result field
       SettleAction · Result: + currency
       RefundAction · Result: + currency
    2. A changed field and an aspect
       SettleAction · Params: ~ invoice (properties.description: Invoice id → The invoice to settle)
       SettleAction · summary: ~ summary (properties.description: Build the receipt → Settle and post)
    3. A link the diagram does not draw
       SettleAction · Links: ~ Ledger (properties.key: ledger → main)
    4. What the diagram draws is no part
       nothing changed inside
    5. An entity a field points at
       nothing changed inside
    6. An added action
       nothing changed inside
"""

from __future__ import annotations

import copy
from typing import Any

from maxitor.graph_compare import changed_inside, compare

ACTION = "shop.SettleAction"
OTHER = "shop.RefundAction"
RESULT = "shop.Receipt"
PARAMS = "shop.SettleAction.Params"
ASPECT = "shop.SettleAction:summary"


def node(node_id: str, node_type: str, label: str, **properties: Any) -> dict[str, Any]:
    """A node of a graph document."""
    return {"id": node_id, "type": node_type, "label": label, "properties": properties}


def edge(source: str, edge_type: str, target: str, relationship: str, **properties: Any) -> dict[str, Any]:
    """An edge of a graph document, with its protocol id."""
    return {"id": f"{source}|{edge_type}|{target}", "source_id": source, "target_id": target, "type": edge_type, "relationship": relationship, "is_dag": False, "properties": properties}


GRAPH: dict[str, Any] = {
    "schema_version": "1.1",
    "nodes": [
        node(ACTION, "Action", "SettleAction"),
        node(OTHER, "Action", "RefundAction"),
        node(RESULT, "Result", "Receipt"),
        node(PARAMS, "Params", "Params"),
        node(f"{RESULT}:reference", "Field", "reference", description="Capture id"),
        node(f"{PARAMS}:invoice", "Field", "invoice", description="Invoice id"),
        node(ASPECT, "SummaryAspect", "summary", description="Build the receipt"),
        node("shop.Clerk", "Role", "ClerkRole"),
        node("shop.Domain", "Domain", "ShopDomain"),
        node("shop.Ledger", "Resource", "Ledger", description="The ledger"),
        node("shop.Order", "Entity", "Order", description="An order"),
    ],
    "edges": [
        edge(ACTION, "generic:result", RESULT, "Aggregation"),
        edge(OTHER, "generic:result", RESULT, "Aggregation"),
        edge(ACTION, "generic:params", PARAMS, "Aggregation"),
        edge(RESULT, "field", f"{RESULT}:reference", "Composition"),
        edge(PARAMS, "field", f"{PARAMS}:invoice", "Composition"),
        edge(ACTION, "@summary_aspect", ASPECT, "Composition"),
        edge(ACTION, "@check_roles", "shop.Clerk", "Association"),
        edge(ACTION, "domain", "shop.Domain", "Aggregation"),
        edge(ACTION, "@connection", "shop.Ledger", "Association", key="ledger"),
        edge(f"{RESULT}:reference", "entity_schema", "shop.Order", "Aggregation"),
    ],
}


def edited() -> dict[str, Any]:
    """A copy of the graph to change."""
    return copy.deepcopy(GRAPH)


def node_of(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    """One node of a graph."""
    return next(each for each in graph["nodes"] if each["id"] == node_id)


def show(newer: dict[str, Any]) -> None:
    """Print what changed inside each action, as the use-case diagram's marks and card read it."""
    found = changed_inside(GRAPH, newer, compare(GRAPH, newer), root_type="Action", drawn_types={"Action", "Role"}, through={"generic:params", "generic:result"})
    if not found:
        print("   nothing changed inside")
    for action, parts in found.items():
        for part in parts:
            sign = {"added": "+", "removed": "−", "changed": "~"}[part.status.value]
            values = "".join(f" ({'.'.join(d.path)}: {d.before} → {d.after})" for d in part.differences)
            print(f"   {action.rsplit('.', 1)[-1]} · {part.group}: {sign} {part.label}{values}")


def main() -> None:
    """Run every case."""
    print("1. A new result field")
    graph = edited()
    graph["nodes"].append(node(f"{RESULT}:currency", "Field", "currency"))
    graph["edges"].append(edge(RESULT, "field", f"{RESULT}:currency", "Composition"))
    show(graph)
    print("2. A changed field and an aspect")
    graph = edited()
    node_of(graph, f"{PARAMS}:invoice")["properties"]["description"] = "The invoice to settle"
    node_of(graph, ASPECT)["properties"]["description"] = "Settle and post"
    show(graph)
    print("3. A link the diagram does not draw")
    graph = edited()
    next(each for each in graph["edges"] if each["type"] == "@connection")["properties"]["key"] = "main"
    node_of(graph, "shop.Ledger")["properties"]["description"] = "Reworded"
    show(graph)
    print("4. What the diagram draws is no part")
    graph = edited()
    node_of(graph, "shop.Clerk")["label"] = "CashierRole"
    node_of(graph, OTHER)["label"] = "ReturnAction"
    show(graph)
    print("5. An entity a field points at")
    graph = edited()
    node_of(graph, "shop.Order")["properties"]["description"] = "Reworded"
    show(graph)
    print("6. An added action")
    graph = edited()
    graph["nodes"].append(node("shop.VoidAction", "Action", "VoidAction"))
    graph["edges"].append(edge("shop.VoidAction", "generic:result", RESULT, "Aggregation"))
    show(graph)


if __name__ == "__main__":
    main()

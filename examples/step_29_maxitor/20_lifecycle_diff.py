"""
20_lifecycle_diff.py — what two versions of a lifecycle compare as

A lifecycle diagram draws states and transitions, so each carries its own mark. This example runs the comparison
Maxitor's server calls over a small lifecycle and prints the marks and the counts a diagram shows.

The cases, with the real output at the bottom:

  1. a lifecycle only the new version has: everything added;
  2. two transitions into one state from different states are two elements;
  3. a transition moved to another state is a removal and an addition;
  4. a change the drawing does not show, a state's order, still marks the state.

Output:

    1. A lifecycle only B has
       +7: 4 states, 3 transitions
    2. Two transitions into one state
       + issued -> expired
       + activated -> expired
    3. A transition moved
       - issued -> exhausted
       + activated -> exhausted
    4. A change the drawing does not show
       ~ expired (properties.attributes.sort_order: 4 -> 9)
"""

from __future__ import annotations

import copy
from typing import Any

from maxitor.graph_compare import Status, compare

ENTITY = "shop.Offer"
LIFECYCLE = f"{ENTITY}:lifecycle:status"
SIGN = {Status.ADDED: "+", Status.REMOVED: "-", Status.CHANGED: "~"}


def state(key: str, kind: str, order: int) -> dict[str, Any]:
    """A state of the lifecycle, as a graph node."""
    return {"id": f"{LIFECYCLE}:{key}", "type": kind, "label": key, "properties": {"state_key": key, "attributes": {"sort_order": order}}}


def transition(source: str, target: str) -> dict[str, Any]:
    """A transition of the lifecycle: its id holds the state it leaves."""
    ends = f"{LIFECYCLE}:{source}", f"{LIFECYCLE}:{target}"
    return {
        "id": f"{ends[0]}|lifecycle_transition|{ends[1]}|{source}",
        "source_id": ends[0],
        "target_id": ends[1],
        "type": "lifecycle_transition",
        "relationship": "Composition",
        "is_dag": False,
        "properties": {"from_state": source, "to_state": target},
    }


EMPTY: dict[str, Any] = {"schema_version": "1.1", "nodes": [], "edges": []}
GRAPH: dict[str, Any] = {
    "schema_version": "1.1",
    "nodes": [state("issued", "StateInitial", 1), state("activated", "StateFinal", 2), state("exhausted", "StateFinal", 3), state("expired", "StateFinal", 4)],
    "edges": [transition("issued", "activated"), transition("issued", "exhausted"), transition("issued", "expired")],
}


def show_transitions(older: dict[str, Any], newer: dict[str, Any]) -> None:
    """Print each changed transition with its sign."""
    result = compare(older, newer)
    for edge_id, element in result.edges.items():
        if element.status in SIGN:
            source, target = edge_id.split("|lifecycle_transition|")
            print(f"   {SIGN[element.status]} {source.rsplit(':', 1)[1]} -> {target.split('|')[0].rsplit(':', 1)[1]}")


print("1. A lifecycle only B has")
first = compare(EMPTY, GRAPH)
print(f"   +{first.node_counts.added + first.edge_counts.added}: {first.node_counts.added} states, {first.edge_counts.added} transitions")

print("2. Two transitions into one state")
two = copy.deepcopy(GRAPH)
two["edges"] = [*GRAPH["edges"][:2], transition("issued", "expired"), transition("activated", "expired")]
show_transitions({**GRAPH, "edges": GRAPH["edges"][:2]}, two)

print("3. A transition moved")
moved = copy.deepcopy(GRAPH)
moved["edges"] = [transition("issued", "activated"), transition("activated", "exhausted")]
show_transitions({**GRAPH, "edges": GRAPH["edges"][:2]}, moved)

print("4. A change the drawing does not show")
ordered = copy.deepcopy(GRAPH)
ordered["nodes"][3]["properties"]["attributes"]["sort_order"] = 9
for node_id, element in compare(GRAPH, ordered).nodes.items():
    if element.status in SIGN:
        difference = element.differences[0]
        print(f"   {SIGN[element.status]} {node_id.rsplit(':', 1)[1]} ({'.'.join(difference.path)}: {difference.before} -> {difference.after})")

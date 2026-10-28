"""
11_edge_ids.py — every edge of the graph has an id, so two versions compare edge by edge

A node of the graph has always had an id: the qualified name of the code that declares it. An edge
had none, and its source, type and target do not name it: an entity can hold two relations to the
same entity, and a lifecycle state can be entered from two states. ``aoa-action-machine`` now
writes an ``id`` on every exported edge (spec 031), computed by one public function,
``edge_id(row)``, from fields the row already carries — so a reader of an older file computes the
same id.

The cases, with the real output at the bottom:

  1. the default rule, ``<source_id>|<type>|<target_id>``;
  2. a relation is named by its field: two relations to one entity differ, and a relation that
     starts pointing at another entity keeps its id;
  3. a lifecycle transition appends the state it leaves: two ways into one state differ;
  4. the build refuses two edges with one id, naming both;
  5. the build refuses ``|`` inside a node id;
  6. a file of format 1.0 has no ``id``: the reader computes exactly the id the export writes;
  7. what format 1.1 changes for a reader: the version, the ``id`` field, the order, the schema.

Output:

    1. The default rule
       aoa.demo.model.access_cascade.actions.access_decide_shape_action.AccessDecideShapeAction|@check_roles|aoa.demo.model.access_cascade.roles.cascade_application_roles.CascadeOfficerRole
    2. A relation is named by its field
       AssuranceDelegatedWorkTicketCoreEntity|entity_relation|assignee_actor
       AssuranceDelegatedWorkTicketCoreEntity|entity_relation|delegator_actor
       pointing at another entity, the same id: True
    3. A transition appends the state it leaves
       DiscountApplicationCoreEntity:lifecycle:lifecycle:cancelled|new
       DiscountApplicationCoreEntity:lifecycle:lifecycle:cancelled|payment_pending
    4. Two edges with one id
       DuplicateEdgeError: Edge id conflict 'shop.Order|uses|shop.Stock':
         first edge:  shop.Order -[uses]-> shop.Stock
         second edge: shop.Order -[uses]-> shop.Stock
       Declare an ID_RULE on the edge class that tells these edges apart.
    5. A node id with the separator
       InvalidGraphError: Node id 'shop.Odd|Name' contains '|', which separates edge id parts.
    6. A file of format 1.0
       4841 edges without id, ids computed: 4841, equal to the written ones: True
    7. What format 1.1 changes
       schema_version: 1.1
       every edge has an id: True
       edges in id order: True
       an edge without id passes the schema: False

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (graph export)

Run:
    uv run python examples/step_26_maxitor/11_edge_ids.py
"""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector
from aoa.action_machine.graph.core.exceptions import DuplicateEdgeError, InvalidGraphError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.edge_identity import edge_id
from aoa.action_machine.graph.graph_json_schema import GRAPH_JSON_SCHEMA
from aoa.demo.model.services.graph_json_service import ExampleModelGraphJsonService

# The demo model's export, as any AOA service writes it.
GRAPH = json.loads(ExampleModelGraphJsonService().coordinator_json())
EDGES = GRAPH["edges"]


def short(node_id: str) -> str:
    """The last part of a qualified name, enough to read an id."""
    return node_id.rsplit(".", 1)[-1]


def repeating(edge_type: str) -> list[dict[str, Any]]:
    """The first pair of ``edge_type`` edges that share their source and target."""
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in EDGES:
        if edge["type"] == edge_type:
            pair = (edge["source_id"], edge["target_id"])
            if pair in seen:
                return [seen[pair], edge]
            seen[pair] = edge
    raise LookupError(edge_type)


class Axis:
    """The one host type of a tiny hand-made graph."""


class Node(BaseGraphNode[object]):
    """A node of a tiny hand-made graph, with its edges and the nodes it brings along."""

    def __init__(self, node_id: str, edges: list[BaseGraphEdge] | None = None, brings: list[BaseGraphNode[Any]] | None = None) -> None:
        super().__init__(node_id=node_id, node_type="Params", label=node_id, properties={}, node_obj=object())
        object.__setattr__(self, "_edges", edges or [])
        object.__setattr__(self, "_brings", brings or [])

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        return self._brings

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return self._edges


class Inspector(BaseGraphNodeInspector[Axis]):
    """Hands the tiny graph to the coordinator."""

    def __init__(self, root: BaseGraphNode[object]) -> None:
        self._root_node = root

    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        return self._root_node if cls is Axis else None


def build(root: BaseGraphNode[object]) -> None:
    """Build a graph from ``root`` and print why it is refused."""
    try:
        NodeGraphCoordinator().build([Inspector(root)])
    except (DuplicateEdgeError, InvalidGraphError) as refusal:
        text = str(refusal).replace("\n", "\n   ")
        print(f"   {type(refusal).__name__}: {text}")


def uses(target: str) -> AssociationGraphEdge:
    """An edge type without an id rule."""
    return AssociationGraphEdge(edge_name="uses", is_dag=False, target_node_id=target)


print("1. The default rule")
print("  ", next(e for e in EDGES if e["type"] == "@check_roles")["id"])

print("2. A relation is named by its field")
first, second = repeating("entity_relation")
for edge in (first, second):
    print("  ", short(edge["id"]))
moved = {**first, "target_id": "aoa.demo.SomeOtherEntity"}
print("   pointing at another entity, the same id:", edge_id(moved) == first["id"])

print("3. A transition appends the state it leaves")
for edge in repeating("lifecycle_transition"):
    print("  ", short(edge["id"]))

print("4. Two edges with one id")
build(Node("shop.Order", edges=[uses("shop.Stock"), uses("shop.Stock")], brings=[Node("shop.Stock")]))

print("5. A node id with the separator")
build(Node("shop.Order", brings=[Node("shop.Odd|Name")]))

print("6. A file of format 1.0")
old_rows = [{key: value for key, value in edge.items() if key != "id"} for edge in EDGES]
computed = [edge_id(row) for row in old_rows]
print(f"   {len(old_rows)} edges without id, ids computed: {len(set(computed))},"
      f" equal to the written ones: {computed == [edge['id'] for edge in EDGES]}")

print("7. What format 1.1 changes")
ids = [edge["id"] for edge in EDGES]
print("   schema_version:", GRAPH["schema_version"])
print("   every edge has an id:", all(ids))
print("   edges in id order:", ids == sorted(ids))
without_id = {**GRAPH, "edges": [old_rows[0], *EDGES[1:]]}
print("   an edge without id passes the schema:", Draft202012Validator(GRAPH_JSON_SCHEMA).is_valid(without_id))

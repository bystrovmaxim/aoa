<!-- translated-from: authoring-intent_draft.md @ 2026-06-17T11:45:55Z · sha256:e1ea6da176f5 -->
<p align="center">
  <img src="../assets/aoa-logo.png" alt="AOA" width="200">
</p>

# Your own intent

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

- [When this is needed](#when-this-is-needed)
- [Four parts](#four-parts)
- [Step 1. The decorator: record the rule on the class](#step-1-the-decorator-record-the-rule-on-the-class)
- [Step 2. The node: how the rule looks in the graph](#step-2-the-node-how-the-rule-looks-in-the-graph)
- [Step 3. The inspector: emit nodes along an axis](#step-3-the-inspector-emit-nodes-along-an-axis)
- [Step 4. Registration in the coordinator](#step-4-registration-in-the-coordinator)
- [What is important to know](#what-is-important-to-know)
- [Verification](#verification)

---

## When this is needed

This is the deepest extension point. An intent turns an agreement — "we mark critical operations", "this is PII", "this step has an SLA" — into a **full-fledged graph object** that can be walked and queried. The same move the shipped `@meta`, `@check_roles`, `@connection` are built on: exactly the reification discussed in [«Questions AOA answers with code»](../explanation/questions-aoa-answers-with-code.md). Once a rule lands in the graph, you can build a [self-audit](../research/self-knowledge.md) and [Maxitor](../tutorials/step-26-maxitor.md) diagrams on it.

The full example: [08_custom_intent.py](../../examples/how_to/08_custom_intent.py).

## Four parts

Your own intent is four small pieces:

1. **A decorator** — records the rule on the host class.
2. **A node** (`BaseGraphNode`) — how the rule looks in the graph; optionally with edges to other nodes.
3. **An inspector** (`BaseGraphNodeInspector[Axis]`) — walks the axis (for example, all `BaseAction`) and emits a node for the rule's carriers.
4. **Registration** — add the inspector to a `NodeGraphCoordinator` and inject it into the machine.

The end-to-end example: `@criticality("high")` marks an operation, the inspector puts a `Criticality` node into the graph with an edge to the operation's node — and the graph starts answering the question "which operations are critical", which ordinary code cannot even pose.

## Step 1. The decorator: record the rule on the class

The decorator is the "intent" itself: it fixes the rule's data on the class (as the shipped intents write their markers).

```python
_CRITICALITY_ATTR = "_criticality_level"

def criticality(level: str):
    def decorator(cls: type) -> type:
        setattr(cls, _CRITICALITY_ATTR, level)
        return cls
    return decorator
```

## Step 2. The node: how the rule looks in the graph

Subclass `BaseGraphNode[T]` and assemble the node from the carrier: a **unique** `node_id`, `node_type`, `label`, `properties`, and the class itself as `node_obj`. Edges to other nodes are returned through `get_all_edges()`:

```python
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

class CriticalityGraphNode(BaseGraphNode[type]):
    NODE_TYPE = "Criticality"

    def __init__(self, action_cls: type, level: str) -> None:
        action_id = TypeIntrospection.full_qualname(action_cls)     # = the Action node's node_id
        super().__init__(
            node_id=f"{action_id}#criticality", node_type=self.NODE_TYPE,
            label=level, properties={"level": level}, node_obj=action_cls,
        )
        self._edges = [AssociationGraphEdge(edge_name="annotates", is_dag=False, target_node_id=action_id)]

    def get_all_edges(self):
        return list(self._edges)

    def to_dict(self):                                              # needed only for JSON export
        return {"id": self.node_id, "type": self.node_type, "label": self.label,
                "properties": {"level": self.properties["level"]}}
```

The `annotates` edge targets the operation node's `node_id` — and its `id` equals the class's `full_qualname`. The machine wires the edges by `target_node_id` at build.

## Step 3. The inspector: emit nodes along an axis

Subclass `BaseGraphNodeInspector[Axis]`, where the axis is a root type (`BaseAction[Any, Any]`, `BaseEntity`, `BaseResource`…). Implement only `_get_node(cls)`: return a node for the rule's carriers or `None` for the rest. The base itself walks the axis and all its subclasses:

```python
from typing import Any
from aoa.action_machine.graph.core.base_graph_node_inspector import BaseGraphNodeInspector

class CriticalityInspector(BaseGraphNodeInspector[BaseAction[Any, Any]]):
    def _get_node(self, cls: type) -> BaseGraphNode[Any] | None:
        level = cls.__dict__.get(_CRITICALITY_ATTR)     # own-class, so the rule is not inherited
        return CriticalityGraphNode(cls, level) if level else None
```

`cls.__dict__.get(...)` instead of `getattr(...)` — if the rule must not be inherited by subclasses; for an inheritable rule use `getattr`.

## Step 4. Registration in the coordinator

Add your inspector to the shipped ones and build the coordinator, then inject it into the machine:

```python
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.node_graph_coordinator_factory import all_axis_graph_node_inspectors

coordinator = NodeGraphCoordinator()
coordinator.build([*all_axis_graph_node_inspectors(), CriticalityInspector()])
machine = ActionProductMachine(graph_coordinator=coordinator)

# the rule is now a graph object:
crit = [n for n in machine.graph_coordinator.get_all_nodes() if n.node_type == "Criticality"]
```

## What is important to know

- **`build()` tests the graph for soundness.** `node_id` must be unique; each edge's `target_node_id` must resolve to an existing node (otherwise `InvalidGraphError`); among edges with `is_dag=True` there must be no cycles. For annotations set `is_dag=False`.
- **A custom `node_type` is not rejected by the graph.** The `export_json_schema` parameter of `build()` is currently ignored — your new node type passes on a par with the shipped ones.
- **The inspector reflects the loaded scope.** The base walks the axis and all its subclasses actually imported into the interpreter; "junk" classes from tests/samples are excluded via [`exclude_graph_model`](../tutorials/step-26-maxitor.md) or by cleaning imports, not by a filter in the inspector.
- **`to_dict()` is only for JSON export.** Introspection via `get_all_nodes()`/`get_all_edges()` does not call it, but with non-empty `properties` it must be overridden (otherwise the base raises on export).

## Verification

```bash
uv run python examples/how_to/08_custom_intent.py
```

```text
Criticality nodes in the graph:
  level=high  annotates -> ChargeCardAction
high-criticality operations: ['ChargeCardAction']
ChargeCardAction ran -> True
```

The `@criticality` rule became a graph node with an edge to the operation; the graph answered which operations are critical, while the operation itself kept working as before — the intent only added knowledge. This is the whole AOA move in miniature: [an agreement turned into a verifiable object](../explanation/questions-aoa-answers-with-code.md). How this graph is read as a whole — [the operation graph (Maxitor)](../tutorials/step-26-maxitor.md); how diagnostics are built on it — [what the system knows about itself](../research/self-knowledge.md).

---

<table width="100%"><tr>
  <td align="left"></td>
  <td align="center"><a href="../index.md">Contents</a></td>
  <td align="right"></td>
</tr></table>

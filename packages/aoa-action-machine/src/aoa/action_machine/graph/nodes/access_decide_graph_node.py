# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/access_decide_graph_node.py
"""
AccessDecideGraphNode — interchange node for an operation's declared object check.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen interchange vertex for the ``@access_decide`` callable one
operation declares: ``node_id`` is the operation's dotted id plus ``:`` plus the
method name, interchange ``node_type`` is ``AccessDecide``, ``label`` is the
method name, and ``node_obj`` is the callable itself. The operation reaches this
node by a composition edge, so the object check appears in the assembled graph
the way the other declared behaviours do — rather than being a method only the
runtime knows about.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    ActionGraphNode ──@access_decide──▶ AccessDecideGraphNode
                                             │ node_obj: the declared callable
                                             │ node_id:  <action> : <method>
                                             └ label:    the method name

    The node carries no edges of its own: the declaration answers about the
    operation's object and depends on nothing else.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the vertex, its identifier and label, and its JSON form.

OUT: finding the declaration (the intent resolver does that) and judging its
answer (the object step of the cascade does that).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.required_context_graph_edge import RequiredContextGraphEdge
from aoa.action_machine.intents.access_decide.access_decide_intent_resolver import (
    AccessDecideIntentResolver,
)
from aoa.action_machine.intents.access_decide.access_decide_signature import validate_types
from aoa.action_machine.system_core.type_introspection import TypeIntrospection


@dataclass(init=False, frozen=True)
class AccessDecideGraphNode(BaseGraphNode[Callable[..., Any]]):
    """
    AI-CORE-BEGIN
        ROLE: Interchange node for the ``@access_decide`` callable of one operation.
        CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(_action_cls) + ':' + method_name``; :attr:`NODE_TYPE` is ``AccessDecide``; ``label`` is the method name; ``node_obj`` is the declared callable; ``properties["description"]`` carries what the check says it decides; :attr:`required_context` holds the ``RequiredContextGraphEdge`` companions the declaration asked for with ``@context_requires``, exactly as the aspect nodes carry theirs.
        INVARIANTS: One node per declaration — the resolver refuses a second one, so an operation never has two of these. The declared signature is validated against the contract types while this node is built: ``params``, ``context``, ``box``, ``connections`` (and ``ctx``) resolve to what the object step hands over, and the return resolves to a verdict.
        FAILURES: :exc:`TypeError` from :func:`~aoa.action_machine.intents.access_decide.access_decide_signature.validate_types` when an annotation cannot be resolved or names something the step never hands over.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "AccessDecide"
    required_context: list[RequiredContextGraphEdge]

    def __init__(self, check_func: Callable[..., Any], _action_cls: type[Any]) -> None:
        validate_types(_action_cls, check_func)
        method_name = TypeIntrospection.unwrapped_callable_name(check_func)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        super().__init__(
            node_id=f"{action_id}:{method_name}",
            node_type=AccessDecideGraphNode.NODE_TYPE,
            label=method_name,
            properties={"description": AccessDecideIntentResolver.resolve_description(_action_cls)},
            node_obj=check_func,
        )
        object.__setattr__(
            self,
            "required_context",
            RequiredContextGraphEdge.get_required_context_edges(check_func, _action_cls, self),
        )

    def get_required_context_keys(self) -> frozenset[str]:
        """Return the dot-path keys the declaration asked for (``properties['key']`` per edge)."""
        out: set[str] = set()
        for edge in self.required_context:
            key = edge.properties.get("key")
            if isinstance(key, str):
                out.add(key)
        return frozenset(out)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the required-context composition edges materialized on this node."""
        return [*self.required_context]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return the required-context companion nodes this declaration pulled in."""
        return [edge.target_node for edge in self.required_context if edge.target_node is not None]

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-safe vertex (``id``, ``type``, ``label``, properties)."""
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": dict(self.properties),
        }

# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/required_context_graph_node.py
"""
RequiredContextGraphNode — interchange node for one ``@context_requires`` dot-path on an aspect method.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.graph.base_graph_node.BaseGraphNode` for a single declared
context key on a concrete ``BaseAction`` regular aspect callable. Composition edges to
these nodes originate on :class:`~aoa.action_machine.graph_model.nodes.regular_aspect_graph_node.RegularAspectGraphNode`
(analogous to :class:`~aoa.action_machine.graph_model.nodes.checker_graph_node.CheckerGraphNode` rows bound via ``_checker_meta``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``ContextRequiresResolver.resolve_required_context_keys(aspect_callable)``
        │
        v
One node per distinct key ──► ``CompositionGraphEdge`` from RegularAspect ──► this node type.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class RequiredContextGraphPayload:
    """Payload for ``node_obj``: host action, aspect method label, declared context dot-path."""

    action_cls: type[Any]
    aspect_method_name: str
    context_key: str


@dataclass(init=False, frozen=True)
class RequiredContextGraphNode(BaseGraphNode[RequiredContextGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange graph node for one ``@context_requires`` key on an aspect callable.
    CONTRACT: ``node_id`` ends with ``:reqctx:{context_key}``; NODE_TYPE ``RequiredContext``; ``properties`` expose ``key``.
    INVARIANTS: One node per declared key after resolver normalization (sorted list from :class:`~aoa.action_machine.intents.context_requires.context_requires_resolver.ContextRequiresResolver`).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "RequiredContext"

    def __init__(
        self,
        aspect_callable: Callable[..., Any],
        _action_cls: type[Any],
        context_key: str,
    ) -> None:
        aspect_method_name = TypeIntrospection.unwrapped_callable_name(aspect_callable)
        action_id = TypeIntrospection.full_qualname(_action_cls)
        key_s = context_key.strip()
        node_id = f"{action_id}:{aspect_method_name}:reqctx:{key_s}"
        payload = RequiredContextGraphPayload(
            action_cls=_action_cls,
            aspect_method_name=aspect_method_name,
            context_key=key_s,
        )
        super().__init__(
            node_id=node_id,
            node_type=RequiredContextGraphNode.NODE_TYPE,
            label=key_s,
            properties={"key": key_s},
            node_obj=payload,
        )

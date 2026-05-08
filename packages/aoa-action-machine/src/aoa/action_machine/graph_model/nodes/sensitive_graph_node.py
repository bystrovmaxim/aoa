# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/sensitive_graph_node.py
"""
SensitiveGraphNode — interchange graph node for one ``@sensitive`` field on a host type.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.graph.base_graph_node.BaseGraphNode` for one property
that carries ``_sensitive_config`` (see :mod:`aoa.action_machine.intents.sensitive.sensitive_decorator`).
Masking parameters are read via :meth:`~aoa.action_machine.intents.sensitive.sensitive_intent_resolver.SensitiveIntentResolver.resolve_sensitive_field`.
``node_id`` uses a ``:sensitive:`` segment so it does not collide with :class:`~aoa.action_machine.graph_model.nodes.property_field_graph_node.PropertyFieldGraphNode`
on the same property name. ``node_obj`` is a frozen :class:`SensitiveGraphPayload`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from aoa.action_machine.intents.sensitive.sensitive_intent_resolver import SensitiveIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class SensitiveGraphNodeEdgeInfo:
    """
    AI-CORE-BEGIN
    ROLE: Interchange target id for an outgoing composition edge to :class:`SensitiveGraphNode`.
    CONTRACT: ``for_property`` builds the same ``node_id`` string as :class:`SensitiveGraphNode`.
    AI-CORE-END
    """

    target_node_id: str

    @classmethod
    def for_property(cls, parent_type: type, property_name: str) -> SensitiveGraphNodeEdgeInfo:
        """Match :meth:`SensitiveGraphNode` interchange ``node_id`` for ``parent_type`` + ``property_name``."""
        name = property_name.strip()
        tid = f"{TypeIntrospection.full_qualname(parent_type)}:sensitive:{name}"
        return cls(target_node_id=tid)


@dataclass(frozen=True)
class SensitiveGraphPayload:
    """Frozen payload for :attr:`~aoa.graph.base_graph_node.BaseGraphNode.node_obj`."""

    property_name: str
    sensitive_enabled: bool
    sensitive_max_chars: int
    sensitive_char: str
    sensitive_max_percent: int


@dataclass(init=False, frozen=True)
class SensitiveGraphNode(BaseGraphNode[SensitiveGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one ``@sensitive`` masking config on ``parent_type``.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(parent_type) + ':sensitive:' + property_name.strip()``;
    :attr:`NODE_TYPE` is ``Sensitive``; reads masking params via
    :meth:`~aoa.action_machine.intents.sensitive.sensitive_intent_resolver.SensitiveIntentResolver.resolve_sensitive_field`;
    ``edges`` empty; ``properties`` mirror the resolved row.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Sensitive"

    def __init__(self, parent_type: type, property_name: str) -> None:
        if not isinstance(parent_type, type):
            msg = f"parent_type must be a type, got {type(parent_type).__name__}"
            raise TypeError(msg)

        name = property_name.strip()
        row = SensitiveIntentResolver.resolve_sensitive_field(parent_type, name)
        if row is None:
            raise ValueError(
                f"No @sensitive configuration on {TypeIntrospection.full_qualname(parent_type)!r} "
                f"for property {name!r}.",
            )

        node_obj = SensitiveGraphPayload(property_name=name, **row)
        node_id = SensitiveGraphNodeEdgeInfo.for_property(parent_type, name).target_node_id
        super().__init__(
            node_id=node_id,
            node_type=SensitiveGraphNode.NODE_TYPE,
            label=name,
            properties=dict(row),
            node_obj=node_obj,
        )

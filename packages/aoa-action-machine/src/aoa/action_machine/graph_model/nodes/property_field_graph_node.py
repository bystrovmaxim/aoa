# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/property_field_graph_node.py
"""
PropertyFieldGraphNode — interchange node for one property-style member under a host type (``parent_type``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.graph.base_graph_node.BaseGraphNode` for one logical property / computed-style member under a
caller-supplied host ``parent_type`` (typically a params or result schema class). ``node_id`` is the host
dotted id plus ``:`` plus the property name; ``node_obj`` is a frozen :class:`PropertyFieldGraphPayload` (includes ``host_type`` for companions / masking).

If the member is ``@sensitive`` on ``parent_type``, a stub :class:`~aoa.action_machine.graph_model.edges.sensitive_graph_edge.SensitiveGraphEdge`
is resolved internally; :meth:`get_all_edges` returns it, and :meth:`get_companion_nodes` adds the matching :class:`~aoa.action_machine.graph_model.nodes.sensitive_graph_node.SensitiveGraphNode`.

Constructor shape matches :class:`FieldGraphNode` (``parent_type``, name, ``required``); this node names that string ``property_name`` on the payload. Callers supply interchange metadata explicitly; optional stub edges use :meth:`~aoa.action_machine.graph_model.edges.sensitive_graph_edge.SensitiveGraphEdge.get_sensitive_edge`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from aoa.action_machine.graph_model.edges.sensitive_graph_edge import SensitiveGraphEdge
from aoa.action_machine.graph_model.nodes.sensitive_graph_node import SensitiveGraphNode
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class PropertyFieldGraphPayload:
    """Frozen payload for :attr:`~aoa.graph.base_graph_node.BaseGraphNode.node_obj` (property-field row metadata)."""

    host_type: type[Any]
    property_name: str
    required: bool


@dataclass(init=False, frozen=True)
class PropertyFieldGraphNode(BaseGraphNode[PropertyFieldGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one declared property-style member under a host ``parent_type``.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(parent_type) + ':' + property_name.strip()``;
    :attr:`NODE_TYPE` is ``PropertyField``; ``parent_type`` must be a ``type``;
    ``@sensitive`` stub edge is derived via :meth:`~aoa.action_machine.graph_model.edges.sensitive_graph_edge.SensitiveGraphEdge.get_sensitive_edge`;
    when non-``None``, :meth:`get_companion_nodes` materializes :class:`~aoa.action_machine.graph_model.nodes.sensitive_graph_node.SensitiveGraphNode`;
    Interchange ``properties`` carry ``required`` only;
    :class:`PropertyFieldGraphPayload` holds ``host_type``, property name, and required flag.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "PropertyField"
    sensitive: SensitiveGraphEdge | None

    def __init__(
        self,
        parent_type: type,
        property_name: str,
        *,
        required: bool = False,
    ) -> None:
        if not isinstance(parent_type, type):
            msg = f"parent_type must be a type, got {type(parent_type).__name__}"
            raise TypeError(msg)

        stripped = property_name.strip()
        node_obj = PropertyFieldGraphPayload(
            host_type=parent_type,
            property_name=property_name,
            required=required,
        )
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(parent_type)}:{stripped}",
            node_type=PropertyFieldGraphNode.NODE_TYPE,
            label=stripped,
            properties={
                "required": required,
            },
            node_obj=node_obj,
        )
        sens = SensitiveGraphEdge.get_sensitive_edge(parent_type, stripped)
        object.__setattr__(self, "sensitive", sens)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return the optional stub :class:`SensitiveGraphEdge` toward :class:`SensitiveGraphNode`."""
        if self.sensitive is None:
            return []
        return [self.sensitive]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Attach :class:`SensitiveGraphNode` when a sensitive stub edge is present (coordinator expansion)."""
        if self.sensitive is None:
            return []

        host = self.node_obj.host_type
        prop = self.node_obj.property_name.strip()
        return [SensitiveGraphNode(host, prop)]

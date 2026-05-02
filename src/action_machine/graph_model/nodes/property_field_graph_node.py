# src/action_machine/graph_model/nodes/property_field_graph_node.py
"""
PropertyFieldGraphNode — interchange node for one property-style member under a host type (``parent_type``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one logical property / computed-style member under a
caller-supplied host ``parent_type`` (typically a params or result schema class). ``node_id`` is the host
dotted id plus ``:`` plus the property name (``parent_type`` is only an argument to ``__init__``, not stored on the payload); ``node_obj`` is a frozen :class:`PropertyFieldGraphPayload`.

Constructor shape matches :class:`FieldGraphNode` (``parent_type``, name, ``required``); this node names that string ``property_name`` on the payload. The class does **not** read Pydantic metadata; callers supply interchange metadata explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class PropertyFieldGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` (property-field row metadata only)."""

    property_name: str
    required: bool


@dataclass(init=False, frozen=True)
class PropertyFieldGraphNode(BaseGraphNode[PropertyFieldGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one declared property-style member under a host ``parent_type``.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(parent_type) + ':' + property_name.strip()``;
    :attr:`NODE_TYPE` is ``PropertyField``; ``parent_type`` must be a ``type``; ``edges`` empty;
    Interchange ``properties`` on the node carry ``required`` only;
    :class:`PropertyFieldGraphPayload` holds property name and required flag.
    No schema introspection inside the class.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "PropertyField"

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

        node_obj = PropertyFieldGraphPayload(
            property_name=property_name,
            required=required,
        )
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(parent_type)}:{property_name.strip()}",
            node_type=PropertyFieldGraphNode.NODE_TYPE,
            label=property_name.strip(),
            properties={
                "required": required,
            },
            node_obj=node_obj,
        )

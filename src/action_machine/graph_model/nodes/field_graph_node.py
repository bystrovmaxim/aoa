# src/action_machine/graph_model/nodes/field_graph_node.py
"""
FieldGraphNode — interchange node for one field under a host type (``parent_type``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` for one logical field under a
caller-supplied host ``parent_type`` (typically a params or result schema class). ``node_id`` is the host
dotted id plus ``:`` plus the field name (``parent_type`` is only an argument to ``__init__``, not stored on the payload); ``node_obj`` is a frozen :class:`FieldGraphPayload`.

Constructor inputs mirror :class:`CheckerGraphNode`: ``parent_type``, ``field_name``, optional ``description``, and ``required``. The class does **not** read Pydantic ``model_fields``; callers supply interchange metadata explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode


@dataclass(frozen=True)
class FieldGraphPayload:
    """Frozen payload for :attr:`~graph.base_graph_node.BaseGraphNode.node_obj` (field row metadata only)."""

    field_name: str
    description: str
    required: bool


@dataclass(init=False, frozen=True)
class FieldGraphNode(BaseGraphNode[FieldGraphPayload]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for one declared field under a host ``parent_type``.
    CONTRACT: ``node_id`` = ``TypeIntrospection.full_qualname(parent_type) + ':' + field_name.strip()``;
    :attr:`NODE_TYPE` is ``Field``; ``parent_type`` must be a ``type``; ``edges`` empty;
    Interchange ``properties`` on the node carry ``required`` and ``description`` (empty string when omitted);
    :class:`FieldGraphPayload` holds field name, description, and required flag.
    No schema introspection inside the class.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Field"

    def __init__(
        self,
        parent_type: type,
        field_name: str,
        *,
        description: str | None = None,
        required: bool = False,
    ) -> None:
        if not isinstance(parent_type, type):
            msg = f"parent_type must be a type, got {type(parent_type).__name__}"
            raise TypeError(msg)

        node_obj = FieldGraphPayload(
            field_name=field_name,
            description="" if description is None else description,
            required=required,
        )
        super().__init__(
            node_id=f"{TypeIntrospection.full_qualname(parent_type)}:{field_name.strip()}",
            node_type=FieldGraphNode.NODE_TYPE,
            label=field_name.strip(),
            properties={
                "required": required,
                "description": "" if description is None else description,
            },
            node_obj=node_obj,
        )

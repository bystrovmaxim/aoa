# src/action_machine/model/graph_model/params_graph_node.py
"""
ParamsGraphNode — interchange node for ``BaseParams`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete params **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

For each declared Pydantic field on the params class, emits a :class:`FieldGraphNode` as
:attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` and a ``COMPOSITION`` edge from this
params vertex to that field (same pattern as :class:`RegularAspectGraphNode` and checkers).
For each entry in ``model_computed_fields`` (``@computed_field``) and each public plain ``property`` on the class
(``__dict__`` over MRO, excluding names that clash with ``model_fields`` or already emitted from computed fields), emits a
:class:`PropertyFieldGraphNode` companion and a
``COMPOSITION`` edge (``edge_name`` prefix ``property:``).

Interchange ``node_type`` is ``"Params"``; ``id`` is the dotted class path. (Legacy facet rows may still use the string ``params_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsGraphNode(...)  ──>  frozen ``BaseGraphNode`` + ``FieldGraphNode`` / ``PropertyFieldGraphNode`` companions + edges
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from action_machine.model.base_params import BaseParams
from action_machine.model.graph_model.edges.field_graph_edge import FieldGraphEdge
from action_machine.model.graph_model.edges.property_graph_edge import PropertyGraphEdge
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsGraphNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label;
    empty ``properties`` (interchange dict); composition lists :attr:`fields` and :attr:`props`
    from ``FieldGraphEdge.get_field_edges`` / ``PropertyGraphEdge.get_property_edges``; :attr:`companion_nodes` from both.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Params"
    fields: list[FieldGraphEdge]
    props: list[PropertyGraphEdge]

    def __init__(self, params_cls: type[TParams]) -> None:
        params_node_id = TypeIntrospection.full_qualname(params_cls)
        super().__init__(
            node_id=params_node_id,
            node_type=ParamsGraphNode.NODE_TYPE,
            label=params_cls.__name__,
            properties={},
            node_obj=params_cls,
        )
        object.__setattr__(self, "fields", FieldGraphEdge.get_field_edges(params_cls, params_node_id, ParamsGraphNode.NODE_TYPE))
        object.__setattr__(self, "props", PropertyGraphEdge.get_property_edges(params_cls, params_node_id, ParamsGraphNode.NODE_TYPE))

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return all outgoing composition edges materialized in explicit edge fields."""
        return [*self.fields, *self.props]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return field and property nodes carried as targets by explicit composition edges."""
        return [
            edge.target_node
            for edge in [*self.fields, *self.props]
            if edge.target_node is not None
        ]

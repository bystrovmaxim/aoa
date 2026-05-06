# src/action_machine/graph_model/nodes/result_graph_node.py
"""
ResultGraphNode — interchange node for ``BaseResult`` schema classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
a concrete result **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

For each declared Pydantic field on the result class, emits a :class:`FieldGraphNode` as
:attr:`~graph.base_graph_node.BaseGraphNode.companion_nodes` and a ``COMPOSITION`` edge from this
result graph node for that field (same pattern as :class:`RegularAspectGraphNode` and checkers).
For each entry in ``model_computed_fields`` (``@computed_field``) and each public plain ``property`` on the class
(``__dict__`` over MRO, excluding names that clash with ``model_fields`` or already emitted from computed fields), emits a
:class:`PropertyFieldGraphNode` companion and a
``COMPOSITION`` edge (``edge_name`` ``property`` on the typed edge class).

Interchange ``node_type`` is ``"Result"``; ``id`` is the dotted class path. (Older interchange payloads may still use the string ``result_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResult]   (``TResult`` bound to ``BaseResult``)
              │
              v
    ResultGraphNode(...)  ──>  frozen ``BaseGraphNode`` + ``FieldGraphNode`` / ``PropertyFieldGraphNode`` companions + edges
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from action_machine.graph_model.edges.field_graph_edge import FieldGraphEdge
from action_machine.graph_model.edges.property_graph_edge import PropertyGraphEdge
from action_machine.model.base_result import BaseResult
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultGraphNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label;
    empty ``properties`` (interchange dict); composition lists :attr:`fields` and :attr:`props`
    from ``FieldGraphEdge.get_field_edges`` / ``PropertyGraphEdge.get_property_edges`` wired to ``self`` host; :attr:`companion_nodes` from both.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Result"
    fields: list[FieldGraphEdge]
    props: list[PropertyGraphEdge]

    def __init__(self, result_cls: type[TResult]) -> None:
        result_node_id = TypeIntrospection.full_qualname(result_cls)
        super().__init__(
            node_id=result_node_id,
            node_type=ResultGraphNode.NODE_TYPE,
            label=result_cls.__name__,
            properties={},
            node_obj=result_cls,
        )
        object.__setattr__(self, "fields", FieldGraphEdge.get_field_edges(result_cls, self))
        object.__setattr__(self, "props", PropertyGraphEdge.get_property_edges(result_cls, self))

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return all outgoing composition edges materialized in explicit edge fields."""
        return [*self.fields, *self.props]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Return field and property nodes carried as targets by explicit composition edges."""
        return [edge.target_node for edge in [*self.fields, *self.props] if edge.target_node is not None]

# src/action_machine/model/graph_model/result_graph_node.py
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
result vertex to that field (same pattern as :class:`RegularAspectGraphNode` and checkers).
For each entry in ``model_computed_fields`` (``@computed_field``) and each public plain ``property`` on the class
(``__dict__`` over MRO, excluding names that clash with ``model_fields`` or already emitted from computed fields), emits a
:class:`PropertyFieldGraphNode` companion and a
``COMPOSITION`` edge (``edge_name`` prefix ``property:``).

Interchange ``node_type`` is ``"Result"``; ``id`` is the dotted class path. (Legacy facet rows may still use the string ``result_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResult]   (``TResult`` bound to ``BaseResult``)
              │
              v
    ResultGraphNode(...)  ──>  frozen ``BaseGraphNode`` + ``FieldGraphNode`` / ``PropertyFieldGraphNode`` companions + edges
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.introspection_tools import TypeIntrospection
from action_machine.model.base_result import BaseResult
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import COMPOSITION

from .field_graph_node import FieldGraphNode
from .property_field_graph_node import PropertyFieldGraphNode

TResult = TypeVar("TResult", bound=BaseResult)


@dataclass(init=False, frozen=True)
class ResultGraphNode(BaseGraphNode[type[TResult]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseResult`` result host class.
    CONTRACT: Built from ``type[TResult]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label;
    empty ``properties``; ``edges`` / :attr:`companion_nodes` from ``model_fields`` and ``model_computed_fields``
    (see :meth:`_field_graph_nodes_for_result`, :meth:`_property_field_graph_nodes_for_result`).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Result"

    def __init__(self, result_cls: type[TResult]) -> None:
        fields = ResultGraphNode._field_graph_nodes_for_result(result_cls)
        prop_fields = ResultGraphNode._property_field_graph_nodes_for_result(result_cls)
        result_node_id = TypeIntrospection.full_qualname(result_cls)
        edges = [
            *ResultGraphNode._composition_edges_to_fields(result_cls, result_node_id, fields),
            *ResultGraphNode._composition_edges_to_property_fields(result_cls, result_node_id, prop_fields),
        ]
        super().__init__(
            node_id=result_node_id,
            node_type=ResultGraphNode.NODE_TYPE,
            label=result_cls.__name__,
            properties={},
            edges=edges,
            node_obj=result_cls,
            companion_nodes=[*fields, *prop_fields],
        )

    @staticmethod
    def _field_graph_nodes_for_result(result_cls: type[BaseResult]) -> list[FieldGraphNode]:
        """One :class:`FieldGraphNode` per entry in ``result_cls.model_fields`` (empty when none)."""
        model_fields = getattr(result_cls, "model_fields", None)
        if not isinstance(model_fields, Mapping):
            return []
        out: list[FieldGraphNode] = []
        for field_name, finfo in model_fields.items():
            out.append(
                FieldGraphNode(
                    result_cls,
                    field_name,
                    description=finfo.description,
                    required=bool(finfo.is_required()),
                ),
            )
        return out

    @staticmethod
    def _composition_edges_to_fields(
        result_cls: type[BaseResult],
        result_node_id: str,
        fields: list[FieldGraphNode],
    ) -> list[BaseGraphEdge]:
        return [
            BaseGraphEdge(
                edge_name=f"field:{fd.node_obj.field_name.strip() or '_'}",
                is_dag=False,
                source_node_id=result_node_id,
                source_node_type=ResultGraphNode.NODE_TYPE,
                source_node_obj=result_cls,
                target_node_id=fd.node_id,
                target_node_type=FieldGraphNode.NODE_TYPE,
                target_node_obj=fd.node_obj,
                edge_relationship=COMPOSITION,
            )
            for fd in fields
        ]

    @staticmethod
    def _property_field_graph_nodes_for_result(
        result_cls: type[BaseResult],
    ) -> list[PropertyFieldGraphNode]:
        """One :class:`PropertyFieldGraphNode` per Pydantic computed field and per plain ``property`` on the class."""
        out: list[PropertyFieldGraphNode] = []
        seen: set[str] = set()

        model_fields = getattr(result_cls, "model_fields", None)
        model_field_names = set(model_fields) if isinstance(model_fields, Mapping) else set()

        model_computed_fields = getattr(result_cls, "model_computed_fields", None)
        if isinstance(model_computed_fields, Mapping):
            for prop_name, _ in model_computed_fields.items():
                seen.add(prop_name)
                out.append(
                    PropertyFieldGraphNode(
                        result_cls,
                        prop_name,
                        required=False,
                    ),
                )

        prop_members = TypeIntrospection.property_members(result_cls)
        for prop_name in sorted(prop_members):
            if prop_name in seen or prop_name in model_field_names:
                continue
            seen.add(prop_name)
            out.append(
                PropertyFieldGraphNode(
                    result_cls,
                    prop_name,
                    required=False,
                ),
            )
        return out

    @staticmethod
    def _composition_edges_to_property_fields(
        result_cls: type[BaseResult],
        result_node_id: str,
        props: list[PropertyFieldGraphNode],
    ) -> list[BaseGraphEdge]:
        return [
            BaseGraphEdge(
                edge_name=f"property:{p.node_obj.property_name.strip() or '_'}",
                is_dag=False,
                source_node_id=result_node_id,
                source_node_type=ResultGraphNode.NODE_TYPE,
                source_node_obj=result_cls,
                target_node_id=p.node_id,
                target_node_type=PropertyFieldGraphNode.NODE_TYPE,
                target_node_obj=p.node_obj,
                edge_relationship=COMPOSITION,
            )
            for p in props
        ]

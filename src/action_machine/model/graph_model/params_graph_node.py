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

Interchange ``node_type`` is ``"Params"``; ``id`` is the dotted class path. (Legacy facet rows may still use the string ``params_schema``.)

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TParams]   (``TParams`` bound to ``BaseParams``)
              │
              v
    ParamsGraphNode(...)  ──>  frozen ``BaseGraphNode`` + ``FieldGraphNode`` companions + edges
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar, TypeVar

from action_machine.model.base_params import BaseParams
from action_machine.introspection_tools import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import COMPOSITION

from .field_graph_node import FieldGraphNode

TParams = TypeVar("TParams", bound=BaseParams)


@dataclass(init=False, frozen=True)
class ParamsGraphNode(BaseGraphNode[type[TParams]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a ``BaseParams`` params host class.
    CONTRACT: Built from ``type[TParams]``; :attr:`NODE_TYPE` for ``node_type``; dotted ``id``, ``__name__`` label;
    empty ``properties``; ``edges`` / :attr:`companion_nodes` from ``model_fields`` (see :meth:`_field_graph_nodes_for_params`).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Params"

    def __init__(self, params_cls: type[TParams]) -> None:
        fields = ParamsGraphNode._field_graph_nodes_for_params(params_cls)
        params_node_id = TypeIntrospection.full_qualname(params_cls)
        edges = ParamsGraphNode._composition_edges_to_fields(params_cls, params_node_id, fields)
        super().__init__(
            node_id=params_node_id,
            node_type=ParamsGraphNode.NODE_TYPE,
            label=params_cls.__name__,
            properties={},
            edges=edges,
            node_obj=params_cls,
            companion_nodes=list(fields),
        )

    @staticmethod
    def _field_graph_nodes_for_params(params_cls: type[BaseParams]) -> list[FieldGraphNode]:
        """One :class:`FieldGraphNode` per entry in ``params_cls.model_fields`` (empty when none)."""
        model_fields = getattr(params_cls, "model_fields", None)
        if not isinstance(model_fields, Mapping):
            return []
        out: list[FieldGraphNode] = []
        for field_name, finfo in model_fields.items():
            out.append(
                FieldGraphNode(
                    params_cls,
                    field_name,
                    description=finfo.description,
                    required=bool(finfo.is_required()),
                ),
            )
        return out

    @staticmethod
    def _composition_edges_to_fields(
        params_cls: type[BaseParams],
        params_node_id: str,
        fields: list[FieldGraphNode],
    ) -> list[BaseGraphEdge]:
        return [
            BaseGraphEdge(
                edge_name=f"field:{fd.node_obj.field_name.strip() or '_'}",
                is_dag=False,
                source_node_id=params_node_id,
                source_node_type=ParamsGraphNode.NODE_TYPE,
                source_node_obj=params_cls,
                target_node_id=fd.node_id,
                target_node_type=FieldGraphNode.NODE_TYPE,
                target_node_obj=fd.node_obj,
                edge_relationship=COMPOSITION,
            )
            for fd in fields
        ]

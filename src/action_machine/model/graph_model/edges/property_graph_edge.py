# src/action_machine/model/graph_model/edges/property_graph_edge.py
"""
PropertyGraphEdge — COMPOSITION from Params → PropertyField interchange vertex.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Mirror params-schema computed / plain-property companions: composition with
``edge_name`` ``property:{name}`` from a params vertex to a
:class:`~action_machine.model.graph_model.property_field_graph_node.PropertyFieldGraphNode`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Params (source id + type)  ──{property:`name`}──►  PropertyFieldGraphNode
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from action_machine.model.base_params import BaseParams
from action_machine.model.graph_model.params_graph_node import ParamsGraphNode
from action_machine.model.graph_model.property_field_graph_node import PropertyFieldGraphNode
from action_machine.system_core import TypeIntrospection
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge


class PropertyGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
    ROLE: Typed composition edge Params host → property-field vertex.
    CONTRACT: ``edge_name`` ``property:`` + stripped property name (``_`` when empty); ``is_dag`` False; ``target_node`` is the ``PropertyFieldGraphNode``.
    INVARIANTS: Frozen via ``CompositionGraphEdge``.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        params_node_id: str,
        params_node_type: str,
        property_node: PropertyFieldGraphNode,
        source_node: BaseGraphNode[Any] | None = None,
    ) -> None:
        super().__init__(
            edge_name="property",
            is_dag=False,
            source_node_id=params_node_id,
            source_node_type=params_node_type,
            source_node=source_node,
            target_node_id=property_node.node_id,
            target_node_type=property_node.node_type,
            target_node=property_node,
        )

    @classmethod
    def for_params(
        cls,
        params_cls: type[BaseParams],
        params_node_id: str,
    ) -> list[PropertyGraphEdge]:
        """Build composition edges from params node to computed/plain property nodes."""
        props = cls._property_graph_nodes_for_params(params_cls)
        return [
            cls(
                params_node_id=params_node_id,
                params_node_type=ParamsGraphNode.NODE_TYPE,
                property_node=p,
            )
            for p in props
        ]

    @classmethod
    def _property_graph_nodes_for_params(
        cls,
        params_cls: type[BaseParams],
    ) -> list[PropertyFieldGraphNode]:
        """One :class:`PropertyFieldGraphNode` per Pydantic computed field and per plain ``property`` on the class."""
        out: list[PropertyFieldGraphNode] = []
        seen: set[str] = set()

        model_fields = getattr(params_cls, "model_fields", None)
        model_field_names = set(model_fields) if isinstance(model_fields, Mapping) else set()

        model_computed_fields = getattr(params_cls, "model_computed_fields", None)
        if isinstance(model_computed_fields, Mapping):
            for prop_name, _ in model_computed_fields.items():
                seen.add(prop_name)
                out.append(
                    PropertyFieldGraphNode(
                        params_cls,
                        prop_name,
                        required=False,
                    ),
                )

        prop_members = TypeIntrospection.property_members(params_cls)
        for prop_name in sorted(prop_members):
            if prop_name in seen or prop_name in model_field_names:
                continue
            seen.add(prop_name)
            out.append(
                PropertyFieldGraphNode(
                    params_cls,
                    prop_name,
                    required=False,
                ),
            )
        return out

# src/action_machine/model/graph_model/action_graph_node.py
"""
ActionGraphNode — interchange node for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from
an action **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TAction]   (``TAction`` bound to ``BaseAction``)
              │
              v
    ``BaseAction[P, R]``  →  ``ActionSchemaIntentResolver``

    ``_depends_info`` (``@depends``)  →  ``depends_edges``

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.intents.connection.connection_intent_resolver import (
    ConnectionIntentResolver,
)
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.introspection_tools import TypeIntrospection
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode
from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge

from .callable_graph_node_locator import CallableGraphNodeLocator
from .params_graph_node import ParamsGraphNode
from .result_graph_node import ResultGraphNode

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionGraphNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: Materializes action metadata and every outgoing edge into explicit fields; ``get_all_edges`` returns the composed edge list.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"
    domain_edge: AssociationGraphEdge | None = field(init=False, repr=False, compare=False)
    params_edge: AggregationGraphEdge | None = field(init=False, repr=False, compare=False)
    result_edge: AggregationGraphEdge | None = field(init=False, repr=False, compare=False)
    depends_edges: list[AssociationGraphEdge]
    connection_edges: list[AssociationGraphEdge]
    regular_aspect_edges: list[CompositionGraphEdge]
    summary_aspect_edges: list[CompositionGraphEdge]
    compensator_graph_edges: list[CompositionGraphEdge]
    error_handler_graph_edges: list[CompositionGraphEdge]

    def __init__(self, action_cls: type[TAction]) -> None:
        node_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=node_id,
            node_type=ActionGraphNode.NODE_TYPE,
            label=action_cls.__name__,
            properties=dict(ActionGraphNode._get_properties(action_cls)),
            edges=[],
            node_obj=action_cls,
        )
        domain_edge = self._get_domain_edge(action_cls)
        depends_edges = self._get_depends_edges(action_cls)
        connection_edges = self._get_connection_edges(action_cls)
        params_edge = self._get_params_edge(action_cls)
        result_edge = self._get_result_edge(action_cls)
        regular_aspect_edges = CallableGraphNodeLocator.get_regular_aspect_edges(self, action_cls)
        summary_aspect_edges = CallableGraphNodeLocator.get_summary_aspect_edges(self, action_cls)
        compensator_graph_edges = CallableGraphNodeLocator.get_compensator_edges(self, action_cls)
        error_handler_graph_edges = CallableGraphNodeLocator.get_error_handler_edges(self, action_cls)
        object.__setattr__(self, "domain_edge", domain_edge[0] if domain_edge else None)
        object.__setattr__(self, "params_edge", params_edge[0] if params_edge else None)
        object.__setattr__(self, "result_edge", result_edge[0] if result_edge else None)
        object.__setattr__(self, "depends_edges", depends_edges)
        object.__setattr__(self, "connection_edges", connection_edges)
        object.__setattr__(self, "regular_aspect_edges", regular_aspect_edges)
        object.__setattr__(self, "summary_aspect_edges", summary_aspect_edges)
        object.__setattr__(self, "compensator_graph_edges", compensator_graph_edges)
        object.__setattr__(self, "error_handler_graph_edges", error_handler_graph_edges)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        edges: list[BaseGraphEdge] = []
        if self.domain_edge is not None:
            edges.append(self.domain_edge)
        edges.extend(self.depends_edges)
        edges.extend(self.connection_edges)
        edges.extend(self.regular_aspect_edges)
        edges.extend(self.summary_aspect_edges)
        edges.extend(self.compensator_graph_edges)
        edges.extend(self.error_handler_graph_edges)
        if self.params_edge is not None:
            edges.append(self.params_edge)
        if self.result_edge is not None:
            edges.append(self.result_edge)
        return edges

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        nodes: list[BaseGraphNode[Any]] = []
        for edge in (
            *self.regular_aspect_edges,
            *self.summary_aspect_edges,
            *self.compensator_graph_edges,
            *self.error_handler_graph_edges,
        ):
            if edge.target_node is not None:
                nodes.append(edge.target_node)
        return nodes

    @classmethod
    def _get_properties(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = MetaIntentResolver.resolve_description(action_cls)
        if desc is not None:
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def _resolve_target_node_type(cls, target_cls: type) -> str:
        """Interchange ``target_node_type`` for an associated target class."""
        if issubclass(target_cls, BaseAction):
            return cls.NODE_TYPE
        if issubclass(target_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"

    def _get_domain_edge(
        self,
        action_cls: type[TAction],
    ) -> list[AssociationGraphEdge]:
        """Zero or one domain edge; empty when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        return [
            AssociationGraphEdge(
                edge_name="domain",
                is_dag=True,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                target_node=None,
            )
            for domain_cls in [MetaIntentResolver.resolve_domain_type(action_cls)]
            if domain_cls is not None
        ]

    def _get_depends_edges(
        self,
        action_cls: type[TAction],
    ) -> list[AssociationGraphEdge]:
        """One ``ASSOCIATION`` edge per ``@depends`` declaration from this action to the declared class."""
        action_id = TypeIntrospection.full_qualname(action_cls)
        return [
            AssociationGraphEdge(
                edge_name=dependency_type.__name__,
                is_dag=True,
                source_node_id=action_id,
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(dependency_type),
                target_node_type=self._resolve_target_node_type(dependency_type),
                target_node=None,
            )
            for dependency_type in DependsIntentResolver.resolve_dependency_types(action_cls)
        ]

    def _get_connection_edges(
        self,
        action_cls: type[TAction],
    ) -> list[AssociationGraphEdge]:
        """One ``ASSOCIATION`` edge per ``@connection`` declaration from this action to the resource class."""
        action_id = TypeIntrospection.full_qualname(action_cls)
        return [
            AssociationGraphEdge(
                edge_name=connection_type.__name__,
                is_dag=True,
                source_node_id=action_id,
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(connection_type),
                target_node_type=self._resolve_target_node_type(connection_type),
                target_node=None,
            )
            for connection_type in ConnectionIntentResolver.resolve_connection_types(action_cls)
        ]

    def _get_params_edge(
        self,
        action_cls: type[TAction],
    ) -> list[AggregationGraphEdge]:
        """Zero or one params schema edge (``AGGREGATION``); empty when the params type does not resolve."""
        params_type = ActionSchemaIntentResolver.resolve_params_type(action_cls)
        if params_type is None:
            return []
        return [
            AggregationGraphEdge(
                edge_name="params",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(params_type),
                target_node_type=ParamsGraphNode.NODE_TYPE,
                target_node=None,
            ),
        ]

    def _get_result_edge(
        self,
        action_cls: type[TAction],
    ) -> list[AggregationGraphEdge]:
        """Zero or one result schema edge (``AGGREGATION``); empty when the result type does not resolve."""
        result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        if result_type is None:
            return []
        return [
            AggregationGraphEdge(
                edge_name="result",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(result_type),
                target_node_type=ResultGraphNode.NODE_TYPE,
                target_node=None,
            ),
        ]

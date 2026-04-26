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
    ``BaseAction[P, R]``  →  ``ActionSchemaIntentResolver`` (or :meth:`get_params_edge` / :meth:`get_result_edge`)

    ``_depends_info`` (``@depends``)  →  :meth:`get_depends_edges`

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.introspection_tools import IntentIntrospection, TypeIntrospection
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge
from graph.edge_relationship import AGGREGATION, ASSOCIATION

from .aspect_graph_node_locator import AspectGraphNodeLocator
from .compensator_graph_node_locator import CompensatorGraphNodeLocator
from .error_handler_graph_node_locator import ErrorHandlerGraphNodeLocator
from .params_graph_node import ParamsGraphNode
from .result_graph_node import ResultGraphNode
from .summary_aspect_graph_node_locator import SummaryAspectGraphNodeLocator

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionGraphNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: ``get_properties``; ``get_domain_edge`` / ``get_depends_edges`` / ``get_connection_edges`` / ``get_params_edge`` / ``get_result_edge`` each return ``list[BaseGraphEdge]``. Own-class ``@regular_aspect`` / ``@summary_aspect`` / ``@compensate`` / ``@on_error`` composition edges are stored in dedicated fields and appended to ``edges``.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"
    params_edge: BaseGraphEdge | None = field(init=False, repr=False, compare=False)
    result_edge: BaseGraphEdge | None = field(init=False, repr=False, compare=False)
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
            properties=dict(ActionGraphNode.get_properties(action_cls)),
            edges=list(ActionGraphNode._get_all_edges(action_cls)),
            node_obj=action_cls,
        )
        params_edge = self.get_params_edge(action_cls)
        result_edge = self.get_result_edge(action_cls)
        regular_aspect_edges = self.get_composition_graph_eges(
            AspectGraphNodeLocator.locate(action_cls),
            node_id,
        )
        summary_aspect_edges = self.get_composition_graph_eges(
            SummaryAspectGraphNodeLocator.locate(action_cls),
            node_id,
        )
        compensator_graph_edges = self.get_composition_graph_eges(
            CompensatorGraphNodeLocator.locate(action_cls),
            node_id,
        )
        error_handler_graph_edges = self.get_composition_graph_eges(
            ErrorHandlerGraphNodeLocator.locate(action_cls),
            node_id,
        )
        object.__setattr__(self, "params_edge", params_edge[0] if params_edge else None)
        object.__setattr__(self, "result_edge", result_edge[0] if result_edge else None)
        object.__setattr__(self, "regular_aspect_edges", regular_aspect_edges)
        object.__setattr__(self, "summary_aspect_edges", summary_aspect_edges)
        object.__setattr__(self, "compensator_graph_edges", compensator_graph_edges)
        object.__setattr__(self, "error_handler_graph_edges", error_handler_graph_edges)
        object.__setattr__(
            self,
            "edges",
            [
                *self.get_all_edges(),
                *regular_aspect_edges,
                *summary_aspect_edges,
                *compensator_graph_edges,
                *error_handler_graph_edges,
                *params_edge,
                *result_edge,
            ],
        )

    @classmethod
    def _depends_target_node_type(cls, dep_cls: type) -> str:
        """Interchange ``target_node_type`` for a ``@depends`` dependency class."""
        if issubclass(dep_cls, BaseAction):
            return cls.NODE_TYPE
        if issubclass(dep_cls, BaseResource):
            return ResourceGraphNode.NODE_TYPE
        return "UncknownTypeNode"

    @classmethod
    def _association_edges_to_declared_types(
        cls,
        action_cls: type[TAction],
        declared_types: list[type],
    ) -> list[BaseGraphEdge]:
        action_id = TypeIntrospection.full_qualname(action_cls)
        edges: list[BaseGraphEdge] = []
        for target_cls in declared_types:
            edges.append(
                BaseGraphEdge(
                    edge_name=target_cls.__name__,
                    is_dag=True,
                    source_node_id=action_id,
                    source_node_type=cls.NODE_TYPE,
                    target_node_id=TypeIntrospection.full_qualname(target_cls),
                    target_node_type=cls._depends_target_node_type(target_cls),
                    edge_relationship=ASSOCIATION,
                ),
            )
        return edges

    def get_params_edge(
        self,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one params schema edge (``AGGREGATION``); empty when the params type does not resolve."""
        params_type = ActionSchemaIntentResolver.resolve_params_type(action_cls)
        if params_type is None:
            return []
        return [
            BaseGraphEdge(
                edge_name="params",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(params_type),
                target_node_type=ParamsGraphNode.NODE_TYPE,
                target_node=None,
                edge_relationship=AGGREGATION,
            ),
        ]

    def get_result_edge(
        self,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one result schema edge (``AGGREGATION``); empty when the result type does not resolve."""
        result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
        if result_type is None:
            return []
        return [
            BaseGraphEdge(
                edge_name="result",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(result_type),
                target_node_type=ResultGraphNode.NODE_TYPE,
                target_node=None,
                edge_relationship=AGGREGATION,
            ),
        ]

    def get_composition_graph_eges(
        self,
        graph_nodes: list[BaseGraphNode[Any]],
        action_id: str,
    ) -> list[CompositionGraphEdge]:
        """Return ``COMPOSITION`` edges from the action to the given graph nodes."""
        edges: list[CompositionGraphEdge] = []
        for aspect_node in graph_nodes:
            edges.append(
                CompositionGraphEdge(
                    edge_name=aspect_node.label,
                    is_dag=False,
                    source_node_id=action_id,
                    source_node_type=self.NODE_TYPE,
                    source_node=self,
                    target_node_id=aspect_node.node_id,
                    target_node_type=aspect_node.node_type,
                    target_node=aspect_node,
                ),
            )
        return edges

    @classmethod
    def get_domain_edge(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """Zero or one domain edge; empty when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        meta_info_dict = IntentIntrospection.meta_info_dict(action_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return []
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return []
        return [
            BaseGraphEdge(
                edge_name="domain",
                is_dag=True,
                source_node_id=TypeIntrospection.full_qualname(action_cls),
                source_node_type=cls.NODE_TYPE,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                edge_relationship=ASSOCIATION,
            ),
        ]

    @classmethod
    def get_depends_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``ASSOCIATION`` edge per ``@depends`` declaration from this action to the declared class.

        Uses :meth:`~action_machine.introspection_tools.intent_introspection.IntentIntrospection.depends_declared_types`.
        """
        return cls._association_edges_to_declared_types(
            action_cls,
            IntentIntrospection.depends_declared_types(action_cls),
        )

    @classmethod
    def get_connection_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        """
        One ``ASSOCIATION`` edge per ``@connection`` declaration from this action to the resource class.

        Uses :meth:`~action_machine.introspection_tools.intent_introspection.IntentIntrospection.connection_declared_types`.
        """
        return cls._association_edges_to_declared_types(
            action_cls,
            IntentIntrospection.connection_declared_types(action_cls),
        )

    @classmethod
    def get_properties(cls, action_cls: type[TAction]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = IntentIntrospection.meta_info_dict(action_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def _get_all_edges(
        cls,
        action_cls: type[TAction],
    ) -> list[BaseGraphEdge]:
        return (
            cls.get_domain_edge(action_cls)
            + cls.get_depends_edges(action_cls)
            + cls.get_connection_edges(action_cls)
        )

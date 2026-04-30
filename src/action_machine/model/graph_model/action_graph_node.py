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
from typing import Any, ClassVar, TypeVar, cast

from action_machine.domain.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.intents.action_schema.action_schema_intent_resolver import (
    ActionSchemaIntentResolver,
)
from action_machine.intents.aspects.regular_aspect_intent_resolver import (
    RegularAspectIntentResolver,
)
from action_machine.intents.aspects.summary_aspect_intent_resolver import (
    SummaryAspectIntentResolver,
)
from action_machine.intents.compensate.compensate_intent_resolver import (
    CompensateIntentResolver,
)
from action_machine.intents.connection.connection_intent_resolver import (
    ConnectionIntentResolver,
)
from action_machine.intents.depends.depends_intent_resolver import DependsIntentResolver
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.intents.on_error.on_error_intent_resolver import (
    OnErrorIntentResolver,
)
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.resources.graph_model.resource_graph_node import ResourceGraphNode
from action_machine.system_core import TypeIntrospection
from graph.aggregation_graph_edge import AggregationGraphEdge
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.composition_graph_edge import CompositionGraphEdge

from .compensator_graph_node import CompensatorGraphNode
from .edges.params_graph_edge import ParamsGraphEdge
from .error_handler_graph_node import ErrorHandlerGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .result_graph_node import ResultGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode

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
    domain_edge: DomainGraphEdge = field(init=False, repr=False, compare=False)
    params_edge: ParamsGraphEdge = field(init=False, repr=False, compare=False)
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
            node_obj=action_cls,
        )
        domain_edge = DomainGraphEdge(action_cls, self.NODE_TYPE, self)
        depends_edges = self._get_depends_edges(action_cls)
        connection_edges = self._get_connection_edges(action_cls)
        params_edge = ParamsGraphEdge(action_cls, self.NODE_TYPE, self)
        result_edge = self._get_result_edge(action_cls)
        regular_aspect_edges = ActionGraphNode.get_regular_aspect_edges(self, action_cls)
        summary_aspect_edges = ActionGraphNode.get_summary_aspect_edges(self, action_cls)
        compensator_graph_edges = ActionGraphNode.get_compensator_edges(self, action_cls)
        error_handler_graph_edges = ActionGraphNode.get_error_handler_edges(self, action_cls)
        object.__setattr__(self, "domain_edge", domain_edge)
        object.__setattr__(self, "params_edge", params_edge)
        object.__setattr__(self, "result_edge", result_edge[0] if result_edge else None)
        object.__setattr__(self, "depends_edges", depends_edges)
        object.__setattr__(self, "connection_edges", connection_edges)
        object.__setattr__(self, "regular_aspect_edges", regular_aspect_edges)
        object.__setattr__(self, "summary_aspect_edges", summary_aspect_edges)
        object.__setattr__(self, "compensator_graph_edges", compensator_graph_edges)
        object.__setattr__(self, "error_handler_graph_edges", error_handler_graph_edges)

    @property
    def connection_keys(self) -> frozenset[str]:
        """Declared ``@connection`` slot keys (non-empty stripped ``properties[\"key\"]`` on connection edges)."""
        keys: set[str] = set()
        for edge in self.connection_edges:
            raw = edge.properties.get("key")
            if isinstance(raw, str) and raw.strip():
                keys.add(raw.strip())
        return frozenset(keys)

    def get_regular_aspect_graph_nodes(self) -> list[RegularAspectGraphNode]:
        """Interchange vertices for ``@regular_aspect`` methods, in composition edge order."""
        out: list[RegularAspectGraphNode] = []
        for edge in self.regular_aspect_edges:
            if edge.target_node is None:
                continue
            out.append(cast(RegularAspectGraphNode, edge.target_node))
        return out

    def get_summary_aspect_graph_node(self) -> SummaryAspectGraphNode | None:
        """Interchange vertex for ``@summary_aspect`` if declared; at most one."""
        for edge in self.summary_aspect_edges:
            if edge.target_node is None:
                continue
            return cast(SummaryAspectGraphNode, edge.target_node)
        return None

    def get_compensator_graph_nodes(self) -> list[CompensatorGraphNode]:
        """Interchange vertices for ``@compensate`` methods, in composition edge order."""
        out: list[CompensatorGraphNode] = []
        for edge in self.compensator_graph_edges:
            if edge.target_node is None:
                continue
            out.append(cast(CompensatorGraphNode, edge.target_node))
        return out

    def compensator_graph_node_for_aspect(
        self,
        aspect_name: str,
    ) -> CompensatorGraphNode | None:
        """Optional compensator for ``aspect_name``; at most one compensator references a regular aspect."""
        needle = aspect_name.strip()
        for node in self.get_compensator_graph_nodes():
            raw = node.properties.get("target_aspect_name")
            if isinstance(raw, str) and raw.strip() == needle:
                return node
        return None

    def get_error_handler_graph_nodes(self) -> list[ErrorHandlerGraphNode]:
        """Interchange vertices for ``@on_error`` methods, in composition edge order."""
        out: list[ErrorHandlerGraphNode] = []
        for edge in self.error_handler_graph_edges:
            if edge.target_node is None:
                continue
            out.append(cast(ErrorHandlerGraphNode, edge.target_node))
        return out

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return [
            self.domain_edge,
            self.params_edge,
            *([] if self.result_edge is None else [self.result_edge]),
            *self.depends_edges,
            *self.connection_edges,
            *self.regular_aspect_edges,
            *self.summary_aspect_edges,
            *self.compensator_graph_edges,
            *self.error_handler_graph_edges,
        ]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        summary = self.get_summary_aspect_graph_node()
        regular = self.get_regular_aspect_graph_nodes()
        compensators = self.get_compensator_graph_nodes()
        error_handlers = self.get_error_handler_graph_nodes()
        return [
            *(cast(BaseGraphNode[Any], n) for n in regular),
            *((cast(BaseGraphNode[Any], summary),) if summary is not None else ()),
            *(cast(BaseGraphNode[Any], n) for n in compensators),
            *(cast(BaseGraphNode[Any], n) for n in error_handlers),
            *(node for n in regular for node in n.get_companion_nodes()),
            *(summary.get_companion_nodes() if summary is not None else []),
            *(node for n in compensators for node in n.get_companion_nodes()),
            *(node for n in error_handlers for node in n.get_companion_nodes()),
        ]

    @staticmethod
    def get_regular_aspect_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return regular aspect composition edges for ``action_cls``."""
        return ActionGraphNode._get_callable_edges(
            source_node,
            [
                RegularAspectGraphNode(aspect_callable, action_cls)
                for aspect_callable in RegularAspectIntentResolver.resolve_regular_aspects(action_cls)
            ],
        )

    @staticmethod
    def get_summary_aspect_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return summary aspect composition edges for ``action_cls``."""
        return ActionGraphNode._get_callable_edges(
            source_node,
            [
                SummaryAspectGraphNode(aspect_callable, action_cls)
                for aspect_callable in SummaryAspectIntentResolver.resolve_summary_aspects(action_cls)
            ],
        )

    @staticmethod
    def get_compensator_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return compensator composition edges for ``action_cls``."""
        return ActionGraphNode._get_callable_edges(
            source_node,
            [
                CompensatorGraphNode(compensator_callable, action_cls)
                for compensator_callable in CompensateIntentResolver.resolve_compensators(action_cls)
            ],
        )

    @staticmethod
    def get_error_handler_edges(
        source_node: BaseGraphNode[Any],
        action_cls: type[BaseAction[Any, Any]],
    ) -> list[CompositionGraphEdge]:
        """Return error handler composition edges for ``action_cls``."""
        return ActionGraphNode._get_callable_edges(
            source_node,
            [
                ErrorHandlerGraphNode(error_handler_callable, action_cls)
                for error_handler_callable in OnErrorIntentResolver.resolve_error_handlers(action_cls)
            ],
        )

    @staticmethod
    def _get_callable_edges(
        source_node: BaseGraphNode[Any],
        graph_nodes: list[BaseGraphNode[Any]],
    ) -> list[CompositionGraphEdge]:
        """Return ``COMPOSITION`` edges from ``source_node`` to callable graph nodes."""
        edges: list[CompositionGraphEdge] = []
        for graph_node in graph_nodes:
            edges.append(
                CompositionGraphEdge(
                    edge_name=graph_node.label,
                    is_dag=False,
                    source_node_id=source_node.node_id,
                    source_node_type=source_node.node_type,
                    source_node=source_node,
                    target_node_id=graph_node.node_id,
                    target_node_type=graph_node.node_type,
                    target_node=graph_node,
                ),
            )
        return edges

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

    def _get_depends_edges(
        self,
        action_cls: type[TAction],
    ) -> list[AssociationGraphEdge]:
        """One ``ASSOCIATION`` edge per ``@depends`` declaration from this action to the declared class."""
        action_id = TypeIntrospection.full_qualname(action_cls)
        return [
            AssociationGraphEdge(
                edge_name="@depends",
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
        """One ``ASSOCIATION`` per ``@connection``; ``edge_name`` ``connection`` = role (from ``@connection``), not a unique id—use ``properties['key']`` and target to distinguish."""
        action_id = TypeIntrospection.full_qualname(action_cls)
        return [
            AssociationGraphEdge(
                edge_name="@connection",
                is_dag=True,
                source_node_id=action_id,
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(connection_type),
                target_node_type=self._resolve_target_node_type(connection_type),
                target_node=None,
                properties={"key": connection_key},
            )
            for connection_type, connection_key in ConnectionIntentResolver.resolve_connection_types_and_keys(
                action_cls,
            )
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

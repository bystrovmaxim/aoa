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

    ``_depends_info`` (``@depends``)  →  ``depends``

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from action_machine.domain.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.model.base_action import BaseAction
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

from .compensator_graph_node import CompensatorGraphNode
from .edges.compensator_graph_edge import CompensatorGraphEdge
from .edges.connection_graph_edge import ConnectionGraphEdge
from .edges.depends_graph_edge import DependsGraphEdge
from .edges.error_handler_graph_edge import ErrorHandlerGraphEdge
from .edges.params_graph_edge import ParamsGraphEdge
from .edges.regular_aspect_graph_edge import RegularAspectGraphEdge
from .edges.result_graph_edge import ResultGraphEdge
from .edges.summary_aspect_graph_edge import SummaryAspectGraphEdge
from .error_handler_graph_node import ErrorHandlerGraphNode
from .regular_aspect_graph_node import RegularAspectGraphNode
from .summary_aspect_graph_node import SummaryAspectGraphNode

TAction = TypeVar("TAction", bound=BaseAction[Any, Any])


@dataclass(init=False, frozen=True)
class ActionGraphNode(BaseGraphNode[type[TAction]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseAction`` host class.
    CONTRACT: Materializes action metadata and every outgoing edge into explicit fields; ``get_all_edges`` returns the composed edge list.
    FAILURES: :exc:`~action_machine.exceptions.MissingMetaError` propagates from :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description` or :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_domain_type` (via ``DomainGraphEdge``) when ``@meta`` data is unusable.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    params: ParamsGraphEdge = field(init=False, repr=False, compare=False)
    result: ResultGraphEdge = field(init=False, repr=False, compare=False)
    depends: list[DependsGraphEdge]
    connection: list[ConnectionGraphEdge]
    regular_aspect: list[RegularAspectGraphEdge]
    summary_aspect: list[SummaryAspectGraphEdge]
    compensator_graph: list[CompensatorGraphEdge]
    error_handler_graph: list[ErrorHandlerGraphEdge]

    def __init__(self, action_cls: type[TAction]) -> None:
        node_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=node_id,
            node_type=ActionGraphNode.NODE_TYPE,
            label=action_cls.__name__,
            properties=dict({"description": MetaIntentResolver.resolve_description(action_cls)}),
            node_obj=action_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge(action_cls, self.NODE_TYPE, self))
        object.__setattr__(self, "params", ParamsGraphEdge(action_cls, self.NODE_TYPE, self))
        object.__setattr__(self, "result", ResultGraphEdge(action_cls, self.NODE_TYPE, self))
        object.__setattr__(self, "depends", DependsGraphEdge.edges_from_dependencies(self, action_cls))
        object.__setattr__(self, "connection", ConnectionGraphEdge.edges_from_connections(self, action_cls))
        object.__setattr__(self, "regular_aspect", RegularAspectGraphEdge.edges_from_regular_aspects(self, action_cls))
        object.__setattr__(self, "summary_aspect", SummaryAspectGraphEdge.edges_from_summary_aspects(self, action_cls))
        object.__setattr__(self, "compensator_graph", CompensatorGraphEdge.edges_from_compensators(self, action_cls))
        object.__setattr__(self, "error_handler_graph", ErrorHandlerGraphEdge.edges_from_error_handlers(self, action_cls))

    def connection_keys(self) -> frozenset[str]:
        """Declared ``@connection`` slot keys (non-empty stripped ``properties[\"key\"]`` on connection edges)."""
        keys: set[str] = set()
        for edge in self.connection:
            raw = edge.properties.get("key")
            if isinstance(raw, str) and raw.strip():
                keys.add(raw.strip())
        return frozenset(keys)

    def get_regular_aspect_graph_nodes(self) -> list[RegularAspectGraphNode]:
        """Interchange vertices for ``@regular_aspect`` methods, in composition edge order."""
        out: list[RegularAspectGraphNode] = []
        for edge in self.regular_aspect:
            if edge.target_node is None:
                continue
            out.append(cast(RegularAspectGraphNode, edge.target_node))
        return out

    def get_summary_aspect_graph_node(self) -> SummaryAspectGraphNode | None:
        """Interchange vertex for ``@summary_aspect`` if declared; at most one."""
        for edge in self.summary_aspect:
            if edge.target_node is None:
                continue
            return cast(SummaryAspectGraphNode, edge.target_node)
        return None

    def get_compensator_graph_nodes(self) -> list[CompensatorGraphNode]:
        """Interchange vertices for ``@compensate`` methods, in composition edge order."""
        out: list[CompensatorGraphNode] = []
        for edge in self.compensator_graph:
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
        for edge in self.error_handler_graph:
            if edge.target_node is None:
                continue
            out.append(cast(ErrorHandlerGraphNode, edge.target_node))
        return out

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return [
            self.domain,
            self.params,
            self.result,
            *self.depends,
            *self.connection,
            *self.regular_aspect,
            *self.summary_aspect,
            *self.compensator_graph,
            *self.error_handler_graph,
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

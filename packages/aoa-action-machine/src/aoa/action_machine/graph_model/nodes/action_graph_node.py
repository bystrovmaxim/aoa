# packages/aoa-action-machine/src/aoa/action_machine/graph_model/nodes/action_graph_node.py
"""
ActionGraphNode — interchange node for ``BaseAction`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~aoa.graph.base_graph_node.BaseGraphNode` view derived from
an action **class** object. Interchange data lives in ``id``, ``node_type``,
``label``, ``properties``, and ``edges``; the class is :attr:`~aoa.graph.base_graph_node.BaseGraphNode.node_obj`.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TAction]   (``TAction`` bound to ``BaseAction``)
              │
              v
    ``BaseAction[P, R]``  →  ``ActionSchemaIntentResolver``

    ``_depends_info`` (``@depends``)  →  ``depends``

    ``DependsGraphEdge`` targets (after coordinator wiring)  →  ``resolved_dependency_infos`` for ``DependencyFactory``

    ActionGraphNode ``__init__`` / helpers  →  frozen ``BaseGraphNode``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from aoa.action_machine.exceptions.missing_summary_aspect_error import MissingSummaryAspectError
from aoa.action_machine.graph_model.edges.domain_graph_edge import DomainGraphEdge
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.runtime.dependency_info import DependencyInfo
from aoa.action_machine.system_core.type_introspection import TypeIntrospection
from aoa.graph.base_graph_edge import BaseGraphEdge
from aoa.graph.base_graph_node import BaseGraphNode

from ..edges.compensator_graph_edge import CompensatorGraphEdge
from ..edges.connection_graph_edge import ConnectionGraphEdge
from ..edges.depends_graph_edge import DependsGraphEdge
from ..edges.error_handler_graph_edge import ErrorHandlerGraphEdge
from ..edges.params_graph_edge import ParamsGraphEdge
from ..edges.regular_aspect_graph_edge import RegularAspectGraphEdge
from ..edges.result_graph_edge import ResultGraphEdge
from ..edges.role_graph_edge import RoleGraphEdge
from ..edges.summary_aspect_graph_edge import SummaryAspectGraphEdge
from .compensator_graph_node import CompensatorGraphNode
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
    FAILURES: :exc:`~aoa.action_machine.exceptions.MissingMetaError` propagates from :meth:`~aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description` or :meth:`~aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_domain_type` (via ``DomainGraphEdge``) when ``@meta`` data is unusable. :exc:`~aoa.action_machine.exceptions.MissingCheckRolesError` when ``@check_roles`` did not set ``_role_info['spec']``. :meth:`get_summary_aspect_graph_node` raises :exc:`~aoa.action_machine.exceptions.MissingSummaryAspectError` when ``summary_aspect`` is empty.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Action"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    params: ParamsGraphEdge = field(init=False, repr=False, compare=False)
    result: ResultGraphEdge = field(init=False, repr=False, compare=False)
    depends: list[DependsGraphEdge]
    connection: list[ConnectionGraphEdge]
    roles: list[RoleGraphEdge]
    regular_aspect: list[RegularAspectGraphEdge]
    summary_aspect: list[SummaryAspectGraphEdge]
    compensators: list[CompensatorGraphEdge]
    on_error_handlers: list[ErrorHandlerGraphEdge]

    def __init__(self, action_cls: type[TAction]) -> None:
        node_id = TypeIntrospection.full_qualname(action_cls)
        super().__init__(
            node_id=node_id,
            node_type=ActionGraphNode.NODE_TYPE,
            label=action_cls.__name__,
            properties=dict({"description": MetaIntentResolver.resolve_description(action_cls)}),
            node_obj=action_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge.from_meta_declared_host(action_cls, self))
        object.__setattr__(self, "params", ParamsGraphEdge(action_cls))
        object.__setattr__(self, "result", ResultGraphEdge(action_cls))
        object.__setattr__(self, "depends", DependsGraphEdge.get_dependency_edges(action_cls))
        object.__setattr__(self, "connection", ConnectionGraphEdge.get_connection_edges(action_cls))
        object.__setattr__(self, "roles", RoleGraphEdge.get_role_edges(action_cls))
        object.__setattr__(self, "regular_aspect", RegularAspectGraphEdge.get_regular_aspect_edges(action_cls))
        object.__setattr__(self, "summary_aspect", SummaryAspectGraphEdge.get_summary_aspect_edges(action_cls))
        object.__setattr__(self, "compensators", CompensatorGraphEdge.get_compensator_edges(action_cls))
        object.__setattr__(self, "on_error_handlers", ErrorHandlerGraphEdge.get_on_error_handlers_edges(action_cls))

    def connection_keys(self) -> frozenset[str]:
        """Declared ``@connection`` slot keys (non-empty stripped ``properties[\"key\"]`` on connection edges)."""
        keys: set[str] = set()
        for edge in self.connection:
            raw = edge.properties.get("key")
            if isinstance(raw, str) and raw.strip():
                keys.add(raw.strip())
        return frozenset(keys)

    def resolved_dependency_infos(self) -> tuple[DependencyInfo, ...]:
        """Return dependency records from wired ``@depends`` edges (same order); empty tuple if none declared."""
        out: list[DependencyInfo] = []
        for edge in self.depends:
            target = edge.target_node
            if target is None:
                msg = (
                    f"@depends interchange edge to {edge.target_node_id!r} "
                    "is missing target_node — use coordinator-built interchange "
                    "(e.g. ActionProductMachine.get_action_node_by_id) before assembling ToolsBox."
                )
                raise RuntimeError(msg)
            host = target.node_obj
            if not isinstance(host, type):
                msg = f"@depends target {edge.target_node_id!r} must resolve to a host type, got {type(host).__name__!r}"
                raise TypeError(msg)
            raw_fac = edge.properties.get("factory")
            factory = raw_fac if raw_fac is None or callable(raw_fac) else None
            desc_raw = edge.properties.get("description", "")
            description = desc_raw if isinstance(desc_raw, str) else ""
            out.append(DependencyInfo(cls=host, factory=factory, description=description))
        return tuple(out)

    def get_regular_aspect_graph_nodes(self) -> list[RegularAspectGraphNode]:
        """Interchange vertices for ``@regular_aspect`` methods, in composition edge order."""
        out: list[RegularAspectGraphNode] = []
        for edge in self.regular_aspect:
            out.append(cast(RegularAspectGraphNode, edge.target_node))
        return out

    def get_summary_aspect_graph_node(self) -> SummaryAspectGraphNode:
        """Interchange graph node for ``@summary_aspect``; raises if the graph has no summary edges."""
        if not self.summary_aspect:
            action_name = getattr(self.node_obj, "__name__", "?")
            msg = (
                f"Action interchange {action_name!r} has no summary_aspect edges; "
                "this helper requires a declared @summary_aspect."
            )
            raise MissingSummaryAspectError(msg)
        return cast(SummaryAspectGraphNode, self.summary_aspect[0].target_node)

    def get_compensator_graph_nodes(self) -> list[CompensatorGraphNode]:
        """Interchange vertices for ``@compensate`` methods, in composition edge order."""
        out: list[CompensatorGraphNode] = []
        for edge in self.compensators:
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
        for edge in self.on_error_handlers:
            out.append(cast(ErrorHandlerGraphNode, edge.target_node))
        return out

    def get_all_edges(self) -> list[BaseGraphEdge]:
        return [
            self.domain,
            self.params,
            self.result,
            *self.depends,
            *self.connection,
            *self.roles,
            *self.regular_aspect,
            *self.summary_aspect,
            *self.compensators,
            *self.on_error_handlers,
        ]

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        summary = self.get_summary_aspect_graph_node() if self.summary_aspect else None
        regular = self.get_regular_aspect_graph_nodes()
        compensators = self.get_compensator_graph_nodes()
        error_handlers = self.get_error_handler_graph_nodes()
        return [
            *(cast(BaseGraphNode[Any], n) for n in regular),
            *((cast(BaseGraphNode[Any], summary),) if summary is not None else ()),
            *(cast(BaseGraphNode[Any], n) for n in compensators),
            *(cast(BaseGraphNode[Any], n) for n in error_handlers),
        ]

# src/action_machine/graph_model/nodes/resource_graph_node.py
"""
ResourceGraphNode — interchange node for ``BaseResource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from a
resource **class** (``type[BaseResource]``). Reads ``description`` and ``domain``
from ``@meta`` scratch (``_meta_info``), same contract as
:class:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode` for
those fields. ``node_id`` uses the dotted full qualname of the resource class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResource]   (``TResource`` bound to ``BaseResource``)
              │
              v
    ``@meta`` → ``_meta_info`` ``description`` / ``domain``
              │
              v
    ``ResourceGraphNode``  →  frozen ``BaseGraphNode`` + domain ``ASSOCIATION`` edge
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.graph_model.nodes.domain_graph_node import DomainGraphNode
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.resources.base_resource import BaseResource
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TResource = TypeVar("TResource", bound=BaseResource)


@dataclass(init=False, frozen=True)
class ResourceGraphNode(BaseGraphNode[type[TResource]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseResource`` host class.
    CONTRACT: ``_get_properties`` from :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description` ``description``; ``domain_edge`` is the ``ASSOCIATION`` edge to :class:`~action_machine.graph_model.nodes.domain_graph_node.DomainGraphNode` from :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_domain_type`.
    FAILURES: :exc:`~action_machine.exceptions.MissingMetaError` from ``resolve_description`` / ``resolve_domain_type`` when ``@meta`` scratch is absent or invalid.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Resource"
    domain_edge: AssociationGraphEdge = field(init=False, repr=False, compare=False)

    def __init__(self, resource_cls: type[TResource]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(resource_cls),
            node_type=ResourceGraphNode.NODE_TYPE,
            label=resource_cls.__name__,
            properties=dict(ResourceGraphNode._get_properties(resource_cls)),
            node_obj=resource_cls,
        )
        domain_edge = self._build_domain_edge(resource_cls)
        object.__setattr__(self, "domain_edge", domain_edge)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return resource relationship edges materialized in the explicit edge field."""
        return [self.domain_edge]

    @classmethod
    def _get_properties(cls, resource_cls: type[TResource]) -> dict[str, Any]:
        """``description`` from ``@meta(description=...)`` via :meth:`MetaIntentResolver.resolve_description`."""
        return {"description": MetaIntentResolver.resolve_description(resource_cls)}

    def _build_domain_edge(self, resource_cls: type[TResource]) -> AssociationGraphEdge:
        """``ASSOCIATION`` to the declared ``@meta`` domain vertex."""
        domain_cls = MetaIntentResolver.resolve_domain_type(resource_cls)
        return AssociationGraphEdge(
            edge_name="domain",
            is_dag=True,
            source_node_id=TypeIntrospection.full_qualname(resource_cls),
            source_node_type=self.NODE_TYPE,
            source_node=self,
            target_node_id=TypeIntrospection.full_qualname(domain_cls),
            target_node_type=DomainGraphNode.NODE_TYPE,
            target_node=None,
        )

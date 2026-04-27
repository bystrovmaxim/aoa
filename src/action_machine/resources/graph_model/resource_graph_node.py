# src/action_machine/resources/graph_model/resource_graph_node.py
"""
ResourceGraphNode — interchange node for ``BaseResource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~graph.base_graph_node.BaseGraphNode` view derived from a
resource **class** (``type[BaseResource]``). Reads ``description`` and ``domain``
from ``@meta`` scratch (``_meta_info``), same contract as
:class:`~action_machine.model.graph_model.action_graph_node.ActionGraphNode` for
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
    ``ResourceGraphNode``  →  frozen ``BaseGraphNode`` + optional domain ``ASSOCIATION`` edge
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.introspection_tools import TypeIntrospection
from action_machine.resources.base_resource import BaseResource
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TResource = TypeVar("TResource", bound=BaseResource)


@dataclass(init=False, frozen=True)
class ResourceGraphNode(BaseGraphNode[type[TResource]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseResource`` host class.
    CONTRACT: ``_get_properties`` from ``@meta`` ``description``; ``_get_domain_edge`` returns
    zero or one ``ASSOCIATION`` edge to :class:`~action_machine.domain.graph_model.domain_graph_node.DomainGraphNode` when ``domain`` is a ``BaseDomain`` subclass.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Resource"
    domain_edge: AssociationGraphEdge | None = field(init=False, repr=False, compare=False)

    def __init__(self, resource_cls: type[TResource]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(resource_cls),
            node_type=ResourceGraphNode.NODE_TYPE,
            label=resource_cls.__name__,
            properties=dict(ResourceGraphNode._get_properties(resource_cls)),
            node_obj=resource_cls,
        )
        domain_edge = self._get_domain_edge(resource_cls)
        object.__setattr__(self, "domain_edge", domain_edge[0] if domain_edge else None)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return resource relationship edges materialized in the explicit edge field."""
        return [
            *([] if self.domain_edge is None else [self.domain_edge]),
        ]

    @classmethod
    def _get_properties(cls, resource_cls: type[TResource]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = MetaIntentResolver.resolve_description(resource_cls)
        if desc is not None:
            properties["description"] = desc.strip()
        return properties

    def _get_domain_edge(
        self,
        resource_cls: type[TResource],
    ) -> list[AssociationGraphEdge]:
        """Zero or one domain edge; empty when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        return [
            AssociationGraphEdge(
                edge_name="domain",
                is_dag=True,
                source_node_id=TypeIntrospection.full_qualname(resource_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                target_node=None,
            )
            for domain_cls in [MetaIntentResolver.resolve_domain_type(resource_cls)]
            if domain_cls is not None
        ]

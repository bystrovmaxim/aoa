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

from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.graph_model.domain_graph_node import DomainGraphNode
from action_machine.introspection_tools import IntentIntrospection, TypeIntrospection
from action_machine.resources.base_resource import BaseResource
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import ASSOCIATION

TResource = TypeVar("TResource", bound=BaseResource)


@dataclass(init=False, frozen=True)
class ResourceGraphNode(BaseGraphNode[type[TResource]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseResource`` host class.
    CONTRACT: ``get_properties`` from ``@meta`` ``description``; ``get_domain_edge`` returns
    zero or one ``ASSOCIATION`` edge to :class:`~action_machine.domain.graph_model.domain_graph_node.DomainGraphNode` when ``domain`` is a ``BaseDomain`` subclass.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Resource"

    def __init__(self, resource_cls: type[TResource]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(resource_cls),
            node_type=ResourceGraphNode.NODE_TYPE,
            label=resource_cls.__name__,
            properties=dict(ResourceGraphNode.get_properties(resource_cls)),
            edges=list(ResourceGraphNode._get_all_edges(resource_cls)),
            node_obj=resource_cls,
        )

    @classmethod
    def get_domain_edge(
        cls,
        resource_cls: type[TResource],
    ) -> list[BaseGraphEdge]:
        """Zero or one domain edge; empty when ``@meta`` has no valid ``BaseDomain`` in ``domain``."""
        meta_info_dict = IntentIntrospection.meta_info_dict(resource_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return []
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return []
        return [
            BaseGraphEdge(
                edge_name="domain",
                is_dag=True,
                source_node_id=TypeIntrospection.full_qualname(resource_cls),
                source_node_type=cls.NODE_TYPE,
                source_node_obj=resource_cls,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                target_node_obj=domain_cls,
                edge_relationship=ASSOCIATION,
            ),
        ]

    @classmethod
    def get_properties(cls, resource_cls: type[TResource]) -> dict[str, Any]:
        """``description`` from ``_meta_info`` when ``@meta(description=...)`` is present."""
        properties: dict[str, Any] = {}
        desc = IntentIntrospection.meta_info_dict(resource_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def _get_all_edges(cls, resource_cls: type[TResource]) -> list[BaseGraphEdge]:
        return cls.get_domain_edge(resource_cls)

# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/resource_graph_node.py
"""
ResourceGraphNode — interchange node for ``BaseResource`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides a :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode` view derived from a
resource **class** (``type[BaseResource]``). Reads ``description`` from ``@meta`` scratch
(``_meta_info``), same contract as
:class:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode` for that field.
``node_id`` uses the dotted full qualname of the resource class.

A resource is a database: it has no domain of its own, so its node carries no ``domain``
edge. Its domains are the domains of the entities it lists with ``@entities``; this node
contributes one ``resource_entity`` edge to each of them.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TResource]   (``TResource`` bound to ``BaseResource``)
              │
              v
    ``@meta`` → ``_meta_info`` ``description``
    ``@entities`` → ``_entities_info`` ordered entity classes
              │
              v
    ``ResourceGraphNode``  →  frozen ``BaseGraphNode`` + one ``resource_entity`` edge per listed entity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.resource_entity_graph_edge import ResourceEntityGraphEdge
from aoa.action_machine.intents.entities.entities_intent_resolver import EntitiesIntentResolver
from aoa.action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TResource = TypeVar("TResource", bound=BaseResource)


@dataclass(init=False, frozen=True)
class ResourceGraphNode(BaseGraphNode[type[TResource]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange node for a concrete ``BaseResource`` host class.
    CONTRACT: ``properties["description"]`` from :meth:`~aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description`; :attr:`entities` lists one ``resource_entity`` aggregation edge per class ``@entities`` names — a resource is a database shared by domains, and it carries no ``domain`` edge.
    FAILURES: :exc:`~aoa.action_machine.exceptions.MissingMetaError` from ``resolve_description`` when ``@meta`` scratch is absent or invalid.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Resource"
    entities: list[ResourceEntityGraphEdge] = field(init=False, repr=False, compare=False)

    def __init__(self, resource_cls: type[TResource]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(resource_cls),
            node_type=ResourceGraphNode.NODE_TYPE,
            label=resource_cls.__name__,
            properties=dict({"description": MetaIntentResolver.resolve_description(resource_cls)}),
            node_obj=resource_cls,
        )
        object.__setattr__(
            self,
            "entities",
            [ResourceEntityGraphEdge(entity_cls) for entity_cls in EntitiesIntentResolver.resolve_entities(resource_cls)],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {
                "description": str(self.properties["description"]),
            },
        }

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return one ``resource_entity`` edge per class ``@entities`` lists; a resource has no ``domain`` edge."""
        return [*self.entities]

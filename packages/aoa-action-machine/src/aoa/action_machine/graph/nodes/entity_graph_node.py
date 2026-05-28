# packages/aoa-action-machine/src/aoa/action_machine/graph/nodes/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~aoa.action_machine.graph.core.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`~aoa.action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_description`,
a ``domain`` edge built by :class:`~aoa.action_machine.graph.edges.domain_graph_edge.DomainGraphEdge`,
``entity_relation`` edges from :class:`~aoa.action_machine.graph.edges.entity_graph_edge.EntityGraphEdge`,
:class:`~aoa.action_machine.graph.edges.lifecycle_graph_edge.LifeCycleGraphEdge`
lifecycle compositions (:attr:`lifecycles`), and ``entity_field`` compositions from
:meth:`~aoa.action_machine.graph.edges.entity_field_graph_edge.EntityFieldGraphEdge.get_entity_field_edges`
to :class:`~aoa.action_machine.graph.nodes.entity_field_graph_node.EntityFieldGraphNode`
for each scalar model field (see :attr:`entity_field_edges`).

State rows belong to each wired :class:`~aoa.action_machine.graph.nodes.lifecycle_graph_node.LifeCycleGraphNode`;
the entity row contributes lifecycle vertices only.

(``@entity`` ``domain``: :meth:`~aoa.action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_domain_type`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.base_graph_edge import BaseGraphEdge
from aoa.action_machine.graph.core.base_graph_node import BaseGraphNode
from aoa.action_machine.graph.edges.domain_graph_edge import DomainGraphEdge
from aoa.action_machine.graph.edges.entity_field_graph_edge import EntityFieldGraphEdge
from aoa.action_machine.graph.edges.entity_graph_edge import EntityGraphEdge
from aoa.action_machine.graph.edges.lifecycle_graph_edge import LifeCycleGraphEdge
from aoa.action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE`; :attr:`domain` / :attr:`relations` / :attr:`lifecycles` / :attr:`entity_field_edges` from scalar fields; :meth:`get_all_edges` lists domain, relations, lifecycle compositions, and ``entity_field`` edges; :meth:`get_companion_nodes` returns lifecycle targets and :class:`EntityFieldGraphNode` targets. JSON omits nested ``fields``/``field_order`` on the entity row.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge] = field(init=False)
    lifecycles: list[LifeCycleGraphEdge] = field(init=False)
    entity_field_edges: list[EntityFieldGraphEdge] = field(init=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        description = EntityIntentResolver.resolve_description(entity_cls)
        field_edges = EntityFieldGraphEdge.get_entity_field_edges(entity_cls)
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties={"description": description},
            node_obj=entity_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge.from_entity_declared_host(entity_cls, self))
        object.__setattr__(self, "relations", EntityGraphEdge.get_entity_relation_edges(entity_cls))
        object.__setattr__(self, "lifecycles", LifeCycleGraphEdge.get_lifecycle_edges(entity_cls))
        object.__setattr__(self, "entity_field_edges", field_edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "properties": {
                "description": str(self.properties["description"]),
            },
        }

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Lifecycle field targets and scalar ``EntityField`` vertices."""
        lifecycle_targets = [target for edge in self.lifecycles if (target := edge.target_node) is not None]
        field_targets = [edge.target_node for edge in self.entity_field_edges if edge.target_node is not None]
        return [*lifecycle_targets, *field_targets]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return ``domain``, entity relations, lifecycle compositions, and field compositions."""
        return [self.domain, *self.relations, *self.lifecycles, *self.entity_field_edges]

# src/action_machine/graph_model/nodes/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`~action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_description`,
a ``domain`` edge built by :class:`~action_machine.graph_model.edges.domain_graph_edge.DomainGraphEdge`,
``entity_relation`` edges from :class:`~action_machine.graph_model.edges.entity_graph_edge.EntityGraphEdge`,
:class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge`
lifecycle associations (:attr:`lifecycles`).

State rows belong to each wired :class:`~action_machine.graph_model.nodes.lifecycle_graph_node.LifeCycleGraphNode`;
the entity row contributes lifecycle vertices only.

(``@entity`` ``domain``: :meth:`~action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_domain_type`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TEntity]  (``TEntity`` bound to ``BaseEntity``)
              │
              v
    EntityGraphNode (``__init__``)
              ├─ :attr:`domain`     ← :class:`~action_machine.graph_model.edges.domain_graph_edge.DomainGraphEdge`
              ├─ :attr:`relations`  ← list[:class:`~action_machine.graph_model.edges.entity_graph_edge.EntityGraphEdge`]
              └─ :attr:`lifecycles` ← :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_association_edges`
              │
              v
    :meth:`get_all_edges` → ``[domain, *relations, *lifecycles]``
    :meth:`get_companion_nodes` → each wired lifecycle ``target_node`` only; coordinator expands nested companions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.graph_model.edges.entity_graph_edge import EntityGraphEdge
from action_machine.graph_model.edges.lifecycle_graph_edge import LifeCycleGraphEdge
from action_machine.intents.entity.entity_intent_resolver import EntityIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE`; :attr:`domain` / :attr:`relations` / :attr:`lifecycles` from :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_association_edges`. :meth:`get_all_edges` lists domain, relations, lifecycle associations only; :meth:`get_companion_nodes` returns direct lifecycle target rows only. Nested state companions are expanded by the coordinator.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge] = field(init=False)
    lifecycles: list[LifeCycleGraphEdge] = field(init=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict({"description": EntityIntentResolver.resolve_description(entity_cls)}),
            node_obj=entity_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge.from_entity_declared_host(entity_cls, self))
        object.__setattr__(self, "relations", EntityGraphEdge.get_entity_relation_edges(entity_cls))
        object.__setattr__(self, "lifecycles", list(LifeCycleGraphEdge.get_lifecycle_association_edges(entity_cls)))

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Direct lifecycle companion rows."""
        return [target for edge in self.lifecycles if (target := edge.target_node) is not None]

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return ``domain``, entity relations, and lifecycle associations."""
        return [self.domain, *self.relations, *self.lifecycles]

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
:class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge` lifecycle associations (:attr:`lifecycles`),
and all template ``lifecycle_transition`` rows flattened on :attr:`states`.

Companions and coordinator wiring still traverse lifecycles; state interchange rows stem from wired lifecycle vertices.

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
              ├─ :attr:`lifecycles` ← :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_association_edges`
              └─ :attr:`states`     ← :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_transition_edges`
              │
              v
    :meth:`get_all_edges` → ``[domain, *relations, *lifecycles]``; :attr:`states` aggregates template ``lifecycle_transition`` rows (:class:`~action_machine.graph_model.edges.state_graph_edge.StateGraphEdge`).
    :meth:`get_companion_nodes` → lifecycle field vertices + their ``StateGraphNode`` companions (from :attr:`lifecycles`)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.graph_model.edges.entity_graph_edge import EntityGraphEdge
from action_machine.graph_model.edges.lifecycle_graph_edge import LifeCycleGraphEdge
from action_machine.graph_model.edges.state_graph_edge import StateGraphEdge
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
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE`; :attr:`domain` / :attr:`relations` / :attr:`lifecycles` / :attr:`states` populated via :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_association_edges` and :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_transition_edges`. :meth:`get_all_edges` lists domain, relations, lifecycle associations only; :attr:`states` exposes the flattened ``lifecycle_transition`` rows. :meth:`get_companion_nodes` walks lifecycles only.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge] = field(init=False)
    lifecycles: list[LifeCycleGraphEdge] = field(init=False)
    states: list[StateGraphEdge] = field(init=False)

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
        object.__setattr__(self, "states", list(LifeCycleGraphEdge.get_lifecycle_transition_edges(entity_cls)))

    def get_companion_nodes(self) -> list[BaseGraphNode[Any]]:
        """Contributed lifecycle interchange rows plus each lifecycle's ``StateGraphNode`` companions."""
        out: list[BaseGraphNode[Any]] = []
        for edge in self.lifecycles:
            vertex = edge.target_node
            if vertex is None:
                continue
            out.append(cast(BaseGraphNode[Any], vertex))
            out.extend(vertex.get_companion_nodes())
        return out

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return ``domain``, entity relations, and lifecycle associations (transition rows on :attr:`states`)."""
        return [self.domain, *self.relations, *self.lifecycles]

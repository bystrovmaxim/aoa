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
``lifecycle`` association edges (:class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge`),
and a flattened bundle (:attr:`~EntityGraphNode.lifecycle_bundle`) that also includes companion ``lifecycle_transition`` arcs.

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
              ├─ :attr:`lifecycles` ← only ``lifecycle`` associations (:class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge`)
              └─ :attr:`lifecycle_bundle` ← full flatten from :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_edges`
              │
              v
    :meth:`get_all_edges` → ``[domain, *relations, *lifecycles]`` (no ``lifecycle_transition`` on the entity interchange id — those stay on companions)
    :meth:`get_companion_nodes` → lifecycle field vertices + their ``StateGraphNode`` rows (from :attr:`lifecycles`)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderEntity(BaseEntity): ...
    n = EntityGraphNode(OrderEntity)
    assert n.node_type == "Entity" and n.label == "OrderEntity"

``@entity`` must declare ``description`` and ``domain`` (:exc:`~action_machine.exceptions.MissingEntityInfoError`
when absent or invalid), matching resource/action resolution style for graph metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar, cast

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
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE`; :attr:`domain` / :attr:`relations` / :attr:`lifecycles` (association edges only); :attr:`lifecycle_bundle` holds associations plus each field's transition edges from :meth:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge.get_lifecycle_edges`. :meth:`get_all_edges` lists domain, relations, and lifecycle associations — not ``lifecycle_transition`` rows (:meth:`get_companion_nodes` traverses **only** :class:`~action_machine.graph_model.edges.lifecycle_graph_edge.LifeCycleGraphEdge` slots).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge] = field(init=False)
    lifecycles: list[LifeCycleGraphEdge] = field(init=False)
    lifecycle_bundle: tuple[BaseGraphEdge, ...] = field(init=False, repr=False, compare=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict({"description": EntityIntentResolver.resolve_description(entity_cls)}),
            node_obj=entity_cls,
        )
        lifes_full = LifeCycleGraphEdge.get_lifecycle_edges(self, entity_cls)
        lifes_associations_only = [
            e for e in lifes_full if isinstance(e, LifeCycleGraphEdge)
        ]
        object.__setattr__(self, "domain", DomainGraphEdge.from_entity_declared_host(entity_cls, self))
        object.__setattr__(self, "relations", EntityGraphEdge.get_entity_relation_edges(self, entity_cls))
        object.__setattr__(self, "lifecycles", lifes_associations_only)
        object.__setattr__(self, "lifecycle_bundle", tuple(lifes_full))

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
        """Return ``domain``, entity relations, and lifecycle field edges."""
        return [self.domain, *self.relations, *self.lifecycles]

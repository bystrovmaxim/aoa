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
and ``@entity_relation`` edges from :class:`~action_machine.graph_model.edges.entity_graph_edge.EntityGraphEdge`.

(``@entity`` ``domain``: :meth:`~action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_domain_type`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TEntity]  (``TEntity`` bound to ``BaseEntity``)
              │
              v
    EntityGraphNode helpers / ``__init__``  →  frozen ``BaseGraphNode``

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
from typing import ClassVar, TypeVar

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.graph_model.edges.entity_graph_edge import EntityGraphEdge
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
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE` for ``node_type``; ``properties["description"]`` via :meth:`~action_machine.intents.entity.entity_intent_resolver.EntityIntentResolver.resolve_description`; ``domain`` via :class:`~action_machine.graph_model.edges.domain_graph_edge.DomainGraphEdge`; entity→entity fields via :class:`~action_machine.graph_model.edges.entity_graph_edge.EntityGraphEdge` (``relations``).
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)
    relations: list[EntityGraphEdge]

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict({"description": EntityIntentResolver.resolve_description(entity_cls)}),
            node_obj=entity_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge.from_entity_declared_host(entity_cls, self))
        object.__setattr__(self, "relations", EntityGraphEdge.get_entity_relation_edges(self, entity_cls)) # type: ignore


    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return ``domain`` plus every non-omitted entity relation edge."""
        return [self.domain, *self.relations]

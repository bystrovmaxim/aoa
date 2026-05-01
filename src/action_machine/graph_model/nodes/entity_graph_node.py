# src/action_machine/graph_model/nodes/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description`, and
a ``domain`` edge built by :class:`~action_machine.graph_model.edges.domain_graph_edge.DomainGraphEdge`
(``@meta`` ``domain``: :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_domain_type`).

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

``@meta`` must declare ``description`` and ``domain`` (:exc:`~action_machine.exceptions.MissingMetaError`
when absent or invalid), matching :class:`~action_machine.graph_model.nodes.action_graph_node.ActionGraphNode`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, TypeVar

from action_machine.domain.entity import BaseEntity
from action_machine.graph_model.edges.domain_graph_edge import DomainGraphEdge
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE` for ``node_type``; ``properties["description"]`` via :meth:`~action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver.resolve_description`; ``domain`` via :class:`~action_machine.graph_model.edges.domain_graph_edge.DomainGraphEdge`.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain: DomainGraphEdge = field(init=False, repr=False, compare=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict({"description": MetaIntentResolver.resolve_description(entity_cls)}),
            node_obj=entity_cls,
        )
        object.__setattr__(self, "domain", DomainGraphEdge(entity_cls, self.NODE_TYPE, self))

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return entity relationship edges materialized in the explicit edge field."""
        return [self.domain]

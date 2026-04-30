# src/action_machine/graph_model/nodes/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`_get_properties`, and
an optional explicit ``domain_edge`` (``@entity`` / ``_entity_info`` merged with
``@meta`` / ``_meta_info``; see :meth:`_declaration_dict`).

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

Edge case: no declaration dict / no domain → ``edges == []``; invalid or
missing ``domain`` is ignored (same as no edges).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.intents.meta.meta_intent_resolver import MetaIntentResolver
from action_machine.system_core import TypeIntrospection
from graph.association_graph_edge import AssociationGraphEdge
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode

from .domain_graph_node import DomainGraphNode

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE` for ``node_type``; ``_get_properties`` / ``_get_domain_edge`` via :meth:`_declaration_dict`.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    domain_edge: AssociationGraphEdge | None = field(init=False, repr=False, compare=False)

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict(EntityGraphNode._get_properties(entity_cls)),
            node_obj=entity_cls,
        )
        domain_edge = self._get_domain_edge(entity_cls)
        object.__setattr__(self, "domain_edge", domain_edge[0] if domain_edge else None)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return entity relationship edges materialized in the explicit edge field."""
        return [
            *([] if self.domain_edge is None else [self.domain_edge]),
        ]

    @classmethod
    def _get_properties(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """``description`` when present in the merged declaration dict (``@entity`` / ``@meta``)."""
        properties: dict[str, Any] = {}
        desc = cls._declaration_dict(entity_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    def _get_domain_edge(
        self,
        entity_cls: type[TEntity],
    ) -> list[AssociationGraphEdge]:
        """Zero or one domain edge; empty when declarations have no valid ``BaseDomain`` in ``domain``."""
        return [
            AssociationGraphEdge(
                edge_name="domain",
                is_dag=False,
                source_node_id=TypeIntrospection.full_qualname(entity_cls),
                source_node_type=self.NODE_TYPE,
                source_node=self,
                target_node_id=TypeIntrospection.full_qualname(domain_cls),
                target_node_type=DomainGraphNode.NODE_TYPE,
                target_node=None,
            )
            for domain_cls in [self._declaration_dict(entity_cls).get("domain")]
            if isinstance(domain_cls, type) and issubclass(domain_cls, BaseDomain)
        ]

    @classmethod
    def _declaration_dict(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """
        Merge ``_entity_info`` (``@entity``) then ``_meta_info`` (``@meta``); latter wins on key clash.
        """
        out: dict[str, Any] = {}
        raw_entity = getattr(entity_cls, "_entity_info", None)
        if isinstance(raw_entity, dict):
            out.update(raw_entity)
        out.update(MetaIntentResolver.meta_info_dict(entity_cls))
        return out

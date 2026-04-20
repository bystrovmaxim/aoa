# src/action_machine/domain/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`get_properties`, ``edges`` from
:meth:`_get_all_edges` via :meth:`get_domain_edge` (``@entity`` / ``_entity_info`` and ``@meta`` / ``_meta_info`` merged; see :meth:`_meta_info_dict`).

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

from dataclasses import dataclass
from typing import Any, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from graph.qualified_name import cls_qualified_dotted_id
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import EdgeRelationship

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; ``get_properties`` / ``get_domain_edge`` via :meth:`_meta_info_dict`; ``edges`` = :meth:`_get_all_edges`.
    AI-CORE-END
    """

    @classmethod
    def _meta_info_dict(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """
        Merge ``_entity_info`` (``@entity``) then ``_meta_info`` (``@meta``); latter wins on key clash.
        """
        out: dict[str, Any] = {}
        for attr in ("_entity_info", "_meta_info"):
            raw = getattr(entity_cls, attr, None)
            if isinstance(raw, dict):
                out.update(raw)
        return out

    @classmethod
    def get_domain_edge(
        cls,
        entity_cls: type[TEntity],
    ) -> BaseGraphEdge | None:
        """
        ``BaseGraphEdge`` for the ``domain`` slot, or ``None`` when declarations have no
        valid ``BaseDomain`` in ``domain``.
        """
        meta_info_dict = cls._meta_info_dict(entity_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return None
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return None
        return BaseGraphEdge(
            edge_name="domain",
            is_dag=False,
            source_node_id=cls_qualified_dotted_id(entity_cls),
            source_node_type="Entity",
            source_node_obj=entity_cls,
            source_node_relationship=EdgeRelationship.ASSOCIATION,
            target_node_id=cls_qualified_dotted_id(domain_cls),
            target_node_type="Domain",
            target_node_obj=domain_cls,
            target_node_relationship=EdgeRelationship.ASSOCIATION,
        )

    @classmethod
    def _get_all_edges(cls, entity_cls: type[TEntity]) -> list[BaseGraphEdge]:
        """From :meth:`get_domain_edge` — empty list when ``get_domain_edge`` is ``None``."""
        edge = cls.get_domain_edge(entity_cls)
        return [edge] if edge is not None else []

    @classmethod
    def get_properties(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """``description`` when present in the merged declaration dict (``@entity`` / ``@meta``)."""
        properties: dict[str, Any] = {}
        desc = cls._meta_info_dict(entity_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    def __init__(self, entity_cls: type[TEntity]) -> None:
        super().__init__(
            node_id=cls_qualified_dotted_id(entity_cls),
            node_type="Entity",
            label=entity_cls.__name__,
            properties=dict(EntityGraphNode.get_properties(entity_cls)),
            edges=list(EntityGraphNode._get_all_edges(entity_cls)),
            node_obj=entity_cls,
        )

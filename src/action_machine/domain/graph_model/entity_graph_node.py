# src/action_machine/domain/graph_model/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`get_properties`, ``edges`` from
:meth:`_get_all_edges` via :meth:`get_domain_edge` (``@entity`` / ``_entity_info`` merged with ``@meta`` / ``_meta_info``; see :meth:`_declaration_dict`).

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
from typing import Any, ClassVar, TypeVar

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.introspection_tools import IntentIntrospection, TypeIntrospection
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode
from graph.edge_relationship import ASSOCIATION

from .domain_graph_node import DomainGraphNode

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; :attr:`NODE_TYPE` for ``node_type``; ``get_properties`` / ``get_domain_edge`` via :meth:`_declaration_dict`; ``edges`` = :meth:`_get_all_edges`.
    AI-CORE-END
    """

    NODE_TYPE: ClassVar[str] = "Entity"
    entity_edges: list[BaseGraphEdge]

    @classmethod
    def _declaration_dict(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """
        Merge ``_entity_info`` (``@entity``) then ``_meta_info`` (``@meta``); latter wins on key clash.
        """
        out: dict[str, Any] = {}
        raw_entity = getattr(entity_cls, "_entity_info", None)
        if isinstance(raw_entity, dict):
            out.update(raw_entity)
        out.update(IntentIntrospection.meta_info_dict(entity_cls))
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
        meta_info_dict = cls._declaration_dict(entity_cls)
        domain_cls = meta_info_dict.get("domain")
        if domain_cls is None:
            return None
        if not isinstance(domain_cls, type) or not issubclass(domain_cls, BaseDomain):
            return None
        return BaseGraphEdge(
            edge_name="domain",
            is_dag=False,
            source_node_id=TypeIntrospection.full_qualname(entity_cls),
            source_node_type=cls.NODE_TYPE,
            target_node_id=TypeIntrospection.full_qualname(domain_cls),
            target_node_type=DomainGraphNode.NODE_TYPE,
            edge_relationship=ASSOCIATION,
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
        desc = cls._declaration_dict(entity_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    def __init__(self, entity_cls: type[TEntity]) -> None:
        entity_edges = EntityGraphNode._get_all_edges(entity_cls)
        super().__init__(
            node_id=TypeIntrospection.full_qualname(entity_cls),
            node_type=EntityGraphNode.NODE_TYPE,
            label=entity_cls.__name__,
            properties=dict(EntityGraphNode.get_properties(entity_cls)),
            node_obj=entity_cls,
        )
        object.__setattr__(self, "entity_edges", entity_edges)

    def get_all_edges(self) -> list[BaseGraphEdge]:
        """Return entity relationship edges materialized in the explicit edge field."""
        return self.entity_edges

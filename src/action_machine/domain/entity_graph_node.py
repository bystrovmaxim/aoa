# src/action_machine/domain/entity_graph_node.py
"""
EntityGraphNode — minimal interchange node for ``BaseEntity`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materializes a frozen :class:`~graph.base_graph_node.BaseGraphNode` from an
entity **class** object: stable ``id`` (dotted path), ``node_type="Entity"``,
``label`` from the class name, ``properties`` from :meth:`get_properties`, ``edges`` from
:meth:`_get_all_edges` via :meth:`get_domain_link` (``@entity`` / ``_entity_info`` and ``@meta`` / ``_meta_info`` merged; see :meth:`_meta_info_dict`).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    type[TEntity]  (``TEntity`` bound to ``BaseEntity``)
              │
              v
    EntityGraphNode.parse / ``_meta_info_dict`` / ``get_properties`` / ``get_domain_link`` / ``_get_all_edges``  →  frozen ``BaseGraphNode``

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- The entity class is :attr:`~graph.base_graph_node.BaseGraphNode.obj`.
- :meth:`get_properties` may add ``description`` from merged declaration dict (``@entity`` / ``@meta``). :meth:`get_domain_link` returns a :class:`~graph.base_graph_edge.BaseGraphEdge` with ``link_name="domain"`` or ``None`` when there is no valid domain; :meth:`_get_all_edges` is ``[edge]`` or ``[]``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path::

    class OrderEntity(BaseEntity): ...
    n = EntityGraphNode(OrderEntity)
    assert n.node_type == "Entity" and n.label == "OrderEntity"

Edge case: no declaration dict / no domain → ``edges == []``; invalid or
missing ``domain`` is ignored (same as no edges).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- No validation in ``parse``; :meth:`get_domain_link` is ``None`` unless ``domain`` is a
  ``BaseDomain`` subclass type in the merged declaration mapping.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Thin BaseGraphNode for entity class types.
CONTRACT: ``node_type="Entity"``; dotted-path ``id``; label = class ``__name__``; ``properties`` from :meth:`get_properties`; ``edges`` from :meth:`_get_all_edges` (via :meth:`get_domain_link` on merged ``@entity`` / ``@meta`` info).
INVARIANTS: Immutable node; domain edge from declaration metadata on the entity class.
FLOW: entity class -> ``BaseGraphNode.__init__`` -> ``parse`` -> frozen BaseGraphNode fields.
EXTENSION POINTS: Other graph node specializations follow the same parse pattern.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from action_machine.common import qualified_dotted_name
from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity import BaseEntity
from action_machine.legacy.interchange_vertex_labels import DOMAIN_VERTEX_TYPE
from graph.base_graph_edge import BaseGraphEdge
from graph.base_graph_node import BaseGraphNode, Payload

TEntity = TypeVar("TEntity", bound=BaseEntity)


@dataclass(init=False, frozen=True)
class EntityGraphNode(BaseGraphNode[type[TEntity]]):
    """
    AI-CORE-BEGIN
    ROLE: Interchange bridge for ``BaseEntity`` host classes.
    CONTRACT: Dotted-path ``id``, ``__name__`` label; ``get_properties`` / ``get_domain_link`` via :meth:`_meta_info_dict`; ``edges`` = :meth:`_get_all_edges`.
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
    def get_domain_link(
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
            link_name="domain",
            target_id=qualified_dotted_name(domain_cls),
            target_node_type=DOMAIN_VERTEX_TYPE,
            is_dag=False,
            target_cls=domain_cls,
        )

    @classmethod
    def _get_all_edges(cls, entity_cls: type[TEntity]) -> list[BaseGraphEdge]:
        """From :meth:`get_domain_link` — empty list when ``get_domain_link`` is ``None``."""
        edge = cls.get_domain_link(entity_cls)
        return [edge] if edge is not None else []

    @classmethod
    def get_properties(cls, entity_cls: type[TEntity]) -> dict[str, Any]:
        """``description`` when present in the merged declaration dict (``@entity`` / ``@meta``)."""
        properties: dict[str, Any] = {}
        desc = cls._meta_info_dict(entity_cls).get("description")
        if isinstance(desc, str) and desc.strip():
            properties["description"] = desc.strip()
        return properties

    @classmethod
    def parse(cls, entity_cls: type[TEntity]) -> Payload:
        return Payload(
            id=qualified_dotted_name(entity_cls),
            node_type="Entity",
            label=entity_cls.__name__,
            properties=dict(cls.get_properties(entity_cls)),
            edges=list(cls._get_all_edges(entity_cls)),
        )

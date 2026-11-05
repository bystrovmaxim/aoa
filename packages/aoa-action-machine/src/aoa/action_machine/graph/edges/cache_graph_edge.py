# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/cache_graph_edge.py
"""
CacheGraphEdge and CacheTagGraphEdge — an operation's cache declarations, and the entities they tag.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

- ``CacheGraphEdge``: composition ``Action → Cache`` named after the declaration
  (``@cache_key``, ``@cache_read``, ``@cache_write``, ``@cache_invalidate``).
- ``CacheTagGraphEdge``: association ``Action → Entity``, one per tag type, named
  ``caches`` for ``@cache_write`` and ``invalidates`` for ``@cache_invalidate``. They let
  a reader see that an updating action drops what reading actions cache, and let the
  build refuse a dead invalidation or a dead tag.
"""

from __future__ import annotations

from typing import Any

from aoa.action_machine.graph.core.association_graph_edge import AssociationGraphEdge
from aoa.action_machine.graph.core.composition_graph_edge import CompositionGraphEdge
from aoa.action_machine.graph.nodes.cache_graph_node import CacheGraphNode
from aoa.action_machine.intents.cache.cache_entity_fields import cached_types
from aoa.action_machine.intents.cache.cache_intent_resolver import CacheIntentResolver, tags_of
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

TAG_EDGE_NAMES = {"write": "caches", "invalidate": "invalidates"}
"""The tag edge of each kind that declares tag types."""


class CacheGraphEdge(CompositionGraphEdge):
    """
    AI-CORE-BEGIN
        ROLE: Typed composition edge host Action → one of its cache declarations.
        CONTRACT: ``edge_name`` is ``@cache_<kind>``; ``target_node`` is the ``CacheGraphNode``.
        INVARIANTS: Frozen via ``CompositionGraphEdge``; ``is_dag`` False.
    AI-CORE-END
    """

    def __init__(self, *, cache_node: CacheGraphNode) -> None:
        super().__init__(
            edge_name=f"@cache_{cache_node.properties['kind']}",
            is_dag=False,
            target_node_id=cache_node.node_id,
            target_node=cache_node,
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Return the JSON-safe edge from ``source_id`` to the declaration."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @staticmethod
    def get_cache_edges(action_cls: type[Any]) -> list[CacheGraphEdge]:
        """One edge per declaration the operation makes in its own body, in the order key, read, write, invalidate."""
        return [
            CacheGraphEdge(cache_node=CacheGraphNode(method, action_cls))
            for _kind, method in CacheIntentResolver.declarations(action_cls).declared
        ]


class CacheTagGraphEdge(AssociationGraphEdge):
    """
    AI-CORE-BEGIN
        ROLE: Typed association edge host Action → an entity its cache tags name.
        CONTRACT: ``edge_name`` is ``caches`` (``@cache_write``) or ``invalidates`` (``@cache_invalidate``); ``target_node_id`` is the entity's full qualname, wired by the coordinator.
        INVARIANTS: ``is_dag`` False; ``properties`` empty.
    AI-CORE-END
    """

    def __init__(self, *, edge_name: str, entity_cls: type) -> None:
        super().__init__(
            edge_name=edge_name,
            is_dag=False,
            target_node_id=TypeIntrospection.full_qualname(entity_cls),
            target_node=None,
            properties={},
        )

    def to_dict(self, *, source_id: str) -> dict[str, Any]:
        """Return the JSON-safe edge from ``source_id`` to the entity."""
        return {
            "source_id": source_id,
            "target_id": self.target_node_id,
            "type": self.edge_name,
            "relationship": self.edge_relationship.archimate_name,
            "is_dag": self.is_dag,
            "properties": {},
        }

    @staticmethod
    def get_cache_tag_edges(action_cls: type[Any]) -> list[CacheTagGraphEdge]:
        """``caches`` to each type the write caches (its tags, and entity by entity its Result's entity types), then ``invalidates``."""
        declarations = CacheIntentResolver.declarations(action_cls)
        edges = [CacheTagGraphEdge(edge_name=TAG_EDGE_NAMES["write"], entity_cls=tag) for tag in cached_types(action_cls)]
        if declarations.invalidate is not None:
            edges.extend(
                CacheTagGraphEdge(edge_name=TAG_EDGE_NAMES["invalidate"], entity_cls=tag)
                for tag in tags_of(declarations.invalidate)
            )
        return edges

# src/action_machine/resources/connection_intent_inspector.py
"""
ConnectionIntentInspector — graph inspector for ``@connection`` structural edges.

Emits one ``action`` facet node per class that declares connections.
If the same action also declares ``@depends``, ``DependencyIntentInspector``
emits a payload with the same graph key; ``GraphCoordinator`` merges them.

Typed data: ``Snapshot`` under cache key ``\"connections\"``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Translate ``@connection`` declarations into structural ``connection`` edges from
the **action** host to the canonical **resource_manager** vertex for the manager
class (same ``node_name`` as ``@meta`` on ``BaseResourceManager``). Decorator
fields (``key``, ``description``, …) live on **edge_meta** only; no separate
``…:connection`` facet nodes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action class with _connection_info
            │
            ▼
    inspect(target_cls)
            │
            ▼
    Snapshot.from_target(...)
            │
            ▼
    to_facet_vertex()
            │
            └─ action node + structural ``connection`` edges → ``resource_manager``

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only classes with non-empty ``_connection_info`` emit payloads.
- Snapshot storage key is fixed: ``connections``.
- Emitted edges are structural and carry ``key`` / ``description`` metadata.
- Node key intentionally collides with depends-inspector action node and is merged by coordinator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Assumes ``@connection`` decorator already validated declarations.
- This inspector does not execute connection factories or runtime I/O.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Structural connection-edge inspector for action graph topology.
CONTRACT: Read ``_connection_info``; emit merged ``action`` rows with edges to ``resource_manager``.
INVARIANTS: Facet cache key is ``connections``; payloads are skipped when declarations are absent.
FLOW: class discovery -> scratch read -> typed snapshot -> payload for coordinator merge/commit.
FAILURES: Missing declarations result in ``None`` payload (skip), not an error.
EXTENSION POINTS: Edge metadata shape can be extended through ``ConnectionInfo``.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE
from action_machine.resources.connection_decorator import ConnectionInfo
from action_machine.resources.connection_intent import ConnectionIntent
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_vertex import FacetVertex


class ConnectionIntentInspector(BaseIntentInspector):
    """
    Inspector for ``ConnectionIntent`` declarations.

    AI-CORE-BEGIN
    ROLE: Concrete connection inspector.
    CONTRACT: Emit action payloads with structural connection edges from ``_connection_info``.
    INVARIANTS: Uses ``ConnectionIntent`` marker traversal and ``connections`` snapshot key.
    AI-CORE-END
    """

    _target_intent: type = ConnectionIntent

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@connection`` facet."""

        class_ref: type
        connections: tuple[ConnectionInfo, ...]

        @staticmethod
        def _connection_edge_meta(conn_info: ConnectionInfo) -> tuple[tuple[str, Any], ...]:
            """All ``ConnectionInfo`` fields except ``cls`` (target node carries the type)."""
            pairs: list[tuple[str, Any]] = []
            for f in fields(conn_info):
                if f.name == "cls":
                    continue
                pairs.append((f.name, getattr(conn_info, f.name)))
            pairs.sort(key=lambda t: t[0])
            return tuple(pairs)

        def to_facet_vertex(self) -> FacetVertex:
            conn_edges = tuple(
                ConnectionIntentInspector._make_edge(
                    target_node_type="resource_manager",
                    target_cls=conn_info.cls,
                    edge_type="connection",
                    is_structural=True,
                    edge_meta=self._connection_edge_meta(conn_info),
                )
                for conn_info in self.connections
            )
            return FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
                node_name=ConnectionIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                edges=conn_edges,
                skip_node_type_snapshot_fallback=True,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> ConnectionIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                connections=tuple(getattr(target_cls, "_connection_info", ())),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "connections"

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        connection_info = getattr(target_cls, "_connection_info", None)
        if not connection_info:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> ConnectionIntentInspector.Snapshot | None:
        if not getattr(target_cls, "_connection_info", None):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()

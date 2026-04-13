# src/action_machine/graph/inspectors/connection_intent_inspector.py
"""
ConnectionIntentInspector — graph inspector for ``@connection`` structural edges.

Emits one ``action`` facet node per class that declares connections.
If the same action also declares ``@depends``, ``DependencyIntentInspector``
emits a payload with the same graph key; ``GateCoordinator`` merges them.

Typed data: ``Snapshot`` under cache key ``\"connections\"``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Translate ``@connection`` declarations into structural graph edges from action
nodes to connection target nodes.

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
    to_facet_payload()
            │
            └─ action node + structural "connection" edges

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
CONTRACT: Read ``_connection_info`` and emit structural ``connection`` edges from ``action`` nodes.
INVARIANTS: Facet cache key is ``connections``; payloads are skipped when declarations are absent.
FLOW: class discovery -> scratch read -> typed snapshot -> payload for coordinator merge/commit.
FAILURES: Missing declarations result in ``None`` payload (skip), not an error.
EXTENSION POINTS: Edge metadata shape can be extended through ``ConnectionInfo``.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.resources.connection_decorator import ConnectionInfo
from action_machine.resources.connection_intent import ConnectionIntent


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

        def to_facet_payload(self) -> FacetPayload:
            conn_edges = tuple(
                ConnectionIntentInspector._make_edge(
                    target_node_type="connection",
                    target_cls=conn_info.cls,
                    edge_type="connection",
                    is_structural=True,
                    edge_meta=ConnectionIntentInspector._make_meta(
                        key=conn_info.key,
                        description=conn_info.description,
                    ),
                )
                for conn_info in self.connections
            )
            return FacetPayload(
                node_type="action",
                node_name=ConnectionIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                edges=conn_edges,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> ConnectionIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                connections=tuple(getattr(target_cls, "_connection_info", ())),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "connections"

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
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
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

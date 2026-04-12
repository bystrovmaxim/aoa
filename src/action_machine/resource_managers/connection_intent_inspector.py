# src/action_machine/resource_managers/connection_intent_inspector.py
"""
ConnectionIntentInspector — graph inspector for ``@connection`` structural edges.

Emits one ``action`` facet node per class that declares connections.
If the same action also declares ``@depends``, ``DependencyIntentInspector``
emits a payload with the same graph key; ``GateCoordinator`` merges them.

Typed data: ``Snapshot`` under cache key ``\"connections\"``.
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload
from action_machine.resource_managers.connection_decorator import ConnectionInfo
from action_machine.resource_managers.connection_intent import ConnectionIntent


class ConnectionIntentInspector(BaseIntentInspector):
    """Inspector for ``ConnectionIntent`` / ``_connection_info`` → structural ``connection`` edges."""

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

# src/action_machine/graph/inspectors/dependency_intent_inspector.py
"""
DependencyIntentInspector — graph inspector for ``@depends`` structural edges.

Emits one ``action`` facet node per class that declares dependencies.
If the same action also declares ``@connection``, ``ConnectionIntentInspector``
emits a second payload with the same graph key; ``GateCoordinator`` merges
those into a single node (concatenated edges).

Typed data: ``Snapshot`` under cache key ``\"depends\"`` (not ``\"action\"``).
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.dependencies.dependency_factory import DependencyInfo
from action_machine.dependencies.dependency_intent import DependencyIntent
from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload


class DependencyIntentInspector(BaseIntentInspector):
    """Inspector for ``DependencyIntent`` / ``_depends_info`` → structural ``depends`` edges."""

    _target_intent: type = DependencyIntent

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@depends`` facet."""

        class_ref: type
        dependencies: tuple[DependencyInfo, ...]

        def to_facet_payload(self) -> FacetPayload:
            dep_edges = tuple(
                DependencyIntentInspector._make_edge(
                    target_node_type="dependency",
                    target_cls=dep_info.cls,
                    edge_type="depends",
                    is_structural=True,
                )
                for dep_info in self.dependencies
            )
            return FacetPayload(
                node_type="action",
                node_name=DependencyIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                edges=dep_edges,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> DependencyIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                dependencies=tuple(getattr(target_cls, "_depends_info", ())),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "depends"

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        depends_info = getattr(target_cls, "_depends_info", None)
        if not depends_info:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> DependencyIntentInspector.Snapshot | None:
        if not getattr(target_cls, "_depends_info", None):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

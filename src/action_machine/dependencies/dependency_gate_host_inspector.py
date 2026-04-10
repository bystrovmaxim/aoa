# src/action_machine/dependencies/dependency_gate_host_inspector.py
"""
DependencyGateHostInspector — graph inspector for ``@depends`` structural edges.

Emits one ``action`` facet node per class that declares dependencies.
If the same action also declares ``@connection``, ``ConnectionGateHostInspector``
emits a second payload with the same graph key; ``GateCoordinator`` merges
those into a single node (concatenated edges).

Typed data: ``Snapshot`` under cache key ``\"depends\"`` (not ``\"action\"``).
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.dependencies.dependency_factory import DependencyInfo
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class DependencyGateHostInspector(BaseGateHostInspector):
    """Inspector for ``DependencyGateHost`` / ``_depends_info`` → structural ``depends`` edges."""

    _target_mixin: type = DependencyGateHost

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_mixin)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@depends`` facet."""

        class_ref: type
        dependencies: tuple[DependencyInfo, ...]

        def to_facet_payload(self) -> FacetPayload:
            dep_edges = tuple(
                DependencyGateHostInspector._make_edge(
                    target_node_type="dependency",
                    target_cls=dep_info.cls,
                    edge_type="depends",
                    is_structural=True,
                )
                for dep_info in self.dependencies
            )
            return FacetPayload(
                node_type="action",
                node_name=DependencyGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                edges=dep_edges,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> DependencyGateHostInspector.Snapshot:
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
    ) -> DependencyGateHostInspector.Snapshot | None:
        if not getattr(target_cls, "_depends_info", None):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

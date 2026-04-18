# src/action_machine/dependencies/dependency_intent_inspector.py
"""
DependencyIntentInspector — graph inspector for ``@depends`` structural edges.

Emits one ``action`` facet node per class that declares dependencies.
If the same action also declares ``@connection``, ``ConnectionIntentInspector``
emits a second payload with the same graph key; ``GraphCoordinator`` merges
those into a single node (concatenated edges).

Typed data: ``Snapshot`` under cache key ``\"depends\"`` (not ``\"action\"``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Translate ``@depends`` declarations into structural graph edges from action
nodes to dependency target nodes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    action class with _depends_info
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
            └─ action node + structural "depends" edges

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only classes with non-empty ``_depends_info`` emit payloads.
- Snapshot storage key is fixed: ``depends``.
- Emitted edges are structural with edge type ``depends``.
- Action node key may collide with connection inspector payload and is merged by coordinator.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Assumes ``@depends`` declarations were validated by decorator-level rules.
- This inspector does not instantiate dependencies or execute factories.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Structural dependency-edge inspector for action topology.
CONTRACT: Read ``_depends_info`` and emit ``depends`` edges from ``action`` nodes.
INVARIANTS: Snapshot key is ``depends``; classes without declarations are skipped.
FLOW: marker subclass discovery -> scratch read -> typed snapshot -> payload for coordinator merge/commit.
FAILURES: Missing declarations return ``None`` payload (skip), not an error.
EXTENSION POINTS: Edge enrichment can be introduced by extending ``DependencyInfo`` handling.
AI-CORE-END
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.dependencies.dependency_factory import DependencyInfo
from action_machine.dependencies.dependency_intent import DependencyIntent
from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.model.base_action import BaseAction


class DependencyIntentInspector(BaseIntentInspector):
    """
    Inspector for ``DependencyIntent`` declarations.

    AI-CORE-BEGIN
    ROLE: Concrete dependency inspector.
    CONTRACT: Emit action payloads with structural depends edges from ``_depends_info``.
    INVARIANTS: Uses ``DependencyIntent`` marker traversal and ``depends`` snapshot key.
    AI-CORE-END
    """

    _target_intent: type = DependencyIntent

    @staticmethod
    def _depends_target_node_type(dep_cls: type) -> str:
        """
        Interchange target kind for a ``@depends`` class.

        ``BaseAction`` subclasses share the primary ``action`` vertex id with the
        action's other facets; stubs use ``node_type=\"action\"`` so the coordinator
        merges them instead of duplicating ``node_name`` as a separate ``dependency`` node.
        """
        return "action" if issubclass(dep_cls, BaseAction) else "dependency"

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
                    target_node_type=DependencyIntentInspector._depends_target_node_type(
                        dep_info.cls,
                    ),
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

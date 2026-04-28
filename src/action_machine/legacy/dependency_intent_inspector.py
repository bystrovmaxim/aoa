# src/action_machine/legacy/dependency_intent_inspector.py
"""
DependencyIntentInspector — graph inspector for ``@depends`` structural edges.

Emits one ``action`` facet node per class that declares dependencies.
``@connection`` is not represented on the legacy facet graph; use
``ActionGraphNode`` for connection edges.

Typed data: ``Snapshot`` under cache key ``"depends"`` (not ``"action"``).

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
    to_facet_vertex()
            │
            └─ action node + structural "depends" edges

    Coordinator materialization adds informational ``belongs_to`` from each
        synthesized **Service** stub to the ``Application`` vertex when
    that vertex exists. ``BaseAction`` / ``BaseResource`` targets reuse
    the canonical ``action`` / ``resource_manager`` vertices (no application edge).
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.intents.depends.depends_intent import DependsIntent
from action_machine.legacy.application_context import ApplicationContext
from action_machine.legacy.interchange_vertex_labels import (
    ACTION_VERTEX_TYPE,
    APPLICATION_VERTEX_TYPE,
    SERVICE_VERTEX_TYPE,
)
from action_machine.model.base_action import BaseAction
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.dependency_info import DependencyInfo
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex


class DependencyIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete dependency inspector.
    CONTRACT: Emit action payloads with structural depends edges from ``_depends_info``.
    INVARIANTS: Uses ``DependsIntent`` marker traversal and ``depends`` snapshot key.
    AI-CORE-END
"""

    _target_intent: type = DependsIntent

    @classmethod
    def stub_outgoing_edges_for_class_dependency(cls) -> tuple[FacetEdge, ...]:
        """
        Edges attached to a materialized ``@depends`` class stub (not ``BaseAction``).

        Declares that a **Service** stub sits under the logical
        ``Application`` root (``BELONGS_TO`` in interchange). Not used for
        ``action`` / ``resource_manager`` merge targets.
        """
        return (
            cls._make_edge(
                target_node_type=APPLICATION_VERTEX_TYPE,
                target_cls=ApplicationContext,
                edge_type="belongs_to",
                is_structural=False,
            ),
        )

    @staticmethod
    def _depends_target_node_type(dep_cls: type) -> str:
        """
        Interchange target kind for a ``@depends`` class.

        ``BaseAction`` subclasses use ``node_type`` ``\"Action\"`` so edges merge into
        the primary action vertex. ``BaseResource`` subclasses use
        ``\"resource_manager\"`` — the same key as ``@connection``, so depends and
        connection share one canonical manager node.

        Other dependency classes use
        ``action_machine.legacy.interchange_vertex_labels.SERVICE_VERTEX_TYPE``;
        identity remains ``target_name`` / ``class_ref``.
        """
        if issubclass(dep_cls, BaseAction):
            return ACTION_VERTEX_TYPE
        if issubclass(dep_cls, BaseResource):
            return "resource_manager"
        return SERVICE_VERTEX_TYPE

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed ``@depends`` facet."""

        class_ref: type
        dependencies: tuple[DependencyInfo, ...]

        def to_facet_vertex(self) -> FacetVertex:
            dep_edges_list: list[FacetEdge] = []
            for dep_info in self.dependencies:
                dep_cls = dep_info.cls
                stub: tuple[FacetEdge, ...] = ()
                if not issubclass(dep_cls, BaseAction) and not issubclass(
                    dep_cls,
                    BaseResource,
                ):
                    stub = DependencyIntentInspector.stub_outgoing_edges_for_class_dependency()
                dep_edges_list.append(
                    DependencyIntentInspector._make_edge(
                        target_node_type=DependencyIntentInspector._depends_target_node_type(
                            dep_cls,
                        ),
                        target_cls=dep_cls,
                        edge_type="depends",
                        is_structural=True,
                        synthetic_stub_edges=stub,
                    ),
                )
            dep_edges = tuple(dep_edges_list)
            return FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
                node_name=DependencyIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                edges=dep_edges,
                skip_node_type_snapshot_fallback=True,
            )

        @classmethod
        def from_target(cls, target_cls: type) -> DependencyIntentInspector.Snapshot:
            return cls(
                class_ref=target_cls,
                dependencies=tuple(getattr(target_cls, "_depends_info", ())),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "depends"

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
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
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()

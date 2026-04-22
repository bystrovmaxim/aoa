# src/action_machine/legacy/role_mode_intent_inspector.py
"""
Graph inspector for role lifecycle metadata (``@role_mode`` scratch).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Only ``ApplicationRole`` receives a **``role_class``** facet row from this inspector
(same anchor as ``RoleClassInspector``), when the class carries ``_role_mode_info``
from ``@role_mode``. Lifecycle ``mode`` lives in ``node_meta`` on that vertex — it
is **not** a separate graph suffix like ``…:role_mode``. Other ``RoleModeIntent``
classes keep ``@role_mode`` for runtime; they are not separate ``role_class`` graph
nodes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @role_mode(RoleMode.ALIVE)
    class ApplicationRole(...):
        ...

          │ import
          ▼
    cls._role_mode_info["mode"] == RoleMode.ALIVE
          │
          ▼
    RoleModeIntentInspector.inspect(cls)
          │
          ▼
    FacetVertex(node_type="role_class", node_name=…ApplicationRole, node_meta mode=…)
          │
          ▼
    GraphCoordinator merges with ``RoleClassInspector`` row → one anchor facet key

"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.intents.role_mode.role_mode_decorator import RoleMode
from action_machine.intents.role_mode.role_mode_intent import RoleModeIntent
from action_machine.legacy.role_graph_roots import ROLE_CLASS_GRAPH_ROOTS
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_vertex import FacetVertex


class RoleModeIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete inspector for role lifecycle classification metadata.
    CONTRACT: ``role_class`` vertex identity + ``mode`` in ``node_meta``; snapshot key ``role_mode``.
    INVARIANTS: Traversal source is ``RoleModeIntent``; payloads contain no edges.
    AI-CORE-END
"""

    _target_intent: type = RoleModeIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed lifecycle facet for a role class."""

        class_ref: type
        mode: RoleMode

        def to_facet_vertex(self) -> FacetVertex:
            return FacetVertex(
                node_type="role_class",
                node_name=RoleModeIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=RoleModeIntentInspector._make_meta(mode=self.mode),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> RoleModeIntentInspector.Snapshot:
            mode = RoleMode.declared_for(target_cls)
            return cls(class_ref=target_cls, mode=mode)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        if not issubclass(target_cls, RoleModeIntent):
            return None
        if target_cls not in ROLE_CLASS_GRAPH_ROOTS:
            return None
        info = getattr(target_cls, "_role_mode_info", None)
        if not isinstance(info, dict):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> RoleModeIntentInspector.Snapshot | None:
        if target_cls not in ROLE_CLASS_GRAPH_ROOTS:
            return None
        if not isinstance(getattr(target_cls, "_role_mode_info", None), dict):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetVertex,
    ) -> str:
        return "role_mode"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()

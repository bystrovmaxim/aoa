# src/action_machine/graph/inspectors/role_mode_intent_inspector.py
"""
Graph inspector for role lifecycle metadata (``@role_mode`` scratch).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Emit a dedicated facet node for every ``RoleModeIntent`` subclass that carries
``_role_mode_info`` (written by ``@role_mode``). This facet is **separate** from
the action ``role`` facet produced by ``RoleIntentInspector`` so tooling can
distinguish “what the action requires” from “how the role type is classified”.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Traversal uses ``_target_intent = RoleModeIntent`` (same subtree as
  ``@role_mode`` authorization).
- ``BaseRole`` itself has no scratch and yields ``None`` from ``inspect()``.
- ``node_type`` is ``role_mode`` (not ``role``). Snapshot storage key matches.
- **Does not** validate unique ``name`` or ``requires_role`` topology — that is
  ``RoleClassInspector``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @role_mode(RoleMode.ALIVE)
    class OrderViewerRole(BaseRole):
        ...

          │ import
          ▼
    cls._role_mode_info["mode"] == RoleMode.ALIVE
          │
          ▼
    RoleModeIntentInspector.inspect(cls)
          │
          ▼
    FacetPayload(node_type="role_mode", node_meta includes mode=…)
          │
          ▼
    GateCoordinator.build() → graph key ``role_mode:<module>.OrderViewerRole``

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: concrete ``BaseRole`` with ``@role_mode`` → non-``None`` payload.

Edge case: undecorated ``RoleModeIntent`` subclass without scratch →
``inspect`` returns ``None`` (nothing to record).

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Corrupt ``_role_mode_info`` should not occur if ``@role_mode`` is the only
  writer; invalid payloads are not repaired here.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Lifecycle facet inspector for role types.
CONTRACT: ``role_mode`` nodes from ``_role_mode_info``; disjoint from action ``role``.
INVARIANTS: Walk ``RoleModeIntent``; skip classes without scratch.
FLOW: coordinator collect → inspect → FacetPayload → commit.
FAILURES: Returns None when no lifecycle scratch.
EXTENSION POINTS: None; keep split with ``RoleClassInspector``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.auth.role_mode_decorator import RoleMode
from action_machine.intents.auth.role_mode_intent import RoleModeIntent


class RoleModeIntentInspector(BaseIntentInspector):
    """
    Builds ``role_mode`` facet nodes from ``@role_mode`` scratch on role types.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for role lifecycle classification metadata.
    CONTRACT: Emit ``role_mode`` payloads from ``_role_mode_info`` declarations.
    INVARIANTS: Traversal source is ``RoleModeIntent``; payloads contain no edges.
    AI-CORE-END
    """

    _target_intent: type = RoleModeIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed lifecycle facet for a role class."""

        class_ref: type
        mode: RoleMode

        def to_facet_payload(self) -> FacetPayload:
            return FacetPayload(
                node_type="role_mode",
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
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        if not issubclass(target_cls, RoleModeIntent):
            return None
        info = getattr(target_cls, "_role_mode_info", None)
        if not isinstance(info, dict):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> RoleModeIntentInspector.Snapshot | None:
        if not isinstance(getattr(target_cls, "_role_mode_info", None), dict):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetPayload,
    ) -> str:
        return "role_mode"

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

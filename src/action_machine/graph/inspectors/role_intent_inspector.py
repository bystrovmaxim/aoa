# src/action_machine/graph/inspectors/role_intent_inspector.py
"""
Role intent inspector for role facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Walk subclasses of ``RoleIntent``, extract role specifications from classes
decorated with ``@check_roles``, and produce ``FacetPayload`` nodes for the
coordinator graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @check_roles(AdminRole)
          │
          ▼
    cls._role_info = {"spec": <BaseRole subtype> | tuple[...] | NoneRole | AnyRole }
          │
          ▼
    RoleIntentInspector.inspect()
          │
          ▼
    Snapshot.from_target() → FacetPayload(node_type="role")
          │
          ▼
    GateCoordinator graph node ``role:<class_name>``

The inspector uses ``_target_intent = RoleIntent`` to discover candidate
classes. For each class with a non‑null ``_role_info``, it builds a payload
containing the role spec. No outgoing edges are added here; ``RoleClassInspector``
may attach informational ``requires_role`` edges **to** these nodes from
``role_class`` facets.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only classes inheriting ``RoleIntent`` are inspected.
- A class may inherit ``RoleIntent`` without ``@check_roles``; such classes
  produce ``None`` from ``inspect()``.
- The ``spec`` value is taken directly from ``_role_info["spec"]`` (``BaseRole``
  type, tuple of types, ``NoneRole``, or ``AnyRole``).
- The facet storage key is ``"role"``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AdminRole)
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    # inspect(AdminAction) → FacetPayload(
    #     node_type="role",
    #     node_meta includes spec == AdminRole,
    # )

    @check_roles(NoneRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    # inspect(PingAction) → spec is NoneRole

    class BaseAction(ABC, RoleIntent, ...):
        ...

    # inspect(BaseAction) → None (no _role_info)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- The inspector does not validate the role spec; validation is performed by
  ``@check_roles`` at import time and by the machine at runtime.
- Global graph checks (key uniqueness, acyclicity, role topology) are performed
  by ``GateCoordinator.build()`` together with ``RoleClassInspector`` /
  ``RoleModeIntentInspector``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role facet inspector.
CONTRACT: Convert ``_role_info`` into a ``FacetPayload`` of type ``"role"``.
INVARIANTS: Target mixin is RoleIntent; storage key is "role"; no edges.
FLOW: _role_info present → Snapshot → FacetPayload → coordinator graph.
FAILURES: Returns None when ``_role_info`` is missing.
EXTENSION POINTS: Payload consumed by coordinator and role-checking runtime.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.auth.role_intent import RoleIntent


class RoleIntentInspector(BaseIntentInspector):
    """
    Role intent inspector.

    Walks ``RoleIntent`` subclasses, detects ``@check_roles``, and builds
    ``FacetPayload`` with role ``spec`` for the coordinator.
    """

    _target_intent: type = RoleIntent

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed role facet for a target class."""

        class_ref: type
        spec: Any

        def to_facet_payload(self) -> FacetPayload:
            return FacetPayload(
                node_type="role",
                node_name=RoleIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=RoleIntentInspector._make_meta(spec=self.spec),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> RoleIntentInspector.Snapshot:
            info = getattr(target_cls, "_role_info", None)
            if not isinstance(info, dict):
                raise TypeError(
                    f"{target_cls.__name__} does not contain valid _role_info.",
                )
            return cls(class_ref=target_cls, spec=info["spec"])

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        """Return all subclasses of ``RoleIntent``."""
        return cls._collect_subclasses(cls._target_intent)

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Build payload if ``@check_roles`` is present."""
        role_info = getattr(target_cls, "_role_info", None)
        if role_info is None:
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> RoleIntentInspector.Snapshot | None:
        if getattr(target_cls, "_role_info", None) is None:
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Build a ``role`` node from ``_role_info``."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

# src/action_machine/intents/auth/role_class_inspector.py
"""
Graph inspector for typed role topology (MRO, ``requires_role``, names).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Materialize a **single** ``role_class`` vertex — ``ApplicationRole`` — as the
interchange anchor. ``RoleIntentInspector`` emits ``requires_role`` edges toward
that anchor (with ``edge_meta`` listing concrete ``@check_roles`` types when
needed). This inspector still **validates** every ``BaseRole`` subtype under
``BaseRole`` (unique ``name``, MRO, and ``@role_mode``) at ``inspect()`` time,
but returns a ``FacetVertex`` only for ``ApplicationRole``. Lifecycle ``mode``
merges from ``RoleModeIntentInspector`` on that node.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Every ``BaseRole`` subclass under inspection must carry ``@role_mode``
  (``_role_mode_info`` present).
- **Unique** stable ``name`` among all ``BaseRole`` subclasses (graph anchors
  included).
- **No** ``RoleMode.UNUSED`` ``BaseRole`` ancestor (other than ``BaseRole``) in
  the MRO of any inspected role.
- **Only** ``ApplicationRole`` produces a ``role_class`` facet row (no feature flags).
- **Does not** re-validate non-empty ``name`` / ``description`` strings (handled
  in ``BaseRole.__init_subclass__``). **Does not** duplicate lifecycle facet
  work (see ``RoleModeIntentInspector``).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseRole subclasses (validated here)
          │
          ├── ``RoleClassInspector`` → ``role_class`` only for ``ApplicationRole``
          │
          └── ``RoleIntentInspector`` → ``action`` —requires_role→ those anchors

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: two unrelated classes both use ``name = "dup"`` →
``InvalidGraphError`` at ``build()``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``InvalidGraphError``: duplicate ``name``, ``UNUSED`` in MRO,
  missing ``@role_mode``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Role-class topology inspector.
CONTRACT: ``role_class`` node only for ``ApplicationRole``; validates all ``BaseRole`` subclasses.
INVARIANTS: Unique name; no UNUSED in MRO; ``@role_mode`` on every subclass.
FLOW: collect subclasses → validate → FacetVertex only for taxonomy roots.
FAILURES: InvalidGraphError on broken topology.
EXTENSION POINTS: Align new cross-facet edges with ``RoleIntentInspector``.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.exceptions import InvalidGraphError
from action_machine.graph.facet_vertex import FacetVertex
from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.auth.role_graph_roots import ROLE_CLASS_GRAPH_ROOTS
from action_machine.intents.auth.role_mode_decorator import RoleMode


def _all_base_role_types() -> tuple[type[BaseRole], ...]:
    return tuple(
        c
        for c in BaseIntentInspector._collect_subclasses(BaseRole)
        if c is not BaseRole and "<locals>" not in c.__qualname__
    )


def _assert_unique_role_name(cls: type[BaseRole]) -> None:
    my_name = cls.name
    for other in _all_base_role_types():
        if other is cls:
            continue
        if other.name == my_name:
            raise InvalidGraphError(
                f"Duplicate role name {my_name!r}: {cls.__qualname__} and "
                f"{other.__qualname__}. "
                f"Stable role names must be unique across BaseRole subclasses.",
            )


def _assert_mro_no_unused_base(cls: type[BaseRole]) -> None:
    for base in cls.__mro__[1:]:
        if base is BaseRole or base is object:
            continue
        if not (isinstance(base, type) and issubclass(base, BaseRole)):
            continue
        try:
            mode = RoleMode.declared_for(base)
        except TypeError:
            continue
        if mode is RoleMode.UNUSED:
            raise InvalidGraphError(
                f"Role {cls.__qualname__!r} inherits from {base.__qualname__!r}, "
                f"which is RoleMode.UNUSED.",
            )


class RoleClassInspector(BaseIntentInspector):
    """
    Emits ``role_class`` topology and action requirements.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for role-class topology.
    CONTRACT: Emit ``role_class`` only for ``ApplicationRole``.
    INVARIANTS: All ``BaseRole`` subclasses validated; roots carry lifecycle metadata.
    AI-CORE-END
    """

    _target_intent: type = BaseRole

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed snapshot for a ``role_class`` graph node."""

        class_ref: type[BaseRole]

        def to_facet_vertex(self) -> FacetVertex:
            return FacetVertex(
                node_type="role_class",
                node_name=RoleClassInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=RoleClassInspector._make_meta(
                    name=self.class_ref.name,
                    description=self.class_ref.description,
                ),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type[BaseRole]) -> RoleClassInspector.Snapshot:
            return cls(class_ref=target_cls)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return list(cls._collect_subclasses(cls._target_intent))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | None:
        if target_cls is BaseRole:
            return None
        if not issubclass(target_cls, BaseRole):
            return None
        # Function-scoped subclasses (e.g. negative tests) must not pollute the graph.
        if "<locals>" in target_cls.__qualname__:
            return None
        role_cls: type[BaseRole] = target_cls
        if not isinstance(getattr(role_cls, "_role_mode_info", None), dict):
            raise InvalidGraphError(
                f"Role class {target_cls.__qualname__} has no @role_mode metadata "
                f"(_role_mode_info). Every BaseRole subclass in the graph must "
                f"declare a lifecycle mode.",
            )
        _assert_unique_role_name(role_cls)
        _assert_mro_no_unused_base(role_cls)
        if role_cls not in ROLE_CLASS_GRAPH_ROOTS:
            return None
        return cls._build_payload(role_cls)

    @classmethod
    def facet_snapshot_for_class(cls, target_cls: type) -> RoleClassInspector.Snapshot | None:
        if target_cls is BaseRole:
            return None
        if not issubclass(target_cls, BaseRole):
            return None
        if "<locals>" in target_cls.__qualname__:
            return None
        role_cls: type[BaseRole] = target_cls
        if not isinstance(getattr(role_cls, "_role_mode_info", None), dict):
            return None
        if role_cls not in ROLE_CLASS_GRAPH_ROOTS:
            return None
        return cls.Snapshot.from_target(role_cls)

    @classmethod
    def facet_snapshot_storage_key(
        cls, target_cls: type, payload: FacetVertex,
    ) -> str:
        return "role_class"

    @classmethod
    def _build_payload(cls, target_cls: type[BaseRole]) -> FacetVertex:
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()

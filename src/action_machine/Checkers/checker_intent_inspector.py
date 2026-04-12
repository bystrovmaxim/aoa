# src/action_machine/checkers/checker_intent_inspector.py
"""
Checker intent inspector: checker facet snapshots for ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read method-level ``_checker_meta`` lists (attached by aspect/checker decorators)
on each **declaring** class member and emit a typed ``Snapshot`` plus
``FacetPayload`` with ``node_type="checker"``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Collection uses ``vars(target_cls)`` and ``BaseIntentInspector._unwrap_declaring_class_member``
  so property-based aspect methods expose metadata on ``fget``.
- Only callable members are considered as checker carriers (same as aspect collection).
- Facet snapshot storage key is always ``"checker"``.
- No edges are emitted from this inspector.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    _unwrap_declaring_class_member  →  getattr(func, "_checker_meta")
         │
         ▼
    Snapshot.Checker rows  →  FacetPayload(node_type="checker")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: an aspect method carries ``_checker_meta``; ``inspect`` returns a
payload listing checker rows for that method name.

Edge case: no ``_checker_meta`` on any member → ``inspect`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Does not validate checker classes at graph build time; declaration-time
validators own that contract.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Checker facet inspector module.
CONTRACT: Method-level _checker_meta → snapshot → FacetPayload.
INVARIANTS: Declaring-class scan only; storage key ``checker``.
FLOW: vars → unwrap → _checker_meta → Snapshot.Checker tuple → payload.
FAILURES: no checkers → None from inspect.
EXTENSION POINTS: runtime reads checker snapshot via coordinator cache.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.checkers.checker_intent import CheckerIntent
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload


class CheckerIntentInspector(BaseIntentInspector):
    """
    Inspector for ``CheckerIntent`` subclasses: checker facet snapshots.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for checker metadata on methods.
    CONTRACT: ``inspect`` / ``Snapshot.from_target`` when checkers exist.
    INVARIANTS: ``_target_intent`` is ``CheckerIntent``.
    AI-CORE-END
    """

    _target_intent: type = CheckerIntent

    @classmethod
    def _collect_checkers(
        cls, target_cls: type,
    ) -> tuple[CheckerIntentInspector.Snapshot.Checker, ...]:
        """
        Flatten all checker rows declared on members of ``target_cls``.

        For each declaring member with ``_checker_meta``, append normalized
        ``Checker`` rows (same shape as coordinator checker facet entries).
        """
        out: list[CheckerIntentInspector.Snapshot.Checker] = []
        for attr_name, attr_value in vars(target_cls).items():
            func = cls._unwrap_declaring_class_member(attr_value)
            if not callable(func):
                continue
            checker_list = getattr(func, "_checker_meta", None)
            if checker_list is None:
                continue
            for checker_dict in checker_list:
                out.append(
                    cls.Snapshot.Checker(
                        method_name=attr_name,
                        checker_class=checker_dict.get("checker_class", type(None)),
                        field_name=checker_dict.get("field_name", ""),
                        required=checker_dict.get("required", False),
                        extra_params={
                            k: v
                            for k, v in checker_dict.items()
                            if k not in ("checker_class", "field_name", "required")
                        },
                    ),
                )
        return tuple(out)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Frozen checker facet for one class."""

        @dataclass(frozen=True)
        class Checker:
            """One checker binding to an aspect method name."""

            method_name: str
            checker_class: type
            field_name: str
            required: bool
            extra_params: dict[str, object]

        class_ref: type
        checkers: tuple[Checker, ...]

        def to_facet_payload(self) -> FacetPayload:
            """Project snapshot into coordinator ``FacetPayload``."""
            entries = tuple(
                (
                    c.method_name,
                    c.checker_class,
                    c.field_name,
                    c.required,
                    tuple((k, v) for k, v in c.extra_params.items()),
                )
                for c in self.checkers
            )
            return FacetPayload(
                node_type="checker",
                node_name=CheckerIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=CheckerIntentInspector._make_meta(checkers=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> CheckerIntentInspector.Snapshot:
            """Build snapshot for one class."""
            return cls(
                class_ref=target_cls,
                checkers=CheckerIntentInspector._collect_checkers(target_cls),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "checker"

    @classmethod
    def _has_checker_methods_invariant(cls, target_cls: type) -> bool:
        """True when any member exposes ``_checker_meta``."""
        return bool(cls._collect_checkers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return checker payload or ``None`` when no checker metadata exists."""
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> CheckerIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no checkers."""
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Materialize ``FacetPayload`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

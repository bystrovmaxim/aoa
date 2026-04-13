# src/action_machine/compensate/compensate_intent_inspector.py
"""
Compensate intent inspector: ``@compensate`` facet snapshots for ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read method-level ``_compensate_meta`` and optional ``_required_context_keys``,
then emit a typed ``Snapshot`` and ``FacetPayload`` with
``node_type="compensator"``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Collection scans ``vars(target_cls)`` (declaring members only).
- Only callable members after property unwrapping are considered.
- Storage key for facet snapshots is always ``"compensator"``.
- No edges from this inspector.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    _unwrap_declaring_class_member  →  _compensate_meta
         │
         ▼
    Snapshot.Compensator  →  FacetPayload(node_type="compensator")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: compensating methods carry ``_compensate_meta`` → non-empty payload.

Edge case: no compensators → ``inspect`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Does not run compensation; only surfaces declaration metadata for the graph and
runtime cache.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Compensator facet inspector module.
CONTRACT: _compensate_meta → Snapshot → FacetPayload.
INVARIANTS: Declaring-class scan; key ``compensator``.
FLOW: vars → unwrap → meta → snapshot rows → payload.
FAILURES: no compensators → None from inspect.
EXTENSION POINTS: saga coordinator reads compensator snapshot from cache.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.compensate.compensate_intent import CompensateIntent
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload


class CompensateIntentInspector(BaseIntentInspector):
    """
    Inspector for ``CompensateIntent`` subclasses: compensator facet snapshots.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for ``@compensate`` declarations.
    CONTRACT: ``inspect`` when compensator metadata exists.
    INVARIANTS: ``_target_intent`` is ``CompensateIntent``.
    AI-CORE-END
    """

    _target_intent: type = CompensateIntent

    @classmethod
    def _collect_compensators(
        cls, target_cls: type,
    ) -> tuple[CompensateIntentInspector.Snapshot.Compensator, ...]:
        """
        Collect compensator methods declared on ``target_cls``.
        """
        out: list[CompensateIntentInspector.Snapshot.Compensator] = []
        for attr_name, attr_value in vars(target_cls).items():
            func = cls._unwrap_declaring_class_member(attr_value)
            if not callable(func):
                continue
            meta = getattr(func, "_compensate_meta", None)
            if meta is None:
                continue
            out.append(
                cls.Snapshot.Compensator(
                    method_name=attr_name,
                    target_aspect_name=meta.get("target_aspect_name", ""),
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(
                        getattr(func, "_required_context_keys", ()) or (),
                    ),
                ),
            )
        return tuple(out)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_intent)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Frozen ``@compensate`` facet for one class."""

        @dataclass(frozen=True)
        class Compensator:
            """One compensator method binding."""

            method_name: str
            target_aspect_name: str
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        compensators: tuple[Compensator, ...]

        def to_facet_payload(self) -> FacetPayload:
            """Project snapshot into coordinator ``FacetPayload``."""
            entries = tuple(
                CompensateIntentInspector._make_meta(
                    method_name=c.method_name,
                    target_aspect_name=c.target_aspect_name,
                    description=c.description,
                    method_ref=c.method_ref,
                    context_keys=c.context_keys,
                )
                for c in self.compensators
            )
            return FacetPayload(
                node_type="compensator",
                node_name=CompensateIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=CompensateIntentInspector._make_meta(compensators=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> CompensateIntentInspector.Snapshot:
            """Build snapshot for one class."""
            return cls(
                class_ref=target_cls,
                compensators=CompensateIntentInspector._collect_compensators(
                    target_cls,
                ),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "compensator"

    @classmethod
    def _has_compensators_invariant(cls, target_cls: type) -> bool:
        """True when any member carries ``_compensate_meta``."""
        return bool(cls._collect_compensators(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return payload or ``None`` when there are no compensators."""
        if not cls._has_compensators_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> CompensateIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no compensators."""
        if not cls._has_compensators_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Materialize ``FacetPayload`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

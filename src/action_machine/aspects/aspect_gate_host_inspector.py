# src/action_machine/aspects/aspect_gate_host_inspector.py
"""
Aspect gate-host inspector for aspect facet snapshots.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect aspect declaration metadata from target classes and convert it into the
coordinator-facing ``FacetPayload`` with node type ``"aspect"``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Decorators write ``_new_aspect_meta`` on methods. This inspector reads those
attributes, normalizes entries into typed snapshot records, and exports a
payload node with tuple-encoded aspect entries. No edges are produced here.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Class is inspected only when aspect methods exist.
- Snapshot preserves declaration order for non-``BaseAction`` classes.
- Facet snapshot storage key is always ``"aspect"``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
- Class declares methods decorated with ``@regular_aspect``/``@summary_aspect``.
- Inspector emits ``FacetPayload`` with ``node_type="aspect"`` and populated
  ``node_meta["aspects"]`` tuple.

Edge case:
- Class has no aspect metadata -> ``inspect(...)`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module expects decorator metadata to be already validated by declaration
and gate-host validation layers. It does not enforce business semantics.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect inspector module.
CONTRACT: Convert method-level aspect metadata into deterministic aspect facet payload.
INVARIANTS: inspect only classes with aspect methods; emit node_type "aspect"; no edges.
FLOW: class methods -> Snapshot.Aspect tuple -> FacetPayload(node_meta["aspects"]).
FAILURES: returns None when class has no aspects; no runtime execution happens here.
EXTENSION POINTS: payload consumed by coordinator and compatible inspectors.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_gate_host_inspector import BaseGateHostInspector
from action_machine.metadata.payload import FacetPayload


class AspectGateHostInspector(BaseGateHostInspector):
    """
    Public inspector for aspect gate-host classes.

    ═══════════════════════════════════════════════════════════════════════════
    AI-CORE-BEGIN
    ═══════════════════════════════════════════════════════════════════════════
    ROLE: Framework inspector contract.
    CONTRACT: Produce aspect facet snapshot/payload for classes using aspect decorators.
    INVARIANTS: target mixin is AspectGateHost; storage key remains "aspect".
    FLOW: collect -> snapshot -> payload.
    FAILURES: no-aspect classes are filtered out by invariant checks.
    EXTENSION POINTS: subclasses can adapt collection/build strategy.
    AI-CORE-END
    ═══════════════════════════════════════════════════════════════════════════
    """

    _target_mixin: type = AspectGateHost

    @classmethod
    def _collect_aspects(cls, target_cls: type) -> tuple[Snapshot.Aspect, ...]:
        """
        Collect normalized aspect entries from a target class.

        ═══════════════════════════════════════════════════════════════════════
        AI-CORE-BEGIN
        ═══════════════════════════════════════════════════════════════════════
        PURPOSE: extract declaration metadata for coordinator-ready snapshots.
        INPUT/OUTPUT: target class -> tuple of typed Aspect entries.
        SIDE EFFECTS: none.
        FAILURES: no exceptions by design for absent metadata; returns empty tuple.
        ORDER: called before inspect/build/snapshot emission.
        AI-CORE-END
        ═══════════════════════════════════════════════════════════════════════
        """
        from action_machine.core.base_action import BaseAction

        if issubclass(target_cls, BaseAction):
            return tuple(target_cls.scratch_aspects())
        out: list[AspectGateHostInspector.Snapshot.Aspect] = []
        for attr_name, attr_value in vars(target_cls).items():
            func: Any = attr_value.fget if isinstance(attr_value, property) and attr_value.fget else attr_value
            meta = getattr(func, "_new_aspect_meta", None)
            if meta is None:
                continue
            out.append(
                cls.Snapshot.Aspect(
                    method_name=attr_name,
                    aspect_type=meta["type"],
                    description=meta.get("description", ""),
                    method_ref=func,
                    context_keys=frozenset(getattr(func, "_required_context_keys", ())),
                ),
            )
        return tuple(out)

    @classmethod
    def _subclasses_recursive(cls) -> list[type]:
        return cls._collect_subclasses(cls._target_mixin)

    @dataclass(frozen=True)
    class Snapshot(BaseFacetSnapshot):
        """Typed aspect facet for class-level aspect entries."""

        @dataclass(frozen=True)
        class Aspect:
            method_name: str
            aspect_type: str
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        aspects: tuple[Aspect, ...]

        def to_facet_payload(self) -> FacetPayload:
            """Convert typed snapshot into coordinator ``FacetPayload`` node."""
            entries = tuple(
                (
                    a.aspect_type,
                    a.method_name,
                    a.description,
                    a.method_ref,
                    a.context_keys,
                )
                for a in self.aspects
            )
            return FacetPayload(
                node_type="aspect",
                node_name=AspectGateHostInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=AspectGateHostInspector._make_meta(aspects=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> AspectGateHostInspector.Snapshot:
            """Build typed aspect snapshot for one class."""
            return cls(
                class_ref=target_cls,
                aspects=AspectGateHostInspector._collect_aspects(target_cls),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "aspect"

    @classmethod
    def _has_aspect_methods_invariant(cls, target_cls: type) -> bool:
        """Return True when target class declares at least one aspect."""
        return bool(cls._collect_aspects(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return aspect payload or ``None`` when target has no aspects."""
        if not cls._has_aspect_methods_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> AspectGateHostInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when target has no aspects."""
        if not cls._has_aspect_methods_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Build aspect payload from typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

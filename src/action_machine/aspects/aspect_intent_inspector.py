# src/action_machine/aspects/aspect_intent_inspector.py
"""
Aspect intent inspector: aspect facet snapshots for ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect per-class aspect declarations (``@regular_aspect`` / ``@summary_aspect``)
from method-level scratch (``_new_aspect_meta``) and expose them as a typed
``Snapshot`` plus coordinator ``FacetPayload`` with ``node_type="aspect"``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Only classes that declare at least one aspect produce a payload; otherwise
  ``inspect`` / ``facet_snapshot_for_class`` return ``None``.
- Collection reads **declaring** class members via ``vars(target_cls)`` (same
  surface decorators attach to); order follows iteration order of that mapping.
- Facet snapshot storage key is always ``"aspect"``.
- No graph edges are emitted from this inspector.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    BaseIntentInspector._unwrap_declaring_class_member
         │
         ▼
    getattr(func, "_new_aspect_meta") → Snapshot.Aspect
         │
         ▼
    Snapshot.to_facet_payload()  →  FacetPayload(node_type="aspect")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: a class defines ``@regular_aspect`` / ``@summary_aspect`` methods;
``inspect(target_cls)`` returns a payload whose ``node_meta`` carries aspect
entries.

Edge case: no aspect metadata on the class → ``inspect`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Assumes decorators already validated declarations. This module does not run
aspects or enforce runtime semantics.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Aspect facet inspector module.
CONTRACT: Declarative aspect metadata → typed snapshot → ``FacetPayload``.
INVARIANTS: Single facet key ``aspect``; collection from declaring class dict only.
FLOW: vars → unwrap → _new_aspect_meta → Snapshot → payload.
FAILURES: absent metadata → None from inspect; no exceptions for empty classes.
EXTENSION POINTS: coordinator and machine consume cached snapshots.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.aspects.aspect_intent import AspectIntent
from action_machine.metadata.base_facet_snapshot import BaseFacetSnapshot
from action_machine.metadata.base_intent_inspector import BaseIntentInspector
from action_machine.metadata.payload import FacetPayload


class AspectIntentInspector(BaseIntentInspector):
    """
    Inspector for ``AspectIntent`` subclasses: builds aspect facet snapshots.

    AI-CORE-BEGIN
    ROLE: Concrete intent inspector for aspects.
    CONTRACT: ``inspect`` / ``Snapshot.from_target`` for classes with aspects.
    INVARIANTS: ``_target_intent`` is ``AspectIntent``; storage key ``aspect``.
    AI-CORE-END
    """

    _target_intent: type = AspectIntent

    @classmethod
    def _collect_aspects(cls, target_cls: type) -> tuple[AspectIntentInspector.Snapshot.Aspect, ...]:
        """
        Collect aspect entries declared on ``target_cls`` (own ``__dict__`` / ``vars``).

        Walks declaring members only; reads ``_new_aspect_meta`` and optional
        ``_required_context_keys`` on unwrapped callables.
        """
        out: list[AspectIntentInspector.Snapshot.Aspect] = []
        for attr_name, attr_value in vars(target_cls).items():
            func = cls._unwrap_declaring_class_member(attr_value)
            if not callable(func):
                continue
            meta = getattr(func, "_new_aspect_meta", None)
            if meta is None:
                continue
            out.append(
                cls.Snapshot.Aspect(
                    method_name=attr_name,
                    aspect_type=meta["type"],
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
        """Frozen aspect facet: class ref plus ordered aspect rows."""

        @dataclass(frozen=True)
        class Aspect:
            """One aspect method after decorator normalization."""

            method_name: str
            aspect_type: str
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        aspects: tuple[Aspect, ...]

        def to_facet_payload(self) -> FacetPayload:
            """Project snapshot into a coordinator ``FacetPayload`` node."""
            entries = tuple(
                AspectIntentInspector._make_meta(
                    aspect_type=a.aspect_type,
                    method_name=a.method_name,
                    description=a.description,
                    method_ref=a.method_ref,
                    context_keys=a.context_keys,
                )
                for a in self.aspects
            )
            return FacetPayload(
                node_type="aspect",
                node_name=AspectIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=AspectIntentInspector._make_meta(aspects=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> AspectIntentInspector.Snapshot:
            """Build a snapshot for one concrete action (or aspect host) class."""
            return cls(
                class_ref=target_cls,
                aspects=AspectIntentInspector._collect_aspects(target_cls),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "aspect"

    @classmethod
    def _has_aspect_methods_invariant(cls, target_cls: type) -> bool:
        """True when ``target_cls`` declares at least one aspect method."""
        return bool(cls._collect_aspects(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return aspect payload or ``None`` when the class has no aspects."""
        if not cls._has_aspect_methods_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> AspectIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no aspects."""
        if not cls._has_aspect_methods_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Materialize ``FacetPayload`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

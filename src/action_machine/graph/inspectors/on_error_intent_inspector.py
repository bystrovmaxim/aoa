# src/action_machine/graph/inspectors/on_error_intent_inspector.py
"""
On-error intent inspector: ``@on_error`` facet snapshots for ``GateCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect method-level ``_on_error_meta`` and optional ``_required_context_keys``,
normalize exception types into tuples, and emit ``FacetPayload`` with
``node_type="error_handler"``.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Collection scans ``vars(target_cls)`` only (declaring members).
- Only callable members after property unwrapping are considered.
- Facet snapshot storage key is always ``"error_handler"``.
- No edges from this inspector.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    _unwrap_declaring_class_member  →  _on_error_meta
         │
         ▼
    normalize exception_types  →  Snapshot.ErrorHandler
         │
         ▼
    FacetPayload(node_type="error_handler")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: a method has ``@on_error`` metadata → payload lists handler rows.

Edge case: no handlers → ``inspect`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Does not invoke handlers; metadata shape is trusted from decorators.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: On-error facet inspector module.
CONTRACT: _on_error_meta → typed handlers → FacetPayload.
INVARIANTS: Declaring-class scan; key ``error_handler``.
FLOW: vars → unwrap → meta → Snapshot → payload.
FAILURES: no handlers → None from inspect.
EXTENSION POINTS: machine resolves handlers from coordinator snapshot at runtime.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.graph.base_facet_snapshot import BaseFacetSnapshot
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.payload import FacetPayload
from action_machine.intents.on_error.on_error_intent import OnErrorIntent


class OnErrorIntentInspector(BaseIntentInspector):
    """
    Inspector for ``OnErrorIntent`` subclasses: error-handler facet snapshots.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for ``@on_error`` declarations.
    CONTRACT: ``inspect`` when ``_on_error_meta`` exists on a member.
    INVARIANTS: ``_target_intent`` is ``OnErrorIntent``.
    AI-CORE-END
    """

    _target_intent: type = OnErrorIntent

    @classmethod
    def _collect_error_handlers(
        cls, target_cls: type,
    ) -> tuple[OnErrorIntentInspector.Snapshot.ErrorHandler, ...]:
        """
        Collect all ``@on_error`` handlers declared on ``target_cls``.
        """
        out: list[OnErrorIntentInspector.Snapshot.ErrorHandler] = []
        for attr_name, attr_value in vars(target_cls).items():
            func = cls._unwrap_declaring_class_member(attr_value)
            if not callable(func):
                continue
            meta = getattr(func, "_on_error_meta", None)
            if meta is None:
                continue
            exc_types = meta.get("exception_types", ())
            if isinstance(exc_types, type):
                exc_types_t = (exc_types,)
            else:
                exc_types_t = tuple(exc_types)
            out.append(
                cls.Snapshot.ErrorHandler(
                    method_name=attr_name,
                    exception_types=exc_types_t,
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
        """Frozen ``@on_error`` facet for one class."""

        @dataclass(frozen=True)
        class ErrorHandler:
            """One error handler method binding."""

            method_name: str
            exception_types: tuple[type[Exception], ...]
            description: str
            method_ref: object
            context_keys: frozenset[str]

        class_ref: type
        error_handlers: tuple[ErrorHandler, ...]

        def to_facet_payload(self) -> FacetPayload:
            """Project snapshot into coordinator ``FacetPayload``."""
            entries = tuple(
                OnErrorIntentInspector._make_meta(
                    method_name=h.method_name,
                    exception_types=h.exception_types,
                    description=h.description,
                    method_ref=h.method_ref,
                    context_keys=h.context_keys,
                )
                for h in self.error_handlers
            )
            return FacetPayload(
                node_type="error_handler",
                node_name=OnErrorIntentInspector._make_node_name(self.class_ref),
                node_class=self.class_ref,
                node_meta=OnErrorIntentInspector._make_meta(error_handlers=entries),
                edges=(),
            )

        @classmethod
        def from_target(cls, target_cls: type) -> OnErrorIntentInspector.Snapshot:
            """Build snapshot for one class."""
            return cls(
                class_ref=target_cls,
                error_handlers=OnErrorIntentInspector._collect_error_handlers(
                    target_cls,
                ),
            )

    @classmethod
    def facet_snapshot_storage_key(
        cls, _target_cls: type, _payload: FacetPayload,
    ) -> str:
        return "error_handler"

    @classmethod
    def _has_error_handlers_invariant(cls, target_cls: type) -> bool:
        """True when any member carries ``_on_error_meta``."""
        return bool(cls._collect_error_handlers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetPayload | None:
        """Return payload or ``None`` when the class has no error handlers."""
        if not cls._has_error_handlers_invariant(target_cls):
            return None
        return cls._build_payload(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> OnErrorIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no handlers."""
        if not cls._has_error_handlers_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetPayload:
        """Materialize ``FacetPayload`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_payload()

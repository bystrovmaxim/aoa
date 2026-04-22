# src/action_machine/legacy/on_error_intent_inspector.py
"""
On-error intent inspector: ``@on_error`` facet snapshots for ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect method-level ``_on_error_meta`` and optional ``_required_context_keys``,
normalize exception types into tuples, and emit **one ``FacetVertex`` per
handler** (``node_type="error_handler"``, name ``{action}:{method_name}``) plus a
canonical **``action``** row for the host class with informational
``has_error_handler`` edges to those handler nodes (no aggregate
``…:error_handlers`` vertex).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
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
    FacetVertex(node_type="error_handler", … host:method) + FacetVertex(action + edges)

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from action_machine.legacy.interchange_vertex_labels import ACTION_VERTEX_TYPE
from action_machine.intents.on_error.on_error_intent import OnErrorIntent
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge, FacetMetaRow
from graph.facet_vertex import FacetVertex


class OnErrorIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete inspector for ``@on_error`` declarations.
    CONTRACT: ``inspect`` emits handler vertices + ``action`` edges when ``_on_error_meta`` exists.
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

    @staticmethod
    def _handler_row_facet_meta(
        h: OnErrorIntentInspector.Snapshot.ErrorHandler,
    ) -> FacetMetaRow:
        """One handler row as ``FacetMetaRow`` (same shape as legacy aggregate entries)."""
        return OnErrorIntentInspector._make_meta(
            method_name=h.method_name,
            exception_types=h.exception_types,
            description=h.description,
            method_ref=h.method_ref,
            context_keys=h.context_keys,
        )

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

        def to_facet_vertex(self) -> FacetVertex:
            """Aggregate meta only (used for snapshot hydration / ``get_snapshot`` consumers)."""
            entries = tuple(
                OnErrorIntentInspector._handler_row_facet_meta(h)
                for h in self.error_handlers
            )
            return FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
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
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "error_handler"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls, _target_cls: type, payload: FacetVertex,
    ) -> bool:
        """Hydrate aggregate ``error_handler`` snapshot onto the canonical ``action`` node only."""
        return payload.node_type == ACTION_VERTEX_TYPE

    @classmethod
    def _has_error_handlers_invariant(cls, target_cls: type) -> bool:
        """True when any member carries ``_on_error_meta``."""
        return bool(cls._collect_error_handlers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> list[FacetVertex] | None:
        """
        Return per-handler ``error_handler`` vertices, then one ``action`` row with edges.

        Order matches :class:`SensitiveIntentInspector` (children before host) so
        phase-1 snapshot bookkeeping stays stable.
        """
        handlers = cls._collect_error_handlers(target_cls)
        if not handlers:
            return None
        out: list[FacetVertex] = []
        host_edges: list[FacetEdge] = []
        for h in handlers:
            child_name = cls._make_host_dependent_node_name(target_cls, h.method_name)
            out.append(
                FacetVertex(
                    node_type="error_handler",
                    node_name=child_name,
                    node_class=target_cls,
                    node_meta=cls._handler_row_facet_meta(h),
                    edges=(),
                ),
            )
            host_edges.append(
                FacetEdge(
                    target_node_type="error_handler",
                    target_name=child_name,
                    edge_type="has_error_handler",
                    is_structural=False,
                    target_class_ref=target_cls,
                ),
            )
        out.append(
            FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
                node_name=cls._make_node_name(target_cls),
                node_class=target_cls,
                node_meta=(),
                edges=tuple(host_edges),
            ),
        )
        return out

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> OnErrorIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no handlers."""
        if not cls._has_error_handlers_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """Materialize ``FacetVertex`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()


def hydrate_error_handler_row(
    row: FacetMetaRow,
) -> OnErrorIntentInspector.Snapshot.ErrorHandler:
    """
    Rebuild :class:`OnErrorIntentInspector.Snapshot.ErrorHandler` from one ``node_meta`` row.

    Normalizes ``context_keys`` to ``frozenset``; ``exception_types`` to a tuple of types.
    """
    d = dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    et = d["exception_types"]
    return OnErrorIntentInspector.Snapshot.ErrorHandler(
        method_name=d["method_name"],
        exception_types=cast("tuple[type[Exception], ...]", tuple(et)),
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )

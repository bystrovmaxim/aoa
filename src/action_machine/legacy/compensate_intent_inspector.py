# src/action_machine/legacy/compensate_intent_inspector.py
"""
Compensate intent inspector: ``@compensate`` facet snapshots for ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read method-level ``_compensate_meta`` and optional ``_required_context_keys``,
then emit **one ``FacetVertex`` per compensator method** (``node_type="Compensator"``,
name ``{action}:{method_name}``) plus a canonical **``action``** row with
informational ``has_compensator`` edges (no aggregate ``…:compensators`` vertex).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Collection scans ``vars(target_cls)`` (declaring members only).
- Only callable members after property unwrapping are considered.
- Storage key for facet snapshots is always ``"compensator"``.
- ``inspect`` returns ``list[FacetVertex]``: per-method ``compensator`` vertices
  then one ``action`` shell with ``has_compensator`` edges.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    _unwrap_declaring_class_member  →  _compensate_meta
         │
         ▼
    Snapshot.Compensator  →  per-method ``compensator`` + ``action`` + edges

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: compensating methods carry ``_compensate_meta`` → non-empty payload.

Edge case: no compensators → ``inspect`` returns ``None``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Does not execute compensation handlers; it only surfaces declaration metadata
for graph build and runtime cache lookup.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Compensator facet inspector module.
CONTRACT: _compensate_meta → per-method vertices + ``action`` edges + aggregate Snapshot.
INVARIANTS: Declaring-class scan; key ``compensator``.
FLOW: vars → unwrap → meta → snapshot rows → payload.
FAILURES: no compensators → None from inspect.
EXTENSION POINTS: saga coordinator reads compensator snapshot from cache.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.legacy.compensate_intent import CompensateIntent
from action_machine.legacy.interchange_vertex_labels import (
    ACTION_VERTEX_TYPE,
    COMPENSATOR_VERTEX_TYPE,
)
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge, FacetMetaRow
from graph.facet_vertex import FacetVertex


class CompensateIntentInspector(BaseIntentInspector):
    """
    Inspector for ``CompensateIntent`` subclasses: compensator facet snapshots.

    AI-CORE-BEGIN
    ROLE: Concrete inspector for ``@compensate`` declarations.
    CONTRACT: ``inspect`` emits per-method ``compensator`` nodes + ``action`` edges when metadata exists.
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

    @staticmethod
    def _compensator_row_facet_meta(
        c: CompensateIntentInspector.Snapshot.Compensator,
    ) -> FacetMetaRow:
        """One compensator row as ``FacetMetaRow`` (same shape as legacy aggregate entries)."""
        return CompensateIntentInspector._make_meta(
            method_name=c.method_name,
            target_aspect_name=c.target_aspect_name,
            description=c.description,
            method_ref=c.method_ref,
            context_keys=c.context_keys,
        )

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

        def to_facet_vertex(self) -> FacetVertex:
            """Aggregate meta for snapshot hydration / ``get_snapshot`` consumers."""
            entries = tuple(
                CompensateIntentInspector._compensator_row_facet_meta(c)
                for c in self.compensators
            )
            return FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
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
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "compensator"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls, _target_cls: type, payload: FacetVertex,
    ) -> bool:
        """Hydrate aggregate ``compensator`` snapshot onto the canonical ``action`` node only."""
        return payload.node_type == ACTION_VERTEX_TYPE

    @classmethod
    def _has_compensators_invariant(cls, target_cls: type) -> bool:
        """True when any member carries ``_compensate_meta``."""
        return bool(cls._collect_compensators(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> list[FacetVertex] | None:
        """
        Return per-method ``compensator`` vertices, then one ``action`` row with edges.

        Children-first ordering matches :class:`OnErrorIntentInspector` / ``SensitiveIntentInspector``.
        """
        compensators = cls._collect_compensators(target_cls)
        if not compensators:
            return None
        out: list[FacetVertex] = []
        host_edges: list[FacetEdge] = []
        for c in compensators:
            child_name = cls._make_host_dependent_node_name(target_cls, c.method_name)
            out.append(
                FacetVertex(
                    node_type=COMPENSATOR_VERTEX_TYPE,
                    node_name=child_name,
                    node_class=target_cls,
                    node_meta=cls._compensator_row_facet_meta(c),
                    edges=(),
                ),
            )
            host_edges.append(
                FacetEdge(
                    target_node_type=COMPENSATOR_VERTEX_TYPE,
                    target_name=child_name,
                    edge_type="has_compensator",
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
    ) -> CompensateIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no compensators."""
        if not cls._has_compensators_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """Materialize ``FacetVertex`` from the typed snapshot."""
        return cls.Snapshot.from_target(target_cls).to_facet_vertex()


def hydrate_compensator_row(
    row: FacetMetaRow,
) -> CompensateIntentInspector.Snapshot.Compensator:
    """
    Rebuild :class:`CompensateIntentInspector.Snapshot.Compensator` from one ``node_meta`` row.

    Normalizes ``context_keys`` to ``frozenset``.
    """
    d = dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    return CompensateIntentInspector.Snapshot.Compensator(
        method_name=d["method_name"],
        target_aspect_name=d["target_aspect_name"],
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )

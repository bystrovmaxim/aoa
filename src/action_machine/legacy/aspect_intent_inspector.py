# src/action_machine/legacy/aspect_intent_inspector.py
"""
Aspect intent inspector: aspect facet snapshots for ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Collect per-class aspect declarations (``@regular_aspect`` / ``@summary_aspect``)
from method-level scratch (``_new_aspect_meta``) and expose them as a typed
``Snapshot`` plus coordinator ``FacetVertex`` with ``node_type="RegularAspect"`` / ``"SummaryAspect"``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
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
    Snapshot.to_facet_vertex()  →  FacetVertex(node_type="RegularAspect" / "SummaryAspect");
    inspect()  →  per-method aspect payloads plus one action payload (has_aspect).

"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.intents.aspects.aspect_intent import AspectIntent
from action_machine.legacy.interchange_vertex_labels import (
    ACTION_VERTEX_TYPE,
    REGULAR_ASPECT_VERTEX_TYPE,
    SUMMARY_ASPECT_VERTEX_TYPE,
)
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge, FacetMetaRow
from graph.facet_vertex import FacetVertex


def vertex_type_for_aspect_kind(kind: str) -> str:
    """Interchange ``node_type`` for decorator aspect kind (``\"regular\"`` / ``\"summary\"``)."""
    if str(kind).strip() == "summary":
        return SUMMARY_ASPECT_VERTEX_TYPE
    return REGULAR_ASPECT_VERTEX_TYPE


class AspectIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete intent inspector for aspects.
    CONTRACT: ``inspect`` / ``Snapshot.from_target`` for classes with aspects.
    INVARIANTS: ``_target_intent`` is ``AspectIntent``; storage key ``aspect``;
      ``vars(target_cls)`` only—no inherited aspect merge.
    AI-CORE-END
"""

    _target_intent: type = AspectIntent

    @classmethod
    def _collect_aspects(cls, target_cls: type) -> tuple[AspectIntentInspector.Snapshot.Aspect, ...]:
        """
        Collect aspect entries declared on ``target_cls`` (own ``__dict__`` / ``vars``).

        Walks **declaring** members only (no MRO walk): each action class owns an
        explicit aspect list on its class body. Order follows ``vars`` insertion
        order. Subclasses override aspect methods and call ``super()`` when they
        need parent behavior.

        Reads ``_new_aspect_meta`` and optional ``_required_context_keys`` on
        unwrapped callables.
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
        """Frozen aspect facet: class ref plus aspect rows in own-class declaration order."""

        @dataclass(frozen=True)
        class Aspect:
            """One aspect method after decorator normalization."""

            method_name: str
            aspect_type: str
            description: str
            method_ref: Callable[..., Any]
            context_keys: frozenset[str]

        class_ref: type
        aspects: tuple[Aspect, ...]

        def to_facet_vertex(self) -> FacetVertex:
            """
            Aggregate facet row (all aspects in ``node_meta``).

            The coordinator's :meth:`inspect` emits **one** payload per aspect method
            with ``node_name = host:method``; this aggregate remains for callers that
            materialize a snapshot without going through ``GraphCoordinator``.
            """
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
            kinds = {a.aspect_type for a in self.aspects}
            if not self.aspects:
                agg_nt = REGULAR_ASPECT_VERTEX_TYPE
            elif kinds == {"summary"}:
                agg_nt = SUMMARY_ASPECT_VERTEX_TYPE
            else:
                agg_nt = REGULAR_ASPECT_VERTEX_TYPE
            return FacetVertex(
                node_type=agg_nt,
                node_name=AspectIntentInspector._make_host_dependent_node_name(
                    self.class_ref, "aspects",
                ),
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
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "aspect"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls,
        _target_cls: type,
        payload: FacetVertex,
    ) -> bool:
        """Hydrate per-method ``aspect`` nodes only; not the synthetic ``action`` shell."""
        return payload.node_type in (
            REGULAR_ASPECT_VERTEX_TYPE,
            SUMMARY_ASPECT_VERTEX_TYPE,
        )

    @classmethod
    def _has_aspect_methods_invariant(cls, target_cls: type) -> bool:
        """True when ``target_cls`` declares at least one aspect method."""
        return bool(cls._collect_aspects(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> FacetVertex | list[FacetVertex] | None:
        """Return one payload per aspect method, or ``None`` when the class has no aspects."""
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
    def _build_payload(cls, target_cls: type) -> list[FacetVertex]:
        """
        One ``FacetVertex`` per declared aspect (``class:method``) plus one ``action``
        row for the host class with ``has_aspect`` edges to each method vertex.
        """
        snap = cls.Snapshot.from_target(target_cls)
        out: list[FacetVertex] = []
        has_aspect_edges: list[FacetEdge] = []
        for a in snap.aspects:
            entries = (
                cls._make_meta(
                    aspect_type=a.aspect_type,
                    method_name=a.method_name,
                    description=a.description,
                    method_ref=a.method_ref,
                    context_keys=a.context_keys,
                ),
            )
            aspect_name = cls._make_node_name(snap.class_ref, a.method_name)
            vt = vertex_type_for_aspect_kind(a.aspect_type)
            has_aspect_edges.append(
                cls._make_edge_by_name(
                    vt,
                    aspect_name,
                    "has_aspect",
                    False,
                ),
            )
            out.append(
                FacetVertex(
                    node_type=vt,
                    node_name=aspect_name,
                    node_class=snap.class_ref,
                    node_meta=cls._make_meta(aspects=entries),
                    edges=(),
                ),
            )
        out.append(
            FacetVertex(
                node_type=ACTION_VERTEX_TYPE,
                node_name=cls._make_node_name(snap.class_ref),
                node_class=snap.class_ref,
                node_meta=(),
                edges=tuple(has_aspect_edges),
            ),
        )
        return out


def hydrate_aspect_row(row: FacetMetaRow) -> AspectIntentInspector.Snapshot.Aspect:
    """
    Rebuild :class:`AspectIntentInspector.Snapshot.Aspect` from one committed ``node_meta`` row.

    Normalizes ``context_keys`` to ``frozenset`` (iterable or empty accepted).
    """
    d = dict(row)
    ck = d["context_keys"]
    if not isinstance(ck, frozenset):
        ck = frozenset(ck or ())
    return AspectIntentInspector.Snapshot.Aspect(
        method_name=d["method_name"],
        aspect_type=d["aspect_type"],
        description=d["description"],
        method_ref=d["method_ref"],
        context_keys=ck,
    )

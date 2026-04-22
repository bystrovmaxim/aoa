# src/action_machine/legacy/checker_intent_inspector.py
"""
Checker intent inspector: checker facet snapshots for ``GraphCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Read method-level ``_checker_meta`` lists (attached by aspect/checker decorators)
on each **declaring** class member and emit a typed ``Snapshot`` plus one
``FacetVertex`` per checker row: a canonical ``Checker`` vertex per
``(aspect method, checker implementation class, field)``, an edge to the existing
aspect vertex for that method, and row metadata on the checker node.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    vars(target_cls)
         │
         ▼
    _unwrap_declaring_class_member  →  getattr(func, "_checker_meta")
         │
         ▼
    Snapshot.Checker rows  →  list[FacetVertex(node_type="Checker", …)]

"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from action_machine.legacy.aspect_intent_inspector import (
    AspectIntentInspector,
    vertex_type_for_aspect_kind,
)
from action_machine.intents.checkers.checker_intent import CheckerIntent
from action_machine.legacy.interchange_vertex_labels import CHECKER_VERTEX_TYPE
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge, FacetMetaRow
from graph.facet_vertex import FacetVertex


class CheckerIntentInspector(BaseIntentInspector):
    """
AI-CORE-BEGIN
    ROLE: Concrete inspector for checker metadata on methods.
    CONTRACT: ``inspect`` / ``Snapshot.from_target`` when checkers exist.
    INVARIANTS: ``_target_intent`` is ``CheckerIntent``.
    AI-CORE-END
"""

    _target_intent: type = CheckerIntent

    _SEGMENT_SAFE = re.compile(r"[^a-zA-Z0-9_.]+")

    @classmethod
    def _checker_impl_segment(cls, checker_class: type) -> str:
        """Stable label for checker implementation (decorator / checker class name)."""
        return checker_class.__name__

    @classmethod
    def _safe_field_segment(cls, field_name: str) -> str:
        t = field_name.strip() or "_"
        return cls._SEGMENT_SAFE.sub("_", t)

    @classmethod
    def _checker_vertex_suffix(
        cls,
        method_name: str,
        checker_class: type,
        field_name: str,
    ) -> str:
        """
        Suffix after host ``module.Class:`` — ``{method}:{CheckerClass}:{field}``.

        Matches the aspect vertex body ``module.Class:{method}`` plus checker kind and field.
        """
        impl = cls._checker_impl_segment(checker_class)
        field = cls._safe_field_segment(field_name)
        return f"{method_name}:{impl}:{field}"

    @classmethod
    def _checker_row_meta(cls, c: CheckerIntentInspector.Snapshot.Checker) -> tuple[tuple[str, Any], ...]:
        """Row shape compatible with :func:`hydrate_checker_row`."""
        return cls._make_meta(
            method_name=c.method_name,
            checker_class=c.checker_class,
            field_name=c.field_name,
            required=c.required,
            extra_params=tuple(c.extra_params.items()),
        )

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

        def to_facet_vertex(self) -> FacetVertex:
            """
            Typed snapshot projection for cache / legacy callers.

            Does not mirror per-checker graph payloads from :meth:`inspect`; graph
            rows use :meth:`CheckerIntentInspector._build_payload` instead.
            """
            return FacetVertex(
                node_type=CHECKER_VERTEX_TYPE,
                node_name=CheckerIntentInspector._make_host_dependent_node_name(
                    self.class_ref, "__checker_snapshot__",
                ),
                node_class=self.class_ref,
                node_meta=(),
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
        cls, _target_cls: type, _payload: FacetVertex,
    ) -> str:
        return "checker"

    @classmethod
    def should_register_facet_snapshot_for_vertex(
        cls,
        _target_cls: type,
        _payload: FacetVertex,
    ) -> bool:
        """Per-checker nodes hydrate from ``committed_facet_rows`` on the facet skeleton."""
        return False

    @classmethod
    def _has_checker_methods_invariant(cls, target_cls: type) -> bool:
        """True when any member exposes ``_checker_meta``."""
        return bool(cls._collect_checkers(target_cls))

    @classmethod
    def inspect(cls, target_cls: type) -> list[FacetVertex] | None:
        """Return one checker payload per row, or ``None`` when no checker metadata exists."""
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls._materialize_checker_payloads(target_cls)

    @classmethod
    def facet_snapshot_for_class(
        cls, target_cls: type,
    ) -> CheckerIntentInspector.Snapshot | None:
        """Return typed snapshot or ``None`` when there are no checkers."""
        if not cls._has_checker_methods_invariant(target_cls):
            return None
        return cls.Snapshot.from_target(target_cls)

    @classmethod
    def _build_payload(cls, target_cls: type) -> FacetVertex:
        """Satisfy ``BaseIntentInspector``; coordinator uses :meth:`inspect` for graph rows."""
        return cls._materialize_checker_payloads(target_cls)[0]

    @classmethod
    def _materialize_checker_payloads(cls, target_cls: type) -> list[FacetVertex]:
        snap = cls.Snapshot.from_target(target_cls)
        aspect_kind_by_method: dict[str, str] = {}
        for a in AspectIntentInspector._collect_aspects(snap.class_ref):
            aspect_kind_by_method[a.method_name] = a.aspect_type
        out: list[FacetVertex] = []
        for c in snap.checkers:
            suffix = cls._checker_vertex_suffix(c.method_name, c.checker_class, c.field_name)
            node_name = cls._make_node_name(snap.class_ref, suffix)
            aspect_name = cls._make_node_name(snap.class_ref, c.method_name)
            aspect_kind = aspect_kind_by_method.get(c.method_name, "regular")
            aspect_nt = vertex_type_for_aspect_kind(aspect_kind)
            edge: FacetEdge = cls._make_edge_by_name(
                aspect_nt,
                aspect_name,
                "checks_aspect",
                False,
            )
            out.append(
                FacetVertex(
                    node_type=CHECKER_VERTEX_TYPE,
                    node_name=node_name,
                    node_class=snap.class_ref,
                    node_meta=cls._checker_row_meta(c),
                    edges=(edge,),
                ),
            )
        return out


def hydrate_checker_row(row: FacetMetaRow) -> CheckerIntentInspector.Snapshot.Checker:
    """
    Rebuild :class:`CheckerIntentInspector.Snapshot.Checker` from one checker facet ``node_meta`` row.

    Accepts ``extra_params`` as ``dict`` or pair-iterable (non-dict mappings coerced via ``dict(...)``).
    """
    d = dict(row)
    extra = d["extra_params"]
    if isinstance(extra, dict):
        ep = extra
    else:
        ep = dict(extra)
    return CheckerIntentInspector.Snapshot.Checker(
        method_name=d["method_name"],
        checker_class=d["checker_class"],
        field_name=d["field_name"],
        required=bool(d["required"]),
        extra_params=ep,
    )

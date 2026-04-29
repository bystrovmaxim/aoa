# src/action_machine/intents/checkers/checker_facet.py
"""
Checker facet rows and typed snapshot for tests and tooling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Reads method-level ``_checker_meta`` (written by ``result_*`` decorators) on each
declaring member and exposes frozen rows plus :func:`hydrate_checker_row` for
``FacetMetaRow`` round-trips. Standalone from ``GraphCoordinator``: no facet
inspector registers checker rows on the interchange graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    vars(target_cls)
         │
         └─► _unwrap_declaring_class_member(func) ─► getattr(..., "_checker_meta")

"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.legacy.interchange_vertex_labels import CHECKER_VERTEX_TYPE
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetMetaRow
from graph.facet_vertex import FacetVertex


@dataclass(frozen=True)
class CheckerFacetSnapshot(BaseFacetSnapshot):
    """
AI-CORE-BEGIN
    ROLE: Typed checker facet snapshot for one action class metadata.
    CONTRACT: Frozen ``checkers`` rows mirror coordinator facet storage shape.
    INVARIANTS: Built only from `_checker_meta` on declared methods (no executor).
AI-CORE-END
"""

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
        """Minimal projection compatible with coordinator snapshot slot shape."""
        return FacetVertex(
            node_type=CHECKER_VERTEX_TYPE,
            node_name=BaseIntentInspector._make_host_dependent_node_name(
                self.class_ref, "__checker_snapshot__",
            ),
            node_class=self.class_ref,
            node_meta=(),
            edges=(),
        )


def _collect_checker_rows(target_cls: type) -> tuple[CheckerFacetSnapshot.Checker, ...]:
    """Flatten ``_checker_meta`` rows from declared aspect methods on ``target_cls``."""
    out: list[CheckerFacetSnapshot.Checker] = []
    for attr_name, attr_value in vars(target_cls).items():
        func = BaseIntentInspector._unwrap_declaring_class_member(attr_value)
        if not callable(func):
            continue
        checker_list = getattr(func, "_checker_meta", None)
        if checker_list is None:
            continue
        for checker_dict in checker_list:
            out.append(
                CheckerFacetSnapshot.Checker(
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


def facet_snapshot_for_checkers(target_cls: type) -> CheckerFacetSnapshot | None:
    """Return a typed checker facet snapshot if the class declares any checker metadata."""
    rows = _collect_checker_rows(target_cls)
    if not rows:
        return None
    return CheckerFacetSnapshot(class_ref=target_cls, checkers=rows)


def hydrate_checker_row(row: FacetMetaRow) -> CheckerFacetSnapshot.Checker:
    """
    Rebuild :class:`CheckerFacetSnapshot.Checker` from one checker facet ``node_meta`` row.

    Accepts ``extra_params`` as ``dict`` or pair-iterable (non-dict mappings coerced via ``dict(...)``).
    """
    d = dict(row)
    extra = d["extra_params"]
    ep = extra if isinstance(extra, dict) else dict(extra)
    return CheckerFacetSnapshot.Checker(
        method_name=d["method_name"],
        checker_class=d["checker_class"],
        field_name=d["field_name"],
        required=bool(d["required"]),
        extra_params=ep,
    )

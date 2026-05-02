# src/action_machine/testing/checker_facet_snapshot.py
"""
CheckerFacetSnapshot — typed checker facet rows for tooling and tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Frozen snapshot carrying checker rows when tests seed checker metadata manually.
Checker row harvesting for :class:`~action_machine.testing.bench.TestBench` lives
alongside in :mod:`action_machine.testing.bench`.

"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.legacy.interchange_vertex_labels import CHECKER_VERTEX_TYPE
from graph.base_facet_snapshot import BaseFacetSnapshot
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_vertex import FacetVertex


@dataclass(frozen=True)
class CheckerFacetSnapshot(BaseFacetSnapshot):
    """
AI-CORE-BEGIN
    ROLE: Typed checker facet snapshot for one action class metadata.
    CONTRACT: Frozen ``checkers`` rows mirror coordinator facet storage shape.
    INVARIANTS: ``checkers`` are supplied by the builder; not validated here.
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

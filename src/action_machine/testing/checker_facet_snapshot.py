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


@dataclass(frozen=True)
class CheckerFacetSnapshot:
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

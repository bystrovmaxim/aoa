# packages/maxitor/core/graph_compare/src/maxitor/graph_compare/__init__.py
"""
maxitor.graph_compare — two graph documents of the Open Gnomon Protocol, compared by ``id``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The comparison Maxitor's app and its tools share: ``compare(a, b)`` gives every
node and edge of two documents a status — added, removed, changed, unchanged —,
every difference of a changed one by property path, and the counts. It reads any
two documents, wherever they come from, and knows nothing about AOA or any
language.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The part needs nothing beyond the standard library and imports nothing of AOA,
the front or a tool; ``scripts/check_package_boundaries.py`` and its own test
``test_graph_compare_boundary.py`` enforce it, so ``pip install maxitor`` with no
extra is enough to use it.
"""

from maxitor.graph_compare.compare import KNOWN_VERSIONS, compare
from maxitor.graph_compare.comparison import (
    Change,
    Comparison,
    Counts,
    Difference,
    ElementComparison,
    GraphNotComparableError,
    Status,
)

__all__ = [
    "KNOWN_VERSIONS",
    "Change",
    "Comparison",
    "Counts",
    "Difference",
    "ElementComparison",
    "GraphNotComparableError",
    "Status",
    "compare",
]

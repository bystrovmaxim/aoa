# src/action_machine/graph/constants.py
"""
Graph constants: edge-type sets for interchange classification (``graph.md`` §5–6).

Interchange **vertex** ``node_type`` strings are opaque to this package; a separate
catalog for the default inspector suite lives in
:mod:`action_machine.interchange_vertex_catalog`.
"""

from __future__ import annotations

from typing import Final

# graph.md §5.1 — ownership edges.
OWNERSHIP_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "HAS_ASPECT",
        "HAS_COMPENSATOR",
        "HAS_ERROR_HANDLER",
        "HAS_CHECKER",
        "HAS_SENSITIVE_FIELD",
        "HAS_PARAMS",
        "HAS_RESULT",
        "HAS_SUBSCRIPTION",
        "HAS_LIFECYCLE",
        "HAS_LIFECYCLE_STATE",
    },
)

# graph.md §5.2 — internal edges.
INTERNAL_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "CHECKS_ASPECT",
        "COMPENSATES_ASPECT",
    },
)

# graph.md §6 — edges that participate in DAG checks on the interchange graph.
# Only structural wiring rows with ``is_dag=True`` use these interchange ``edge_type``
# values. Other interchange edge kinds use ``is_dag=False`` and are excluded from this slice.
DAG_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "DEPENDS_ON",
        "CONNECTS_TO",
    },
)

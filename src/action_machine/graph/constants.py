# src/action_machine/graph/constants.py
"""
Graph constants and ``REVERSE_EDGE_MAP`` (``graph.md`` v4.1 §2.1, §5–6).

Centralize allowed interchange ``node_type`` values / edge-type sets and the canonical reverse map
for §5.3 **direct** edges so builders and tests do not duplicate literals.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

# graph.md §2.1 — interchange vertex types (business layer elements).
VERTEX_TYPES: Final[frozenset[str]] = frozenset(
    {
        "Action",
        "RegularAspect",
        "SummaryAspect",
        "compensator",
        "error_handler",
        "checker",
        "sensitive_field",
        "role_class",
        "Application",
        "domain",
        "entity",
        "lifecycle",
        "lifecycle_state_initial",
        "lifecycle_state_intermediate",
        "lifecycle_state_final",
        "params_schema",
        "result_schema",
        "service",
        "resource_manager",
        "plugin",
        "subscription",
    },
)

# graph.md §5.1 — ownership edges (no automatic reverse).
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

# graph.md §5.2 — internal edges (no automatic reverse).
INTERNAL_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "CHECKS_ASPECT",
        "COMPENSATES_ASPECT",
    },
)

# graph.md §6 — edges that participate in DAG checks on the interchange graph.
# Structural service/connection wiring only. Entity–entity UML edges
# (``COMPOSITION_*``, ``AGGREGATION_*``, ``ASSOCIATION_*`` and their §5.3 reverses)
# are **not** listed here: they may form cycles (e.g. mutual references) and are
# validated separately from this acyclicity slice (``is_dag`` is false on those rows).
DAG_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "DEPENDS_ON",
        "CONNECTS_TO",
    },
)

# graph.md §11.4 — direct → reverse for §5.3 autonomous vertex pairs.
_REVERSE_EDGE_MAP_RAW: Final[dict[str, str]] = {
    "BELONGS_TO": "CONTAINS",
    "ASSIGNED_TO": "REQUIRES_ROLE",
    "DEPENDS_ON": "DEPENDED_BY",
    "CONNECTS_TO": "SERVES",
    "SUBSCRIBES_TO": "EMITS_EVENTS_FOR",
    "IMPLIES": "IMPLIED_BY",
    "COMPOSITION_ONE": "COMPOSED_IN_ONE",
    "COMPOSITION_MANY": "COMPOSED_IN_MANY",
    "AGGREGATION_ONE": "AGGREGATED_IN_ONE",
    "AGGREGATION_MANY": "AGGREGATED_IN_MANY",
    "ASSOCIATION_ONE": "ASSOCIATED_FROM_ONE",
    "ASSOCIATION_MANY": "ASSOCIATED_FROM_MANY",
}

REVERSE_EDGE_MAP: Final[Mapping[str, str]] = MappingProxyType(_REVERSE_EDGE_MAP_RAW)

# graph.md §5.3 — **Stereotype** label on the **reverse** edge (reverse column of the edge table).
_REVERSE_STEREOTYPE_RAW: Final[dict[str, str]] = {
    "BELONGS_TO": "Aggregation",
    "ASSIGNED_TO": "Access",
    "DEPENDS_ON": "Serving",
    "CONNECTS_TO": "Flow",
    "SUBSCRIBES_TO": "Triggering",
    "IMPLIES": "Specialization",
    "COMPOSITION_ONE": "Composition",
    "COMPOSITION_MANY": "Composition",
    "AGGREGATION_ONE": "Aggregation",
    "AGGREGATION_MANY": "Aggregation",
    "ASSOCIATION_ONE": "Association",
    "ASSOCIATION_MANY": "Association",
}

REVERSE_EDGE_STEREOTYPE: Final[Mapping[str, str]] = MappingProxyType(_REVERSE_STEREOTYPE_RAW)

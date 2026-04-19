# tests/graph_contract/test_constants_and_parsing.py

"""
Unit tests: interchange vertex catalog and edge-type sets.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock graph interchange constants independent of ``GraphCoordinator``.
"""

from __future__ import annotations

from action_machine.graph import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
)
from action_machine.legacy.interchange_vertex_catalog import INTERCHANGE_KNOWN_VERTEX_TYPES


def test_vertex_types_contains_core_kinds() -> None:
    types = INTERCHANGE_KNOWN_VERTEX_TYPES
    assert "Action" in types
    assert "Domain" in types
    assert "Checker" in types
    assert "Compensator" in types
    assert "lifecycle_state_initial" in types
    assert "params_schema" in types
    assert len(types) == 21


def test_ownership_internal_and_dag_sets_disjoint() -> None:
    assert OWNERSHIP_EDGE_TYPES.isdisjoint(INTERNAL_EDGE_TYPES)
    assert OWNERSHIP_EDGE_TYPES.isdisjoint(DAG_EDGE_TYPES)
    assert INTERNAL_EDGE_TYPES.isdisjoint(DAG_EDGE_TYPES)


def test_dag_edge_types_expected() -> None:
    assert DAG_EDGE_TYPES == frozenset({"DEPENDS_ON", "CONNECTS_TO"})

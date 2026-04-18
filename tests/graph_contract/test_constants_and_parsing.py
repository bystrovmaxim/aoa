# tests/graph_contract/test_constants_and_parsing.py

"""
Unit tests: interchange vertex catalog, edge-type sets, vertex-id parsing helpers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock graph interchange constants and pure helpers independent of ``GraphCoordinator``.
"""

from __future__ import annotations

import pytest

from action_machine.graph import (
    DAG_EDGE_TYPES,
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
    split_checker_vertex_id,
    split_host_element_vertex_id,
)
from action_machine.interchange_vertex_catalog import INTERCHANGE_KNOWN_VERTEX_TYPES


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


def test_split_checker_vertex_id_ok() -> None:
    vid = "myapp.actions.CreateOrderAction.validate_data_aspect:txn_id"
    host, method, field = split_checker_vertex_id(vid)
    assert host == "myapp.actions.CreateOrderAction"
    assert method == "validate_data_aspect"
    assert field == "txn_id"


@pytest.mark.parametrize(
    "bad",
    [
        "no.colon.here",
        "two:colons:here",
        ":onlyfield",
        "onlyhost:",
    ],
)
def test_split_checker_vertex_id_rejects(bad: str) -> None:
    with pytest.raises(ValueError):
        split_checker_vertex_id(bad)


def test_split_host_element_vertex_id_ok() -> None:
    host, element = split_host_element_vertex_id("myapp.actions.CreateOrderAction.validate_data_aspect")
    assert host == "myapp.actions.CreateOrderAction"
    assert element == "validate_data_aspect"


def test_split_host_element_vertex_id_rejects_colon() -> None:
    with pytest.raises(ValueError):
        split_host_element_vertex_id("host.method:field")

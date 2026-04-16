# tests/graph_logical_contract/test_logical_dag_coordinator_invariant.py

"""C3-style: built coordinator logical graph has an acyclic DAG slice."""

from __future__ import annotations

import importlib

import pytest

from action_machine.graph.logical import logical_dag_subgraph_is_acyclic_from_rx
from maxitor.test_domain.build import _MODULES, build_test_coordinator


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


@pytest.mark.graph_coverage
def test_built_logical_graph_dag_slice_is_acyclic() -> None:
    _import_test_domain_modules()
    lg = build_test_coordinator().get_logical_graph()
    assert logical_dag_subgraph_is_acyclic_from_rx(lg) is True

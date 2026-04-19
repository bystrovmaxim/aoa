# tests/graph_contract/test_dag_coordinator_invariant.py

"""C3-style: built coordinator interchange graph has an acyclic DAG slice."""

from __future__ import annotations

import importlib

import pytest

from graph import dag_subgraph_is_acyclic_from_rx
from maxitor.samples.build import _MODULES, build_sample_coordinator


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


@pytest.mark.graph_coverage
def test_built_interchange_graph_dag_slice_is_acyclic() -> None:
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    assert dag_subgraph_is_acyclic_from_rx(lg) is True

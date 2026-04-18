# tests/graph_contract/test_reverse_edge_pairs.py

"""Interchange edge categories: no ``category="reverse"`` rows (forward projection only)."""

from __future__ import annotations

import importlib

import pytest

from action_machine.graph import INTERNAL_EDGE_TYPES, OWNERSHIP_EDGE_TYPES
from maxitor.samples.build import _MODULES, build_sample_coordinator


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


@pytest.mark.graph_coverage
def test_interchange_graph_has_no_reverse_category_edges() -> None:
    """Interchange graph never uses ``category="reverse"``."""
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    for _s, _t, w in lg.weighted_edge_list():
        assert w.get("category") != "reverse", w


@pytest.mark.graph_coverage
def test_ownership_edges_use_ownership_category_when_present() -> None:
    """§5.1: any ``HAS_*`` edge must use ``category=ownership`` (no reverse pair)."""
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    for _s, _t, w in lg.weighted_edge_list():
        if w["edge_type"] in OWNERSHIP_EDGE_TYPES:
            assert w["category"] == "ownership", w


@pytest.mark.graph_coverage
def test_internal_edges_use_internal_category_when_present() -> None:
    """§5.2: internal edge types use ``category=internal``."""
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    for _s, _t, w in lg.weighted_edge_list():
        if w["edge_type"] in INTERNAL_EDGE_TYPES:
            assert w["category"] == "internal", w


@pytest.mark.graph_coverage
def test_no_reverse_category_on_ownership_or_internal_types() -> None:
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    forbidden_reverse = OWNERSHIP_EDGE_TYPES | INTERNAL_EDGE_TYPES
    for _s, _t, w in lg.weighted_edge_list():
        assert not (
            w["edge_type"] in forbidden_reverse and w["category"] == "reverse"
        ), f"unexpected reverse for {w['edge_type']}: {w}"

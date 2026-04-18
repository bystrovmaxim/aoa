# tests/graph_contract/test_reverse_edge_pairs.py

"""§5.3: every ``direct`` edge in ``REVERSE_EDGE_MAP`` has a paired ``reverse`` edge."""

from __future__ import annotations

import importlib

import pytest
import rustworkx as rx

from action_machine.graph import (
    INTERNAL_EDGE_TYPES,
    OWNERSHIP_EDGE_TYPES,
    REVERSE_EDGE_MAP,
)
from maxitor.samples.build import _MODULES, build_sample_coordinator


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def _edge_quads(lg: rx.PyDiGraph) -> set[tuple[str, str, str, str]]:
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    out: set[tuple[str, str, str, str]] = set()
    for s, t, w in lg.weighted_edge_list():
        out.add(
            (
                id_by_idx[s],
                id_by_idx[t],
                w["edge_type"],
                w["category"],
            ),
        )
    return out


@pytest.mark.graph_coverage
def test_each_mapped_direct_edge_has_reverse_pair() -> None:
    _import_test_domain_modules()
    lg = build_sample_coordinator().get_graph()
    quads = _edge_quads(lg)
    id_by_idx = {i: lg[i]["id"] for i in lg.node_indices()}
    for s, t, w in lg.weighted_edge_list():
        if w["category"] != "direct":
            continue
        fwd = w["edge_type"]
        if fwd not in REVERSE_EDGE_MAP:
            continue
        rev_type = REVERSE_EDGE_MAP[fwd]
        src, tgt = id_by_idx[s], id_by_idx[t]
        assert (tgt, src, rev_type, "reverse") in quads, (
            f"missing reverse for direct {fwd}: ({src!r} -> {tgt!r})"
        )


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

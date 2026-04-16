# tests/graph_logical_contract/test_pr2_logical_graph_builder.py

"""
``LogicalGraphBuilder``: G0 delegation + narrow ``FacetPayload`` projection vs golden G0.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.logical import LogicalEdge, LogicalGraphBuilder, LogicalVertex
from action_machine.graph.payload import EdgeInfo, FacetPayload

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "logical_minimal.json"


def _stub_class(module: str, short: str) -> type:
    t = type(short, (), {})
    t.__module__ = module
    t.__qualname__ = short
    return t


def _g0_demo_types() -> tuple[type, type, type]:
    """Types whose ``__module__`` / ``__qualname__`` match ``logical_minimal.json`` ids."""
    domain = _stub_class("golden_demo.domains", "DemoDomain")
    action = _stub_class("golden_demo.actions", "DemoAction")
    role = _stub_class("golden_demo.roles", "DemoRole")
    return domain, action, role


def _g0_facet_payloads() -> tuple[FacetPayload, ...]:
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge(
        "domain",
        demo_domain,
        "belongs_to",
        False,
    )
    return (
        FacetPayload(
            node_type="domain",
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(display_name="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=(),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetPayload(
            node_type="role",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(),
        ),
    )


def _canonical_vertices(vertices: list[LogicalVertex]) -> list[dict]:
    rows = [asdict(v) for v in vertices]
    return sorted(rows, key=lambda r: r["id"])


def _canonical_edges(edges: list[LogicalEdge]) -> list[dict]:
    rows = [asdict(e) for e in edges]
    return sorted(
        rows,
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_logical_graph_builder_synthetic_g0_matches_fixture() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = raw["input"]
    expected = raw["expected"]

    vertices, edges = LogicalGraphBuilder.build(synthetic_g0=inp)

    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_logical_graph_builder_facet_payloads_match_fixture() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = raw["expected"]

    vertices, edges = LogicalGraphBuilder.build(facet_payloads=_g0_facet_payloads())

    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_logical_graph_builder_rejects_no_source() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        LogicalGraphBuilder.build()


def test_logical_graph_builder_rejects_both_sources() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        LogicalGraphBuilder.build(synthetic_g0={}, facet_payloads=_g0_facet_payloads())


def test_facet_projection_rejects_duplicate_action_id_as_domain() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    shared = BaseIntentInspector._make_node_name(demo_action)
    payloads = (
        FacetPayload(
            node_type="domain",
            node_name=shared,
            node_class=demo_domain,
            node_meta=(),
            edges=(),
        ),
        FacetPayload(
            node_type="action",
            node_name=shared,
            node_class=demo_action,
            node_meta=(),
            edges=(),
        ),
    )
    with pytest.raises(ValueError, match="duplicate vertex id"):
        LogicalGraphBuilder.build(facet_payloads=payloads)


def test_facet_empty_payloads_yield_empty_graph() -> None:
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=())
    assert vertices == []
    assert edges == []


def test_facet_payload_order_is_canonicalized() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = raw["expected"]
    shuffled = (
        _g0_facet_payloads()[2],
        _g0_facet_payloads()[3],
        _g0_facet_payloads()[0],
        _g0_facet_payloads()[1],
    )
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=shuffled)
    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_facet_meta_without_separate_action_row_matches_golden() -> None:
    """Coordinator may omit a standalone ``action`` facet when ``meta`` already names the action."""
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge("domain", demo_domain, "belongs_to", False)
    payloads = (
        FacetPayload(
            node_type="domain",
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(display_name="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetPayload(
            node_type="role",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(),
        ),
    )
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = raw["expected"]
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=payloads)
    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_facet_role_spec_non_type_skips_assigned_edges() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge("domain", demo_domain, "belongs_to", False)
    payloads = (
        FacetPayload(
            node_type="domain",
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(display_name="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=(),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="x", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetPayload(
            node_type="role",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec="not-a-type"),
            edges=(),
        ),
    )
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=payloads)
    assert len(vertices) == 2
    assert {v.vertex_type for v in vertices} == {"domain", "action"}
    assert len(edges) == 2
    assert all(e.edge_type in ("BELONGS_TO", "CONTAINS") for e in edges)


def test_facet_belongs_to_empty_target_name_raises() -> None:
    _, demo_action, _ = _g0_demo_types()
    action_name = BaseIntentInspector._make_node_name(demo_action)
    bad_edge = EdgeInfo(
        target_node_type="domain",
        target_name="",
        edge_type="belongs_to",
        is_structural=False,
    )
    payloads = (
        FacetPayload(
            node_type="meta",
            node_name=action_name,
            node_class=demo_action,
            node_meta=(),
            edges=(bad_edge,),
        ),
    )
    with pytest.raises(ValueError, match="missing domain target_name"):
        LogicalGraphBuilder.build(facet_payloads=payloads)


def test_facet_duplicate_belongs_to_deduped_to_single_pair() -> None:
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    edge1 = BaseIntentInspector._make_edge("domain", demo_domain, "belongs_to", False)
    edge2 = BaseIntentInspector._make_edge("domain", demo_domain, "belongs_to", False)
    payloads = (
        FacetPayload(
            node_type="domain",
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(display_name="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=(),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="d", domain=demo_domain),
            edges=(edge1, edge2),
        ),
        FacetPayload(
            node_type="role",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(),
        ),
    )
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=payloads)
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = raw["expected"]
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )
    assert len(vertices) == len(expected["vertices"])


def test_facet_projection_ignores_unknown_facet_kind() -> None:
    _, demo_action, _ = _g0_demo_types()
    action_name = BaseIntentInspector._make_node_name(demo_action)
    noise = FacetPayload(
        node_type="aspect",
        node_name=f"{action_name}.noise_aspect",
        node_class=demo_action,
        node_meta=(),
        edges=(),
    )
    base = list(_g0_facet_payloads())
    vertices, edges = LogicalGraphBuilder.build(facet_payloads=(*base, noise))
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = raw["expected"]
    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )

# tests/graph_contract/test_graph_builder.py

"""
Facet → interchange projection (:mod:`graph.graph_builder`).
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from action_machine.legacy.interchange_vertex_labels import DOMAIN_VERTEX_TYPE
from graph import GraphBuilder, GraphEdge, GraphVertex
from graph.base_intent_inspector import BaseIntentInspector
from graph.facet_edge import FacetEdge
from graph.facet_vertex import FacetVertex
from graph.graph_builder import build_interchange_from_facet_vertices
from graph.graph_coordinator import GraphCoordinator


def _interchange_canonical(payloads: tuple[FacetVertex, ...]) -> tuple[list[dict], list[dict]]:
    """Canonical dict rows for interchange vertices/edges (no JSON goldens)."""
    v, e = build_interchange_from_facet_vertices(payloads)
    return _canonical_vertices(v), _canonical_edges(e)


def _simulate_phase1_merge(
    gc: GraphCoordinator,
    payloads: tuple[FacetVertex, ...],
) -> list[FacetVertex]:
    """Same key fold/merge as :meth:`GraphCoordinator._phase1_collect` (without inspectors)."""
    by_key: dict[str, FacetVertex] = {}
    for p in payloads:
        ck = gc._facet_collect_key(p)
        inc = gc._normalize_payload_for_collect_key(p, ck)
        if ck not in by_key:
            by_key[ck] = inc
            continue
        merged = gc._merge_facets_under_collect_key(by_key[ck], inc)
        if merged is None:
            msg = f"unexpected duplicate merge failure for {ck!r}"
            raise AssertionError(msg)
        by_key[ck] = merged
    return list(by_key.values())


def _stub_class(module: str, short: str) -> type:
    t = type(short, (), {})
    t.__module__ = module
    t.__qualname__ = short
    return t


def _g0_demo_types() -> tuple[type, type, type]:
    """Stub types with stable ``__module__`` / ``__qualname__`` for G0 facet tests."""
    domain = _stub_class("golden_demo.domains", "DemoDomain")
    action = _stub_class("golden_demo.actions", "DemoAction")
    role = _stub_class("golden_demo.roles", "DemoRole")
    return domain, action, role


def _g0_facet_vertices() -> tuple[FacetVertex, ...]:
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    role_class_name = BaseIntentInspector._make_node_name(demo_role)
    domain_edge = BaseIntentInspector._make_edge(
        DOMAIN_VERTEX_TYPE,
        demo_domain,
        "belongs_to",
        False,
    )
    requires_role_edge = BaseIntentInspector._make_edge(
        "role_class",
        demo_role,
        "requires_role",
        False,
    )
    return (
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetVertex(
            node_type="role_class",
            node_name=role_class_name,
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetVertex(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(requires_role_edge,),
        ),
        FacetVertex(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
    )


def _g0_meta_no_action_payloads() -> tuple[FacetVertex, ...]:
    """Facet tuples for meta+role_class+action merge without a standalone structural action row."""
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    return (
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetVertex(
            node_type="role_class",
            node_name=BaseIntentInspector._make_node_name(demo_role),
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetVertex(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetVertex(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(
                BaseIntentInspector._make_edge(
                    "role_class",
                    demo_role,
                    "requires_role",
                    False,
                ),
            ),
        ),
    )


def _canonical_vertices(vertices: list[GraphVertex]) -> list[dict]:
    rows = [asdict(v) for v in vertices]
    return sorted(rows, key=lambda r: r["id"])


def _canonical_edges(edges: list[GraphEdge]) -> list[dict]:
    rows = [asdict(e) for e in edges]
    return sorted(
        rows,
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_graph_builder_facet_vertices_match_fixture() -> None:
    exp_v, exp_e = _interchange_canonical(_g0_facet_vertices())
    vertices, edges = build_interchange_from_facet_vertices(_g0_facet_vertices())
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_vertices_after_phase1_merge_match_fixture() -> None:
    gc = GraphCoordinator()
    merged = _simulate_phase1_merge(gc, _g0_facet_vertices())
    exp_v, exp_e = _interchange_canonical(tuple(merged))
    vertices, edges = build_interchange_from_facet_vertices(merged)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_graph_builder_requires_facet_vertices_keyword() -> None:
    with pytest.raises(TypeError):
        GraphBuilder.build_from_facet_vertices()


def test_graph_builder_rejects_unknown_keyword() -> None:
    with pytest.raises(TypeError):
        GraphBuilder.build_from_facet_vertices(facet_vertices=(), extra_kw=1)  # type: ignore[call-arg]


def test_facet_projection_rejects_duplicate_facet_key() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    name = BaseIntentInspector._make_node_name(demo_action)
    facet_vertices = (
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=name,
            node_class=demo_domain,
            node_meta=(),
            edges=(),
        ),
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=name,
            node_class=demo_domain,
            node_meta=(),
            edges=(),
        ),
    )
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_interchange_from_facet_vertices(facet_vertices)


def test_facet_empty_vertices_yield_empty_graph() -> None:
    vertices, edges = build_interchange_from_facet_vertices(())
    assert vertices == []
    assert edges == []


def test_facet_vertex_order_is_canonicalized() -> None:
    exp_v, exp_e = _interchange_canonical(_g0_facet_vertices())
    shuffled = (
        _g0_facet_vertices()[3],
        _g0_facet_vertices()[2],
        _g0_facet_vertices()[0],
        _g0_facet_vertices()[1],
    )
    vertices, edges = build_interchange_from_facet_vertices(shuffled)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_meta_without_separate_action_row_matches_canonical() -> None:
    """Coordinator may omit a standalone ``action`` facet when ``meta`` already names the action."""
    payloads = _g0_meta_no_action_payloads()
    exp_v, exp_e = _interchange_canonical(payloads)
    vertices, edges = build_interchange_from_facet_vertices(payloads)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_role_spec_non_type_skips_assigned_edges() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    payloads = (
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetVertex(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="x", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetVertex(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec="not-a-type"),
            edges=(),
        ),
    )
    vertices, edges = build_interchange_from_facet_vertices(payloads)
    assert len(vertices) == 3
    assert {v.node_type for v in vertices} == {DOMAIN_VERTEX_TYPE, "Action", "meta"}
    assert len(edges) == 1
    assert edges[0].edge_type == "BELONGS_TO"


def test_facet_belongs_to_empty_target_name_raises() -> None:
    _, demo_action, _ = _g0_demo_types()
    meta_name = BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta")
    bad_edge = FacetEdge(
        target_node_type=DOMAIN_VERTEX_TYPE,
        target_name="",
        edge_type="belongs_to",
        is_structural=False,
    )
    payloads = (
        FacetVertex(
            node_type="meta",
            node_name=meta_name,
            node_class=demo_action,
            node_meta=(),
            edges=(bad_edge,),
        ),
    )
    with pytest.raises(ValueError, match="unknown target_id"):
        build_interchange_from_facet_vertices(payloads)


def test_facet_duplicate_belongs_to_deduped_to_single_pair() -> None:
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    edge1 = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    edge2 = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    requires_role_edge = BaseIntentInspector._make_edge(
        "role_class",
        demo_role,
        "requires_role",
        False,
    )
    payloads = (
        FacetVertex(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetVertex(
            node_type="role_class",
            node_name=BaseIntentInspector._make_node_name(demo_role),
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetVertex(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(requires_role_edge,),
        ),
        FacetVertex(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="d", domain=demo_domain),
            edges=(edge1, edge2),
        ),
    )
    vertices, edges = build_interchange_from_facet_vertices(payloads)
    exp_v, exp_e = _interchange_canonical(payloads)
    assert _canonical_edges(edges) == exp_e
    assert len(vertices) == len(exp_v)


def test_facet_projection_includes_unknown_facet_kind_as_generic_vertex() -> None:
    _, demo_action, _ = _g0_demo_types()
    action_name = BaseIntentInspector._make_node_name(demo_action)
    noise = FacetVertex(
        node_type="RegularAspect",
        node_name=f"{action_name}:noise_aspect",
        node_class=demo_action,
        node_meta=(),
        edges=(),
    )
    base = list(_g0_facet_vertices())
    exp_v_base, exp_e_base = _interchange_canonical(tuple(base))
    vertices, edges = build_interchange_from_facet_vertices((*base, noise))
    got_v = _canonical_vertices(vertices)
    extra_id = f"{action_name}:noise_aspect"
    assert any(v["id"] == extra_id for v in got_v)
    got_without_extra = sorted([v for v in got_v if v["id"] != extra_id], key=lambda r: r["id"])
    assert got_without_extra == exp_v_base
    assert _canonical_edges(edges) == exp_e_base

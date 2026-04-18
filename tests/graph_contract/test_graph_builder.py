# tests/graph_contract/test_graph_builder.py

"""
``GraphBuilder`` — synthetic bundle and facet payloads (:mod:`action_machine.graph.graph_builder`).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from action_machine.graph import GraphBuilder, GraphEdge, GraphVertex
from action_machine.graph.base_intent_inspector import BaseIntentInspector
from action_machine.graph.edge_info import EdgeInfo
from action_machine.graph.facet_payload import FacetPayload
from action_machine.graph.graph_builder import build_interchange_from_facet_payloads
from action_machine.graph.graph_coordinator import GraphCoordinator
from action_machine.interchange_vertex_labels import DOMAIN_VERTEX_TYPE

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "golden_graph" / "synthetic_minimal.json"


def _interchange_canonical(payloads: tuple[FacetPayload, ...]) -> tuple[list[dict], list[dict]]:
    """Canonical dict rows for interchange vertices/edges (no JSON goldens)."""
    v, e = build_interchange_from_facet_payloads(payloads)
    return _canonical_vertices(v), _canonical_edges(e)


def _simulate_phase1_merge(
    gc: GraphCoordinator,
    payloads: tuple[FacetPayload, ...],
) -> list[FacetPayload]:
    """Same key fold/merge as :meth:`GraphCoordinator._phase1_collect` (without inspectors)."""
    by_key: dict[str, FacetPayload] = {}
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
    """Types whose ``__module__`` / ``__qualname__`` match ``synthetic_minimal.json`` ids."""
    domain = _stub_class("golden_demo.domains", "DemoDomain")
    action = _stub_class("golden_demo.actions", "DemoAction")
    role = _stub_class("golden_demo.roles", "DemoRole")
    return domain, action, role


def _g0_facet_payloads() -> tuple[FacetPayload, ...]:
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
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="role_class",
            node_name=role_class_name,
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetPayload(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(requires_role_edge,),
        ),
        FacetPayload(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
    )


def _g0_meta_no_action_payloads() -> tuple[FacetPayload, ...]:
    """Facet tuples for meta+role_class+action merge without a standalone structural action row."""
    demo_domain, demo_action, demo_role = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    return (
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="role_class",
            node_name=BaseIntentInspector._make_node_name(demo_role),
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="demo", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetPayload(
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


def test_graph_builder_synthetic_g0_matches_fixture() -> None:
    raw = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    inp = raw["input"]
    expected = raw["expected"]

    vertices, edges = GraphBuilder.build(synthetic_bundle=inp)

    assert _canonical_vertices(vertices) == sorted(expected["vertices"], key=lambda r: r["id"])
    assert _canonical_edges(edges) == sorted(
        expected["edges"],
        key=lambda r: (r["source_id"], r["target_id"], r["edge_type"], r["category"]),
    )


def test_graph_builder_facet_payloads_match_fixture() -> None:
    exp_v, exp_e = _interchange_canonical(_g0_facet_payloads())
    vertices, edges = build_interchange_from_facet_payloads(_g0_facet_payloads())
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_payloads_after_phase1_merge_match_fixture() -> None:
    gc = GraphCoordinator()
    merged = _simulate_phase1_merge(gc, _g0_facet_payloads())
    exp_v, exp_e = _interchange_canonical(tuple(merged))
    vertices, edges = build_interchange_from_facet_payloads(merged)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_graph_builder_requires_synthetic_g0_keyword() -> None:
    with pytest.raises(TypeError):
        GraphBuilder.build()


def test_graph_builder_rejects_unknown_keyword() -> None:
    with pytest.raises(TypeError):
        GraphBuilder.build(synthetic_bundle={}, facet_payloads=_g0_facet_payloads())


def test_facet_projection_rejects_duplicate_facet_key() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    name = BaseIntentInspector._make_node_name(demo_action)
    payloads = (
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=name,
            node_class=demo_domain,
            node_meta=(),
            edges=(),
        ),
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=name,
            node_class=demo_domain,
            node_meta=(),
            edges=(),
        ),
    )
    with pytest.raises(ValueError, match="duplicate vertex id"):
        build_interchange_from_facet_payloads(payloads)


def test_facet_empty_payloads_yield_empty_graph() -> None:
    vertices, edges = build_interchange_from_facet_payloads(())
    assert vertices == []
    assert edges == []


def test_facet_payload_order_is_canonicalized() -> None:
    exp_v, exp_e = _interchange_canonical(_g0_facet_payloads())
    shuffled = (
        _g0_facet_payloads()[3],
        _g0_facet_payloads()[2],
        _g0_facet_payloads()[0],
        _g0_facet_payloads()[1],
    )
    vertices, edges = build_interchange_from_facet_payloads(shuffled)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_meta_without_separate_action_row_matches_golden() -> None:
    """Coordinator may omit a standalone ``action`` facet when ``meta`` already names the action."""
    payloads = _g0_meta_no_action_payloads()
    exp_v, exp_e = _interchange_canonical(payloads)
    vertices, edges = build_interchange_from_facet_payloads(payloads)
    assert _canonical_vertices(vertices) == exp_v
    assert _canonical_edges(edges) == exp_e


def test_facet_role_spec_non_type_skips_assigned_edges() -> None:
    demo_domain, demo_action, _ = _g0_demo_types()
    domain_name = BaseIntentInspector._make_node_name(demo_domain)
    action_name = BaseIntentInspector._make_node_name(demo_action)
    domain_edge = BaseIntentInspector._make_edge(DOMAIN_VERTEX_TYPE, demo_domain, "belongs_to", False)
    payloads = (
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="x", domain=demo_domain),
            edges=(domain_edge,),
        ),
        FacetPayload(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec="not-a-type"),
            edges=(),
        ),
    )
    vertices, edges = build_interchange_from_facet_payloads(payloads)
    assert len(vertices) == 3
    assert {v.node_type for v in vertices} == {DOMAIN_VERTEX_TYPE, "Action", "meta"}
    assert len(edges) == 1
    assert edges[0].edge_type == "BELONGS_TO"


def test_facet_belongs_to_empty_target_name_raises() -> None:
    _, demo_action, _ = _g0_demo_types()
    meta_name = BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta")
    bad_edge = EdgeInfo(
        target_node_type=DOMAIN_VERTEX_TYPE,
        target_name="",
        edge_type="belongs_to",
        is_structural=False,
    )
    payloads = (
        FacetPayload(
            node_type="meta",
            node_name=meta_name,
            node_class=demo_action,
            node_meta=(),
            edges=(bad_edge,),
        ),
    )
    with pytest.raises(ValueError, match="unknown target_id"):
        build_interchange_from_facet_payloads(payloads)


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
        FacetPayload(
            node_type=DOMAIN_VERTEX_TYPE,
            node_name=domain_name,
            node_class=demo_domain,
            node_meta=BaseIntentInspector._make_meta(label="demo"),
            edges=(),
        ),
        FacetPayload(
            node_type="role_class",
            node_name=BaseIntentInspector._make_node_name(demo_role),
            node_class=demo_role,
            node_meta=BaseIntentInspector._make_meta(name="demo", description="golden stub role"),
            edges=(),
        ),
        FacetPayload(
            node_type="Action",
            node_name=action_name,
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(spec=demo_role),
            edges=(requires_role_edge,),
        ),
        FacetPayload(
            node_type="meta",
            node_name=BaseIntentInspector._make_host_dependent_node_name(demo_action, "meta"),
            node_class=demo_action,
            node_meta=BaseIntentInspector._make_meta(description="d", domain=demo_domain),
            edges=(edge1, edge2),
        ),
    )
    vertices, edges = build_interchange_from_facet_payloads(payloads)
    exp_v, exp_e = _interchange_canonical(payloads)
    assert _canonical_edges(edges) == exp_e
    assert len(vertices) == len(exp_v)


def test_facet_projection_includes_unknown_facet_kind_as_generic_vertex() -> None:
    _, demo_action, _ = _g0_demo_types()
    action_name = BaseIntentInspector._make_node_name(demo_action)
    noise = FacetPayload(
        node_type="RegularAspect",
        node_name=f"{action_name}:noise_aspect",
        node_class=demo_action,
        node_meta=(),
        edges=(),
    )
    base = list(_g0_facet_payloads())
    exp_v_base, exp_e_base = _interchange_canonical(tuple(base))
    vertices, edges = build_interchange_from_facet_payloads((*base, noise))
    got_v = _canonical_vertices(vertices)
    extra_id = f"{action_name}:noise_aspect"
    assert any(v["id"] == extra_id for v in got_v)
    got_without_extra = sorted([v for v in got_v if v["id"] != extra_id], key=lambda r: r["id"])
    assert got_without_extra == exp_v_base
    assert _canonical_edges(edges) == exp_e_base

# tests/maxitor/test_export_uses_graph.py

"""Maxitor export uses ``get_graph_for_visualization`` / ``get_graph`` for the interchange view."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import rustworkx as rx

from maxitor.graph_export import (
    JSON_SCHEMA_ID,
    coordinator_pygraph_for_visual_export,
    export_pygraph_to_dot,
    export_pygraph_to_graphml,
    export_pygraph_to_json,
    json_document_to_pygraph,
    normalize_coordinator_node_payload_for_visualization,
    pygraph_to_dot_source,
    pygraph_to_json_document,
)
from maxitor.samples.build import _MODULES, build_sample_coordinator
from maxitor.visualizer import G6_CDN_URL, export_samples_graph_html, generate_g6_html


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_coordinator_pygraph_matches_built_coordinator() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    g = coordinator_pygraph_for_visual_export(coord)
    assert len(g) == len(coord.get_graph())
    sample = g[0]
    assert "node_type" in sample


def test_coordinator_pygraph_prefers_get_graph_for_visualization() -> None:
    class _Stub:
        def get_graph_for_visualization(self) -> rx.PyDiGraph:
            g = rx.PyDiGraph()
            g.add_node({"node_type": "action", "id": "viz.only", "label": "V"})
            return g

        def get_graph(self) -> rx.PyDiGraph:
            g = rx.PyDiGraph()
            g.add_node({"node_type": "role_class", "id": "fallback.only", "label": "L"})
            return g

    out = coordinator_pygraph_for_visual_export(_Stub())
    assert len(out) == 1
    assert out[0]["id"] == "viz.only"


def test_coordinator_pygraph_falls_back_to_get_graph() -> None:
    class _Stub:
        def __init__(self) -> None:
            self._g = rx.PyDiGraph()
            self._g.add_node({"node_type": "x", "id": "n", "class_ref": None})

        def get_graph(self) -> rx.PyDiGraph:
            return self._g

    stub = _Stub()
    out = coordinator_pygraph_for_visual_export(stub)
    assert len(out) == 1
    assert out[0].get("node_type") == "x"


def test_coordinator_pygraph_requires_graph_api() -> None:
    class _Empty:
        pass

    with pytest.raises(TypeError, match="get_graph"):
        coordinator_pygraph_for_visual_export(_Empty())


def test_normalize_interchange_node_maps_to_facet_keys() -> None:
    raw = {
        "node_type": "action",
        "id": "pkg.actions.Foo",
        "label": "Foo",
        "stereotype": "Business Process",
        "class_ref": None,
        "properties": {},
    }
    norm = normalize_coordinator_node_payload_for_visualization(raw)
    assert norm["node_type"] == "action"
    assert norm["id"] == "pkg.actions.Foo"
    assert norm["label"] == "Foo"
    assert norm["stereotype"] == "Business Process"
    assert norm["properties"] == {}


def test_json_document_to_pygraph_roundtrip_counts() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    doc = pygraph_to_json_document(graph)
    back = json_document_to_pygraph(doc)
    assert len(back) == len(graph)
    assert back.num_edges() == graph.num_edges()


def test_pygraph_to_json_document_roundtrip_keys() -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    doc = pygraph_to_json_document(graph)
    assert doc["schema"] == JSON_SCHEMA_ID
    assert doc["node_count"] == len(graph)
    assert doc["edge_count"] == graph.num_edges()
    first = doc["nodes"][0]["data"]
    assert first.get("node_type")


@pytest.mark.integration
def test_json_export_writes_utf8(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    out = tmp_path / "out.json"
    export_pygraph_to_json(graph, out)
    import json as _json

    loaded = _json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema"] == JSON_SCHEMA_ID
    assert len(loaded["nodes"]) >= 1


def test_pygraph_to_dot_source_shape() -> None:
    g = rx.PyDiGraph()
    g.add_node({"node_type": "action", "id": "pkg.X", "label": "X"})
    src = pygraph_to_dot_source(g, graph_id="t")
    assert src.startswith("digraph")
    assert "n0" in src
    assert "pkg.X" in src or "X" in src


@pytest.mark.integration
def test_dot_export_writes_digraph(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    out = tmp_path / "out.dot"
    export_pygraph_to_dot(graph, out)
    body = out.read_text(encoding="utf-8")
    assert body.strip().startswith("digraph")
    assert " -> " in body


@pytest.mark.integration
def test_graphml_export_smoke_contains_graphml(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    out = tmp_path / "out.graphml"
    export_pygraph_to_graphml(graph, out)
    text = out.read_text(encoding="utf-8")
    assert "graphml" in text.lower()
    assert "<node " in text or "<node\t" in text


@pytest.mark.integration
def test_html_export_smoke_contains_g6_cdn_and_node_type(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    target = tmp_path / "g.html"
    generate_g6_html(graph, target, title="t")
    html = target.read_text(encoding="utf-8")
    assert G6_CDN_URL in html
    assert '"node_type"' in html
    assert "color-legend" in html
    assert "type: 'line'" in html or 'type: "line"' in html
    assert "type: 'image'" in html or 'type: "image"' in html
    assert "bubble-sets" in html
    assert "bubble-application-roles" in html


@pytest.mark.integration
def test_export_samples_graph_html_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _import_test_domain_modules()
    from maxitor import visualizer as viz

    monkeypatch.setattr(viz, "_default_archive_logs_dir", lambda: tmp_path)
    path = export_samples_graph_html()
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert G6_CDN_URL in body

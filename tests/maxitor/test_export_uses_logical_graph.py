# tests/maxitor/test_export_uses_logical_graph.py

"""Maxitor export picks the logical graph when the coordinator exposes ``get_logical_graph``."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
import rustworkx as rx

from maxitor.graph_export import (
    coordinator_pygraph_for_visual_export,
    export_pygraph_to_graphml,
    normalize_coordinator_node_payload_for_visualization,
)
from maxitor.test_domain.build import _MODULES, build_test_coordinator
from maxitor.visualizer import G6_CDN_URL, export_test_domain_graph_html, generate_g6_html


def _import_test_domain_modules() -> None:
    for name in _MODULES:
        importlib.import_module(name)


def test_coordinator_pygraph_prefers_logical_graph() -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    g = coordinator_pygraph_for_visual_export(coord)
    assert len(g) == len(coord.get_logical_graph())
    sample = g[0]
    assert "vertex_type" in sample


def test_coordinator_pygraph_falls_back_to_get_graph() -> None:
    class _Stub:
        def __init__(self) -> None:
            self._g = rx.PyDiGraph()
            self._g.add_node({"node_type": "x", "name": "n", "class_ref": None})

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


def test_normalize_logical_node_maps_to_facet_keys() -> None:
    raw = {
        "vertex_type": "action",
        "id": "pkg.actions.Foo",
        "display_name": "Foo",
        "stereotype": "Business Process",
        "class_ref": None,
        "properties": {},
    }
    norm = normalize_coordinator_node_payload_for_visualization(raw)
    assert norm["node_type"] == "action"
    assert norm["name"] == "pkg.actions.Foo"
    assert norm["label"] == "Foo"


@pytest.mark.integration
def test_graphml_export_smoke_contains_graphml(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    out = tmp_path / "out.graphml"
    export_pygraph_to_graphml(graph, out)
    text = out.read_text(encoding="utf-8")
    assert "graphml" in text.lower()
    assert "<node " in text or "<node\t" in text


@pytest.mark.integration
def test_html_export_smoke_contains_g6_cdn_and_node_type(tmp_path: Path) -> None:
    _import_test_domain_modules()
    coord = build_test_coordinator()
    graph = coordinator_pygraph_for_visual_export(coord)
    target = tmp_path / "g.html"
    generate_g6_html(graph, target, title="t")
    html = target.read_text(encoding="utf-8")
    assert G6_CDN_URL in html
    assert '"node_type"' in html


@pytest.mark.integration
def test_export_test_domain_graph_html_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _import_test_domain_modules()
    from maxitor import visualizer as viz

    monkeypatch.setattr(viz, "_default_archive_logs_dir", lambda: tmp_path)
    path = export_test_domain_graph_html()
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert G6_CDN_URL in body

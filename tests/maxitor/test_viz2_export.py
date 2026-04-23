from __future__ import annotations

from pathlib import Path

import pytest

from maxitor.samples.node_build import (
    build_sample_node_graph_coordinator,
    export_samples_graph_html,
)
from maxitor.viz2 import interchange_graph_visualizer as viz2
from maxitor.viz2.interchange_graph_visualizer import G6_CDN_URL


def test_build_sample_node_graph_coordinator_has_nodes() -> None:
    coord = build_sample_node_graph_coordinator()
    assert coord.get_all_nodes()


@pytest.mark.integration
def test_export_samples_graph_html_writes_viz2_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "graph_node_2.html"
    monkeypatch.setattr(viz2, "INTERCHANGE_AXES_GRAPH_HTML_PATH", target)

    path = export_samples_graph_html()

    assert path == target
    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert G6_CDN_URL in html
    assert "color-legend" in html
    assert "bubble-sets" in html

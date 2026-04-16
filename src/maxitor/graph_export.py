# src/maxitor/graph_export.py
"""
GraphML export for coordinator ``PyDiGraph`` — purpose.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Write rustworkx graphs under ``maxitor`` diagnostics to **GraphML** via
``rustworkx.write_graphml``. The coordinator may expose either a **facet** graph
(``node_type``, ``name``, ``class_ref`` on nodes) or a **logical interchange** graph
(``vertex_type``, ``id``, ``display_name``). This module normalizes logical payloads
into the facet-shaped view expected by string-only GraphML serialization, and picks
``get_logical_graph()`` when present so HTML and GraphML stay aligned on the same
export surface.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    build_test_coordinator()
            │
            ▼
    coordinator_pygraph_for_visual_export(coordinator)
            │   (get_graph_for_visualization, else get_logical_graph, else get_graph)
            ▼
    PyDiGraph  ──►  normalize node dicts  ──►  pygraph_to_graphml_string_dicts
            │                                          │
            │                                          ▼
            │                                 export_pygraph_to_graphml(path)
            │
            └──►  (visualizer.generate_g6_html reuses normalization import)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Topology is preserved: node index order maps through ``rw_index`` onto the copy
  written to GraphML.
- Non-string node/edge payload values are never passed to ``write_graphml``; a
  sanitized copy is built first.
- ``normalize_coordinator_node_payload_for_visualization`` does not mutate the
  input graph payloads in place.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- **Happy path:** ``export_test_domain_graph_graphml()`` writes
  ``archive/logs/test_domain_graph.graphml`` using the logical graph when the
  coordinator implements ``get_logical_graph()``.
- **Edge case:** a stub coordinator that only implements ``get_graph()`` still
  exports; normalization maps logical interchange payloads to facet-shaped keys.
  Implementations may override ``get_graph_for_visualization`` to steer exports
  without relying on the default ``get_graph()`` interchange shape.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``coordinator_pygraph_for_visual_export`` raises ``TypeError`` when neither
  ``get_logical_graph`` nor ``get_graph`` is callable.
- Very large ``meta`` / attribute blobs on edges are truncated when JSON-encoded
  for GraphML edge attributes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import rustworkx as rx

DEFAULT_TEST_DOMAIN_GRAPH_GRAPHML = "test_domain_graph.graphml"


def _archive_logs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "archive" / "logs"


def normalize_coordinator_node_payload_for_visualization(
    node: dict[str, Any],
) -> dict[str, Any]:
    """
    Map logical interchange node payloads to the facet-shaped keys used by exporters.
    """
    if "vertex_type" not in node or "id" not in node:
        return dict(node)
    vid = str(node["id"])
    vt = str(node.get("vertex_type", "unknown"))
    display = str(node.get("display_name", "") or "").strip()
    label = display or (vid.rsplit(".", maxsplit=1)[-1] if "." in vid else vid)
    return {
        "node_type": vt,
        "name": vid,
        "label": label,
        "class_ref": node.get("class_ref"),
    }


def coordinator_pygraph_for_visual_export(coordinator: object) -> rx.PyDiGraph:
    """Return the graph used for maxitor HTML/GraphML export (logical graph when available)."""
    visual = getattr(coordinator, "get_graph_for_visualization", None)
    if callable(visual):
        return cast(rx.PyDiGraph, visual())
    logical = getattr(coordinator, "get_logical_graph", None)
    if callable(logical):
        return cast(rx.PyDiGraph, logical())
    graph = getattr(coordinator, "get_graph", None)
    if callable(graph):
        return cast(rx.PyDiGraph, graph())
    msg = (
        "Coordinator must expose get_graph_for_visualization(), "
        "get_logical_graph(), and/or get_graph()"
    )
    raise TypeError(msg)


def pygraph_to_graphml_string_dicts(graph: rx.PyDiGraph) -> rx.PyDiGraph:
    """
    Build a directed graph copy with string-only node/edge dicts safe for GraphML.
    """
    out = rx.PyDiGraph()
    old_to_new: dict[int, int] = {}
    for idx in graph.node_indices():
        raw = graph[idx]
        node = dict(raw) if isinstance(raw, dict) else {}
        node = normalize_coordinator_node_payload_for_visualization(node)
        name = str(node.get("name", "") or "")
        node_type = str(node.get("node_type", "") or "")
        cr = node.get("class_ref")
        class_name = (
            f"{cr.__module__}.{cr.__qualname__}" if isinstance(cr, type) else ""
        )
        graph_key = f"{node_type}:{name}" if node_type or name else str(int(idx))
        payload = {
            "name": name,
            "type": node_type,
            "class_name": class_name,
            "graph_key": graph_key,
            "rw_index": str(int(idx)),
        }
        old_to_new[idx] = out.add_node(payload)
    for s, t, w in graph.weighted_edge_list():
        ed = dict(w) if isinstance(w, dict) else {}
        edge_type = str(ed.get("edge_type", "") or "")
        ep: dict[str, str] = {"type": edge_type}
        meta = ed.get("meta")
        if meta is not None:
            try:
                ep["meta"] = json.dumps(meta, ensure_ascii=False, default=str)[:8000]
            except TypeError:
                ep["meta"] = str(meta)[:8000]
        out.add_edge(old_to_new[s], old_to_new[t], ep)
    return out


def export_pygraph_to_graphml(graph: rx.PyDiGraph, output_path: str | Path) -> Path:
    """Write GraphML for the given graph topology to ``output_path``."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = pygraph_to_graphml_string_dicts(graph)
    rx.write_graphml(safe, str(path))
    return path


def export_test_domain_graph_graphml(
    output_path: str | Path | None = None,
    *,
    use_timestamp: bool = False,
) -> Path:
    """Build the test_domain coordinator and write GraphML under ``archive/logs``."""
    from maxitor.test_domain.build import build_test_coordinator  # pylint: disable=import-outside-toplevel

    coordinator = build_test_coordinator()
    graph = coordinator_pygraph_for_visual_export(coordinator)

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = (
            f"test_domain_graph_{ts}.graphml"
            if use_timestamp
            else DEFAULT_TEST_DOMAIN_GRAPH_GRAPHML
        )
        target = log_dir / name

    written = export_pygraph_to_graphml(graph, target)
    print(f"Graph GraphML written to {written}")
    return written


if __name__ == "__main__":
    export_test_domain_graph_graphml()

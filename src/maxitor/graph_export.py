# src/maxitor/graph_export.py
"""
GraphML export for coordinator ``PyDiGraph`` — purpose.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Write rustworkx graphs under ``maxitor`` diagnostics to **GraphML**, **JSON**, and
a minimal **DOT** (Graphviz) encoding. The coordinator may expose either a **facet**
graph (``node_type``, ``id``, ``class_ref`` on facet nodes) or an **interchange**
graph (``node_type``, ``id``, ``label``, ``properties``; no ``class_ref``). This module normalizes interchange
payloads into the facet-shaped view expected by string-only GraphML serialization,
and picks ``get_graph_for_visualization()`` / ``get_graph()`` so HTML, GraphML, JSON, and DOT stay
aligned on the same export surface.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    build_sample_coordinator()
            │
            ▼
    coordinator_pygraph_for_visual_export(coordinator)
            │   (get_graph_for_visualization, else get_graph)
            ▼
    PyDiGraph  ──►  normalize node dicts  ──►  pygraph_to_graphml_string_dicts
            │                                          │
            │                                          ▼
            │                                 export_pygraph_to_graphml(path)
            │
            ├──►  pygraph_to_json_document  ──►  export_pygraph_to_json(path)
            │
            ├──►  pygraph_to_dot_source       ──►  export_pygraph_to_dot(path)
            │
            └──►  (visualizer.generate_g6_html reuses normalization import)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

- **Happy path:** ``export_samples_graph_graphml()`` writes
  ``archive/logs/samples_graph.graphml`` using the interchange graph when the
  coordinator implements ``get_graph()``.
- **Edge case:** a stub coordinator that only implements ``get_graph()`` still
  exports; normalization maps interchange payloads to facet-shaped keys.
  Implementations may override ``get_graph_for_visualization`` to steer exports
  without relying on the default ``get_graph()`` interchange shape.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import rustworkx as rx

DEFAULT_SAMPLES_GRAPH_GRAPHML = "samples_graph.graphml"
DEFAULT_SAMPLES_GRAPH_JSON = "samples_graph.json"
DEFAULT_SAMPLES_GRAPH_DOT = "samples_graph.dot"
JSON_SCHEMA_ID = "actionmachine.rustworkx.coordinator_interchange.v1"


def _archive_logs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "archive" / "logs"


def normalize_coordinator_node_payload_for_visualization(
    node: dict[str, Any],
) -> dict[str, Any]:
    """
    Map interchange node payloads to the keys used by exporters and the HTML panel.

    **Preserves** the full interchange payload (``properties``, etc.) and
    fills ``label`` when missing. Interchange nodes do not carry runtime ``type``
    objects; identity is the string ``id`` (often a qualified Python path).
    Vertex identity stays on the interchange ``id`` (no duplicate ``name``).
    """
    merged = dict(node)
    merged.pop("class_ref", None)
    # Legacy payloads may still carry ``vertex_type``; canonical key is ``node_type``.
    if "vertex_type" in merged and "node_type" not in merged:
        merged["node_type"] = str(merged.pop("vertex_type"))
    if "id" not in merged:
        return merged
    text = str(merged.get("label", "") or "").strip()
    if not text:
        text = str(merged.get("display_name", "") or "").strip()
    vid = str(merged["id"])
    derived = text or (vid.rsplit(".", maxsplit=1)[-1] if "." in vid else vid)
    merged.setdefault("label", derived)
    return merged


def coordinator_pygraph_for_visual_export(coordinator: object) -> rx.PyDiGraph:
    """Return the graph used for maxitor HTML/GraphML export (interchange view when available)."""
    visual = getattr(coordinator, "get_graph_for_visualization", None)
    if callable(visual):
        return cast(rx.PyDiGraph, visual())
    graph = getattr(coordinator, "get_graph", None)
    if callable(graph):
        return cast(rx.PyDiGraph, graph())
    msg = "Coordinator must expose get_graph_for_visualization() and/or get_graph()"
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
        nid = str(node.get("id") or node.get("name") or "")
        node_type = str(node.get("node_type", "") or "")
        # Interchange ``id`` is the stable qualified string; no ``type`` object on nodes.
        class_name = nid
        graph_key = f"{node_type}:{nid}" if node_type or nid else str(int(idx))
        payload = {
            "id": nid,
            "node_type": node_type,
            "class_name": class_name,
            "graph_key": graph_key,
            "rw_index": str(int(idx)),
        }
        old_to_new[idx] = out.add_node(payload)
    for s, t, w in graph.weighted_edge_list():
        ed = dict(w) if isinstance(w, dict) else {}
        edge_type = str(ed.get("edge_type", "") or "")
        ep: dict[str, str] = {"type": edge_type}
        edge_row = ed.get("edge_row")
        if edge_row is not None:
            try:
                ep["edge_row"] = json.dumps(edge_row, ensure_ascii=False, default=str)[:8000]
            except TypeError:
                ep["edge_row"] = str(edge_row)[:8000]
        out.add_edge(old_to_new[s], old_to_new[t], ep)
    return out


def export_pygraph_to_graphml(graph: rx.PyDiGraph, output_path: str | Path) -> Path:
    """Write GraphML for the given graph topology to ``output_path``."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = pygraph_to_graphml_string_dicts(graph)
    rx.write_graphml(safe, str(path))
    return path


def _json_safe_value(value: Any) -> Any:
    """Recursively coerce node/edge payloads to JSON-serializable data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    if isinstance(value, frozenset):
        return sorted((_json_safe_value(v) for v in value), key=str)
    if isinstance(value, (tuple, list)):
        return [_json_safe_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    return str(value)


def pygraph_to_json_document(graph: rx.PyDiGraph) -> dict[str, Any]:
    """
    Build a portable JSON document: node/edge indices plus sanitized payloads.

    Intended for diagnostics and agents; not a stable RPC schema.
    """
    nodes: list[dict[str, Any]] = []
    for idx in graph.node_indices():
        raw = graph[idx]
        payload = dict(raw) if isinstance(raw, dict) else {"_repr": str(raw)}
        nodes.append({"rustworkx_index": int(idx), "data": _json_safe_value(payload)})
    edges: list[dict[str, Any]] = []
    for s, t, w in graph.weighted_edge_list():
        ed = dict(w) if isinstance(w, dict) else {"_repr": str(w)}
        edges.append(
            {
                "source_index": int(s),
                "target_index": int(t),
                "data": _json_safe_value(ed),
            }
        )
    return {
        "schema": JSON_SCHEMA_ID,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def json_document_to_pygraph(doc: Mapping[str, Any]) -> rx.PyDiGraph:
    """
    Rebuild a ``PyDiGraph`` from :func:`pygraph_to_json_document` output.

    Node ``rustworkx_index`` values must be ``0 .. node_count-1`` contiguous.
    """
    if not isinstance(doc, Mapping):
        msg = "document must be a mapping"
        raise TypeError(msg)
    schema = doc.get("schema")
    if schema is not None and schema != JSON_SCHEMA_ID:
        msg = f"unsupported JSON document schema: {schema!r}"
        raise ValueError(msg)
    nodes_raw = doc.get("nodes")
    edges_raw = doc.get("edges")
    if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
        msg = "document must contain list nodes and list edges"
        raise TypeError(msg)
    sorted_nodes = sorted(nodes_raw, key=lambda n: int(n["rustworkx_index"]))
    for i, entry in enumerate(sorted_nodes):
        if not isinstance(entry, Mapping):
            msg = "each node entry must be a mapping"
            raise TypeError(msg)
        ri = int(entry["rustworkx_index"])
        if ri != i:
            msg = f"node rustworkx_index must be contiguous from 0, expected {i}, got {ri}"
            raise ValueError(msg)
    g = rx.PyDiGraph()
    for entry in sorted_nodes:
        data = entry.get("data")
        if not isinstance(data, dict):
            msg = "each node entry must have object data"
            raise TypeError(msg)
        g.add_node(dict(data))
    for ee in edges_raw:
        if not isinstance(ee, Mapping):
            msg = "each edge entry must be a mapping"
            raise TypeError(msg)
        s = int(ee["source_index"])
        t = int(ee["target_index"])
        w = ee.get("data")
        if w is None:
            w = {}
        elif not isinstance(w, dict):
            w = {"_repr": str(w)}
        g.add_edge(s, t, dict(w))
    return g


def export_pygraph_to_json(graph: rx.PyDiGraph, output_path: str | Path) -> Path:
    """Write ``pygraph_to_json_document`` to ``output_path`` (UTF-8, indent=2)."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pygraph_to_json_document(graph)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _dot_escape_label(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", " ")
    )


def pygraph_to_dot_source(graph: rx.PyDiGraph, *, graph_id: str = "coordinator_graph") -> str:
    """
    Minimal DOT for Graphviz: one node per rustworkx index, labels from normalized names.

    Edge labels carry ``edge_type`` when present. Not optimized for huge graphs.
    """
    safe_id = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in graph_id) or "G"
    lines = [
        f'digraph "{_dot_escape_label(safe_id)}" {{',
        "  rankdir=LR;",
        "  node [shape=box style=rounded];",
    ]
    for idx in graph.node_indices():
        raw = graph[idx]
        node = dict(raw) if isinstance(raw, dict) else {}
        norm = normalize_coordinator_node_payload_for_visualization(node)
        label = str(
            norm.get("label") or norm.get("id") or norm.get("name") or f"node_{idx}"
        )
        lines.append(f'  n{int(idx)} [label="{_dot_escape_label(label)}"];')
    for s, t, w in graph.weighted_edge_list():
        ed = dict(w) if isinstance(w, dict) else {}
        et = str(ed.get("edge_type", "") or "")
        lines.append(f'  n{int(s)} -> n{int(t)} [label="{_dot_escape_label(et)}"];')
    lines.append("}")
    return "\n".join(lines)


def export_pygraph_to_dot(graph: rx.PyDiGraph, output_path: str | Path) -> Path:
    """Write UTF-8 DOT source produced by :func:`pygraph_to_dot_source`."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pygraph_to_dot_source(graph), encoding="utf-8")
    return path


def export_samples_graph_graphml(
    output_path: str | Path | None = None,
    *,
    use_timestamp: bool = False,
) -> Path:
    """Build the samples coordinator and write GraphML under ``archive/logs``."""
    from maxitor.samples.build import build_sample_coordinator  # pylint: disable=import-outside-toplevel

    coordinator = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coordinator)

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = (
            f"samples_graph_{ts}.graphml"
            if use_timestamp
            else DEFAULT_SAMPLES_GRAPH_GRAPHML
        )
        target = log_dir / name

    written = export_pygraph_to_graphml(graph, target)
    print(f"Graph GraphML written to {written}")
    return written


def export_samples_graph_json(
    output_path: str | Path | None = None,
    *,
    use_timestamp: bool = False,
) -> Path:
    """Build the samples coordinator and write JSON under ``archive/logs``."""
    from maxitor.samples.build import build_sample_coordinator  # pylint: disable=import-outside-toplevel

    coordinator = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coordinator)

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = (
            f"samples_graph_{ts}.json"
            if use_timestamp
            else DEFAULT_SAMPLES_GRAPH_JSON
        )
        target = log_dir / name

    written = export_pygraph_to_json(graph, target)
    print(f"Graph JSON written to {written}")
    return written


def export_samples_graph_dot(
    output_path: str | Path | None = None,
    *,
    use_timestamp: bool = False,
) -> Path:
    """Build the samples coordinator and write DOT under ``archive/logs``."""
    from maxitor.samples.build import build_sample_coordinator  # pylint: disable=import-outside-toplevel

    coordinator = build_sample_coordinator()
    graph = coordinator_pygraph_for_visual_export(coordinator)

    if output_path is not None:
        target = Path(output_path)
    else:
        log_dir = _archive_logs_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        name = (
            f"samples_graph_{ts}.dot"
            if use_timestamp
            else DEFAULT_SAMPLES_GRAPH_DOT
        )
        target = log_dir / name

    written = export_pygraph_to_dot(graph, target)
    print(f"Graph DOT written to {written}")
    return written


if __name__ == "__main__":
    export_samples_graph_graphml()

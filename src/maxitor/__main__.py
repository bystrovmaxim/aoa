# src/maxitor/__main__.py
"""``python -m maxitor`` — собрать samples координатор и вывести размер графа."""

from __future__ import annotations

from maxitor.samples.build import build_sample_coordinator

if __name__ == "__main__":
    c = build_sample_coordinator()
    print(f"Nodes: {c.graph_node_count}")
    print(f"Edges: {c.graph_edge_count}")

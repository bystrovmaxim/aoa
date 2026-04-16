# src/maxitor/__main__.py
"""``python -m maxitor`` — собрать test_domain координатор и вывести размер графа."""

from __future__ import annotations

from maxitor.test_domain.build import build_test_coordinator

if __name__ == "__main__":
    c = build_test_coordinator()
    print(f"Nodes: {c.graph_node_count}")
    print(f"Edges: {c.graph_edge_count}")

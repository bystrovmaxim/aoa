# packages/aoa-maxitor/src/aoa/maxitor/__main__.py
"""``python -m aoa.maxitor`` builds the sample ``NodeGraphCoordinator`` and prints graph size."""

from __future__ import annotations

from aoa.maxitor.samples.node_build import build_sample_node_graph_coordinator

if __name__ == "__main__":
    c = build_sample_node_graph_coordinator()
    print(f"Nodes: {len(c.get_all_nodes())}")
    print(f"Edges: {sum(len(node.get_all_edges()) for node in c.get_all_nodes())}")

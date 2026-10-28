# packages/aoa-maxitor/src/aoa/maxitor/print_graph.py
"""
Print Maxitor's own graph — the build command of Maxitor's entry in ``gnomon.toml``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor is itself an AOA service. ``gnomon write`` runs
``python -m aoa.maxitor.print_graph`` and saves what it prints in
``packages/aoa-maxitor/graph.json``, so every change to Maxitor carries its graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Importing the application module registers Maxitor's actions; the graph is then
the one ``create_app`` builds its machine with, written to standard output and
nothing else. Run in a process of its own, apart from the demo's graph.
"""

from __future__ import annotations

import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    """Write Maxitor's graph document to standard output."""
    importlib.import_module("aoa.maxitor.api.app")
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()

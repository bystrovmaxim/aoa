# packages/maxitor/app/src/maxitor/viewer/build_graph.py
"""
Build the viewer's own graph and write it to standard output — the build command of the ``viewer`` entry in ``gnomon.toml``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor is itself an AOA service. ``gnomon write`` runs
``python -m maxitor.viewer.build_graph`` and saves what it prints in
``packages/maxitor/app/graph.json``, so every change to the viewer carries its graph.
The graph comes from ``maxitor.viewer`` alone: another service of the package, when there
is one, keeps a file of its own beside it.

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
    importlib.import_module("maxitor.viewer.api.app")
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()

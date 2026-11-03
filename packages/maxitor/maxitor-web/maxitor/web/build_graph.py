# packages/maxitor/maxitor-web/maxitor/web/build_graph.py
"""
Build the front's own graph and write it to standard output — the build command of the ``maxitor`` entry in ``graph-builder.toml``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maxitor is itself an AOA service. ``graph-builder write`` runs
``python -m maxitor.web.build_graph`` and saves what it prints in
``packages/maxitor/maxitor-web/graph.json``, so every change to the front carries its graph.
The graph comes from ``maxitor.web`` alone: another service of the package, when there
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
    importlib.import_module("maxitor.web.api.app")
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()

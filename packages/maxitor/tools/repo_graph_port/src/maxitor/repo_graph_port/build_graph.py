# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/build_graph.py
"""
Build the port's own graph and write it to standard output — the build command of the ``repo-graph-port`` entry in ``graph-builder.toml``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The port is a service, so it keeps its graph beside its code, in
``packages/maxitor/tools/repo_graph_port/graph.json``, built from its own code only:
every change to the port carries its graph.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

import the server module (its actions, resources and roles register themselves) ──► the coordinator's JSON ──► stdout.
"""

from __future__ import annotations

import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    """Write the port's graph document to standard output."""
    importlib.import_module("maxitor.repo_graph_port.server")
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()

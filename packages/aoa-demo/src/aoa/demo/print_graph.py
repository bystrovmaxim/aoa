# packages/aoa-demo/src/aoa/demo/print_graph.py
"""
Print the demo's graph — the build command of the demo's entry in ``gnomon.toml``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``gnomon write`` runs ``python -m aoa.demo.print_graph`` and saves what it prints
in ``packages/aoa-demo/graph.json``, so every change to the demo's model carries
the graph it produces.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Registers the demo's sample modules, builds the coordinator the demo serves at
``/graph-json``, and writes its JSON to standard output — nothing else, since
standard output is the graph. Run in a process of its own: importing Maxitor in
the same process would add Maxitor's own actions to the graph.
"""

from __future__ import annotations

import sys

from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator


def main() -> None:
    """Write the demo's graph document to standard output."""
    sys.stdout.write(build_registered_interchange_coordinator().to_json())


if __name__ == "__main__":
    main()

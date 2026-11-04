# specs/059-maxitor-concept/model/build_graph.py
"""
Builds the graph of the Maxitor concept's data model and writes it to standard output.

The graph is built the same way as the graphs of the demo and Maxitor: importing the
model registers its entities, and the standard coordinator prints the graph. The output
is saved to ``graph.json`` next to this file. When the file runs as a script, Python puts
this folder first on the import path, so the model is imported by its module name.
The model is still a design, so it lives inside the specification, and the repository's
``graph-builder.toml`` has no entry for it.
"""

from __future__ import annotations

import importlib
import sys

from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator


def main() -> None:
    """Write the model's graph document to standard output."""
    importlib.import_module("enterprise_model")
    sys.stdout.write(create_node_graph_coordinator().to_json())


if __name__ == "__main__":
    main()

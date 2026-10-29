"""
12_graph_file.py — a service keeps its current graph in one file, and every merge carries it

The demo and Maxitor each print their graph, and ``graph-builder write`` saves it in a file beside the
package — ``packages/aoa-demo/graph.json``, ``packages/maxitor/app/graph.json`` — listed in
``graph-builder.toml`` at the repository root. The file changes in the same pull request as the code that
changed the graph, so git holds the graph's whole history; CI runs ``graph-builder check`` and fails when a
file is stale. The format is the Open Gnomon Protocol; ``graph-builder``, of the ``maxitor`` package,
knows nothing about AOA: it runs each build, checks what it prints, and keeps the file.

The cases, with the real output at the bottom:

  1. the repository's config: which graphs, built how, saved where;
  2. a saved graph passes the schema of the version it declares;
  3. built again, the graph is the file byte for byte;
  4. a stale copy: ``check`` names what changed, by id — what the file holds → what the build
     prints — and writes nothing;
  5. a copy written with another indent: only the formatting differs;
  6. a document of an unknown version is refused by name.

Everything this example writes goes into a temporary folder.

Output:

    1. The repository's graphs
       demo     uv run --extra dev python -m aoa.demo.build_graph  →  packages/aoa-demo/graph.json
       maxitor  uv run --extra dev python -m maxitor.viewer.build_graph  →  packages/maxitor/app/graph.json
    2. A saved graph against its schema
       packages/aoa-demo/graph.json: 1.1, 3213 nodes, 4841 edges — a graph
    3. Built again
       the same bytes as the file: True
    4. A stale copy
       stale
         edges[id=aoa.demo.model.telemetry_pipeline.telemetry_pipeline_domain.TelemetryPipelineDomain|application|aoa.action_machine.application.application.Application]: added
         nodes[id=aoa.demo.model.store.store_domain.StoreDomain].label: Shop → StoreDomain
    5. Another indent
       stale: only the formatting differs
    6. An unknown version
       GraphRefused: graph 9.9: unknown schema version '9.9'; known: 1.0, 1.1

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (graph files)

Run:
    uv run --extra dev python examples/step_26_maxitor/12_graph_file.py
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from maxitor.graph_builder.config import read_config
from maxitor.graph_builder.schemas import GraphRefused, check_graph
from maxitor.graph_builder.writer import build, check, render

# The repository root: the folder that holds graph-builder.toml, wherever this runs from.
REPO_ROOT = next(path for path in (Path.cwd(), *Path(__file__).resolve().parents) if (path / "graph-builder.toml").is_file())
os.chdir(REPO_ROOT)

print("1. The repository's graphs")
GRAPHS = read_config("graph-builder.toml")
for graph in GRAPHS:
    print(f"   {graph.name:<8} {graph.build}  →  {graph.file.relative_to(REPO_ROOT)}")
DEMO = next(graph for graph in GRAPHS if graph.name == "demo")

print("2. A saved graph against its schema")
saved = json.loads(DEMO.file.read_text(encoding="utf-8"))
check_graph(saved)
print(f"   {DEMO.file.relative_to(REPO_ROOT)}: {saved['schema_version']},"
      f" {len(saved['nodes'])} nodes, {len(saved['edges'])} edges — a graph")

print("3. Built again")
print("   the same bytes as the file:", render(build(DEMO)) == DEMO.file.read_bytes())

with tempfile.TemporaryDirectory() as folder:
    copy = replace(DEMO, file=Path(folder) / "graph.json")

    print("4. A stale copy")
    stale = json.loads(json.dumps(saved))
    node = next(node for node in stale["nodes"] if node["id"].endswith(".StoreDomain"))
    node["label"] = "Shop"
    stale["edges"].pop()
    copy.file.write_bytes(render(stale))
    (outcome,) = check([copy])
    print("  ", outcome.state)
    for line in outcome.details:
        print("    ", line)

    print("5. Another indent")
    copy.file.write_text(json.dumps(saved, indent=4), encoding="utf-8")
    (outcome,) = check([copy])
    print(f"   {outcome.state}: {outcome.details[0]}")

print("6. An unknown version")
try:
    check_graph({**saved, "schema_version": "9.9"})
except GraphRefused as refused:
    print(f"   GraphRefused: {refused}")

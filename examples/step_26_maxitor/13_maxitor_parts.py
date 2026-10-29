"""
13_maxitor_parts.py — Maxitor is one package; an install chooses its parts, and the protocol needs no Python

``maxitor`` holds the app (``maxitor.viewer``), the ``graph-builder`` command and the skills. ``pip install
maxitor`` with no extra installs the command alone — nothing of AOA, no server — which is all a CI job
needs; ``maxitor[viewer]`` adds the app. The graph's format, the Open Gnomon Protocol, is a folder of JSON
Schemas with no code: any validator in any language checks a graph against it.

The cases, with the real output at the bottom:

  1. a clean environment with ``maxitor`` and no extra: the command runs, nothing of AOA is installed;
  2. the app's command in that environment names the extra it needs, and exits with 2;
  3. any language: a plain JSON Schema validator — not Maxitor — accepts the demo's graph against the
     protocol's schema, and refuses it without one edge's ``id``;
  4. the app's import is ``maxitor.viewer``.

Case 1 builds the ``maxitor`` wheel and a clean environment in a temporary folder (``uv`` required).

Output:

    1. pip install maxitor, no extra
       graph-builder 3.0.0
       ok 1.1: 214 nodes, 305 edges
       installed: attrs, jsonschema, jsonschema-specifications, jsonschema_rs, maxitor, referencing, rpds-py, typing_extensions
       anything of AOA or of the server: none
    2. The app without its extra
       exit 2: maxitor-api needs the viewer: pip install "maxitor[viewer]"
    3. Any language: a plain JSON Schema validator
       the demo's graph against packages/open-gnomon-protocol/graph/1.1.json: valid
       the same without edges[0].id: refused — 'id' is a required property
    4. The app's import
       maxitor.viewer.api.app.create_app

Tutorial: ../../docs/tutorials/step-26-maxitor.md  ·  topic: Maxitor (parts and install)

Run:
    uv run --extra dev python examples/step_26_maxitor/13_maxitor_parts.py
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator
from maxitor.viewer.api.app import create_app

# The repository root: the folder that holds graph-builder.toml, wherever this runs from.
REPO_ROOT = next(path for path in (Path.cwd(), *Path(__file__).resolve().parents) if (path / "graph-builder.toml").is_file())
os.chdir(REPO_ROOT)

print("1. pip install maxitor, no extra")
with tempfile.TemporaryDirectory() as folder:
    tmp = Path(folder)
    subprocess.run(["uv", "build", "--package", "maxitor", "--wheel", "--out-dir", str(tmp / "dist"), "-q"], check=True)
    subprocess.run(["uv", "venv", "-q", str(tmp / "venv")], check=True)
    python = tmp / "venv" / "bin" / "python"
    subprocess.run(["uv", "pip", "install", "-q", f"--python={python}", *map(str, (tmp / "dist").glob("maxitor-*.whl"))], check=True)
    graph_builder = str(tmp / "venv" / "bin" / "graph-builder")
    print("  ", subprocess.run([graph_builder, "--version"], capture_output=True, text=True, check=True).stdout.strip())
    print("  ", subprocess.run([graph_builder, "validate", "packages/maxitor/app/graph.json"], capture_output=True, text=True, check=True).stdout.strip())
    listing = "import importlib.metadata as m; print(' '.join(sorted(d.metadata['Name'].lower() for d in m.distributions())))"
    installed = subprocess.run([str(python), "-c", listing], capture_output=True, text=True, check=True).stdout.split()
    print("   installed:", ", ".join(installed))
    heavy = [name for name in installed if name.startswith("aoa") or name in {"fastapi", "uvicorn", "duckdb", "httpx", "websockets"}]
    print("   anything of AOA or of the server:", ", ".join(heavy) or "none")

    print("2. The app without its extra")
    started = subprocess.run([str(tmp / "venv" / "bin" / "maxitor-api")], capture_output=True, text=True)
    print(f"   exit {started.returncode}: {started.stderr.strip()}")

print("3. Any language: a plain JSON Schema validator")
schema_file = "packages/open-gnomon-protocol/graph/1.1.json"
validator = Draft202012Validator(json.loads(Path(schema_file).read_text(encoding="utf-8")))
graph = json.loads(Path("packages/aoa-demo/graph.json").read_text(encoding="utf-8"))
print(f"   the demo's graph against {schema_file}:", "valid" if validator.is_valid(graph) else "refused")
broken = copy.deepcopy(graph)
del broken["edges"][0]["id"]
reasons = {error.message for error in validator.iter_errors(broken)}
reasons |= {sub.message for error in validator.iter_errors(broken) for sub in error.context or ()}
print("   the same without edges[0].id: refused —", "'id' is a required property" if "'id' is a required property" in reasons else sorted(reasons)[:1])

print("4. The app's import")
print("  ", f"{create_app.__module__}.{create_app.__name__}")

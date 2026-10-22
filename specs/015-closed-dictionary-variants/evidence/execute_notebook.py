# specs/015-closed-dictionary-variants/evidence/execute_notebook.py
"""Run a notebook's code cells in one namespace and write their output back into the notebook.

The repository's check run does not execute notebooks, and the environment has no `nbformat`,
so an example's notebook can drift from its script without anything failing. This helper is
the missing check: it executes the code cells the way a reader would, cell after cell in the
same namespace, captures what each cell prints, and stores it as the cell's output.

Usage::

    python execute_notebook.py NOTEBOOK.ipynb [NOTEBOOK.ipynb ...]

A cell that raises stops that notebook: the file is left untouched and the error is printed,
because half-written outputs are worse than stale ones.
"""

from __future__ import annotations

import codeop
import io
import json
import subprocess
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


def _run(path: Path) -> bool:
    """Execute one notebook in place; return ``False`` when a cell raised."""
    notebook: dict[str, Any] = json.loads(path.read_text())
    namespace: dict[str, Any] = {"__name__": "__main__", "__file__": str(path)}
    counts = 0
    compiler = codeop.Compile()
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        counts += 1
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                exec(compiler(source, f"{path}:cell{counts}", "exec"), namespace)
        except Exception:
            print(f"{path}: cell {counts} failed", file=sys.stderr)
            traceback.print_exc()
            return False
        printed = buffer.getvalue()
        cell["outputs"] = (
            [{"name": "stdout", "output_type": "stream", "text": printed.splitlines(keepends=True)}]
            if printed
            else []
        )
        cell["execution_count"] = counts
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
    return True


def main(argv: list[str]) -> int:
    """
    Execute every notebook named on the command line, and report how many passed.

    Each notebook runs in its own process: they register entities in one global registry, so
    two notebooks in one interpreter see each other's models and the second fails on a name
    the first already declared.
    """
    if argv[:1] == ["--one"]:
        return 0 if _run(Path(argv[1])) else 1
    failed = [
        path
        for path in argv
        if subprocess.run(
            [sys.executable, __file__, "--one", path], check=False
        ).returncode
    ]
    print(f"executed {len(argv) - len(failed)}/{len(argv)} notebooks")
    for path in failed:
        print(f"  failed: {path}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

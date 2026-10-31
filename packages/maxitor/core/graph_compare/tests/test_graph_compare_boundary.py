# packages/maxitor/core/graph_compare/tests/test_graph_compare_boundary.py
"""The comparison needs nothing beyond the standard library: no AOA, no front, no tool, no third-party package."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

PART = Path(__file__).resolve().parents[1] / "src" / "maxitor" / "graph_compare"


def _imported(module: Path) -> set[str]:
    """Every top-level module name one file imports, and every ``maxitor.*`` name in full."""
    names: set[str] = set()
    for statement in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
        if isinstance(statement, ast.Import):
            names.update(alias.name for alias in statement.names)
        elif isinstance(statement, ast.ImportFrom) and statement.module and statement.level == 0:
            names.add(statement.module)
    return names


def test_the_part_imports_only_the_standard_library_and_itself() -> None:
    """A third-party import fails here even where the boundary checker, which knows only this repository's packages, would not."""
    foreign = {
        f"{module.name}: {name}"
        for module in sorted(PART.glob("*.py"))
        for name in _imported(module)
        if name.split(".")[0] not in sys.stdlib_module_names
        and name != "maxitor.graph_compare"
        and not name.startswith("maxitor.graph_compare.")
    }
    assert foreign == set()
    assert len(list(PART.glob("*.py"))) >= 4

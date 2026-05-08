# tests/graph_contract/test_import_boundaries.py
"""Import boundary checks for the core test suite."""

from __future__ import annotations

import ast
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN_TEST_IMPORT_PREFIXES = ("maxitor",)


def _imported_roots(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module.split(".", 1)[0])
    return out


def test_tests_tree_does_not_import_maxitor() -> None:
    """``tests/`` is the action_machine suite; Maxitor keeps its own isolated tests."""
    offenders: list[str] = []
    for path in sorted(_TESTS_ROOT.rglob("*.py")):
        if any(part == "__pycache__" for part in path.parts):
            continue
        imported_roots = _imported_roots(path)
        forbidden = sorted({name for name in imported_roots if name in _FORBIDDEN_TEST_IMPORT_PREFIXES})
        if forbidden:
            rel = path.relative_to(_TESTS_ROOT.parent)
            offenders.append(f"{rel}: {', '.join(forbidden)}")

    assert not offenders, "Forbidden imports in tests/:\n" + "\n".join(offenders)

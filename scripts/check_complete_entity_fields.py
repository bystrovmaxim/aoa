#!/usr/bin/env python3
# scripts/check_complete_entity_fields.py
"""
Check that every entity relationship field declares exactly one assignment-side ``Field(...)``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pydantic merges the assignment-side ``= Field(...)`` and a ``Field(...)`` written inside
``Annotated[...]`` into one ``FieldInfo``, so runtime validation cannot prove where the
field description was written. The complete-declaration contract requires one
assignment-side ``Field(...)`` and none inside ``Annotated``. This static gate enforces
that placement on source and examples.

The checker parses source with ``ast`` only; it never imports the checked modules and never
needs a resolved model. Runtime semantic checks work without source files, and this script
does not claim ``FieldInfo`` preserves source spelling — the two checks are complementary.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Explicit file/directory roots; every ``.py`` file under them.
    Fields whose annotation references a relation container (the eight container names).
    Import aliases of ``pydantic.Field`` (``from pydantic import Field`` /
    ``from pydantic import Field as F`` / ``import pydantic`` → ``pydantic.Field``).

**Out of scope**
    Files outside the given roots.
    Runtime semantics: direction-marker count, description content, resolved targets and
    pair compatibility belong to the build validators, not this script.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

::

    python scripts/check_complete_entity_fields.py <root> [<root> ...]

Exit code 0 means no violation; 1 means at least one violation; 2 means a usage error.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_RELATION_CONTAINERS = frozenset(
    {
        "AssociationOne",
        "AssociationMany",
        "CompositeOne",
        "CompositeMany",
        "AggregateOne",
        "AggregateMany",
        "Specialization",
        "Generalization",
    }
)


def _collect_field_names(tree: ast.AST) -> set[str]:
    """Return the names in ``tree`` that resolve to ``pydantic.Field``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "pydantic":
            for alias in node.names:
                if alias.name == "Field":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pydantic":
                    names.add("pydantic.Field")
    return names


def _dotted_name(node: ast.AST) -> str:
    """Return the dotted source name of an attribute chain, e.g. ``pydantic.Field``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr}"
    return ""


def _is_field_call(node: ast.AST, field_names: set[str]) -> bool:
    """True when ``node`` is a call to a name that resolves to ``pydantic.Field``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in field_names
    if isinstance(func, ast.Attribute):
        return _dotted_name(func) in field_names
    return False


def _references_relation_container(node: ast.AST) -> bool:
    """True when ``node`` names one of the eight relation containers anywhere inside it."""
    return any(isinstance(item, ast.Name) and item.id in _RELATION_CONTAINERS for item in ast.walk(node))


def _annotation_side_field(node: ast.AST, field_names: set[str]) -> bool:
    """True when a ``Field(...)`` call appears inside the annotation subtree."""
    return any(_is_field_call(item, field_names) for item in ast.walk(node))


def _check_annassign(
    node: ast.AnnAssign,
    field_names: set[str],
    path: str,
    violations: list[str],
) -> None:
    """Apply the single-assignment-side-Field rule to one annotated field."""
    if not _references_relation_container(node.annotation):
        return
    name = node.target.id if isinstance(node.target, ast.Name) else "<anonymous>"
    if _annotation_side_field(node.annotation, field_names):
        violations.append(
            f"{path}:{node.lineno}: field '{name}' has a Field(...) inside Annotated; "
            f"write a single assignment-side Field(...)"
        )
        return
    if node.value is None:
        violations.append(
            f"{path}:{node.lineno}: field '{name}' has no assignment-side Field(...); write = Field(description=...)"
        )
        return
    if not _is_field_call(node.value, field_names):
        violations.append(
            f"{path}:{node.lineno}: field '{name}' has an unsupported assignment; write = Field(description=...)"
        )


def _check_file(path: Path) -> list[str]:
    """Return the violations in one Python file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return [f"{path}:1: cannot parse source: {exc}"]
    field_names = _collect_field_names(tree)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            _check_annassign(node, field_names, str(path), violations)
    return violations


def _iter_python_files(root: Path) -> list[Path]:
    """Return the ``.py`` files under ``root`` (one file if ``root`` is a file)."""
    if root.is_file():
        return [root] if root.suffix == ".py" else []
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def main(argv: list[str] | None = None) -> int:
    """Run the source gate and return the process exit code."""
    parser = argparse.ArgumentParser(description="Check one assignment-side Field per entity relation field.")
    parser.add_argument("roots", nargs="+", help="Files or directories to scan.")
    args = parser.parse_args(argv)

    violations: list[str] = []
    for raw in args.roots:
        root = Path(raw)
        for path in _iter_python_files(root):
            violations.extend(_check_file(path))

    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())

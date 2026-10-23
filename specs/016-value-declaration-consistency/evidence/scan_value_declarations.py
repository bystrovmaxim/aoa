# specs/016-value-declaration-consistency/evidence/scan_value_declarations.py
"""
Count the declaration forms before and after the migration.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The feature replaces the class-name declaration form with ``value(...)``. This
scan is the evidence for SC-001 and SC-002: it reports how many declarations use
each form, and how many undefined-name suppressions exist, per area.

A declaration is an uppercase assignment inside a class body whose base name
ends in ``EnumEntity`` or ``StateEntity``. An ordinary constructor call outside
such a body — a deliberately built copy in an example — is not a declaration and
is not counted.

Run from the repository root::

    uv run python specs/016-value-declaration-consistency/evidence/scan_value_declarations.py
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

_ALIAS_SUPPRESSION = re.compile(r"noqa:?\s*F821|type:\s*ignore\[name-defined\]")
_KIND_SUFFIXES = ("EnumEntity", "StateEntity")

_AREAS = ("packages/aoa-action-machine", "packages/aoa-maxitor", "packages/aoa-demo", "examples")


class _Declarations(ast.NodeVisitor):
    """Collect the declaration forms and the classes that declare them."""

    def __init__(self) -> None:
        """Start with empty counts."""
        self.class_name = 0
        self.value_form = 0
        self.declaring_classes = 0
        self._declaring_depth = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Count one declaring class, then visit its body in that mode."""
        declaring = any(
            isinstance(base, ast.Name) and base.id.endswith(_KIND_SUFFIXES) for base in node.bases
        )
        if declaring:
            self.declaring_classes += 1
            self._declaring_depth += 1
        self.generic_visit(node)
        if declaring:
            self._declaring_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        """Count an uppercase assignment to a call, in a declaring class body only."""
        if self._declaring_depth and isinstance(node.value, ast.Call):
            func = node.value.func
            name = func.id if isinstance(func, ast.Name) else ""
            if name == "value" and all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
                self.value_form += 1
            elif name.endswith(_KIND_SUFFIXES) and all(
                isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
            ):
                self.class_name += 1
        self.generic_visit(node)


def _python_files(root: Path) -> Iterator[Path]:
    """Yield the Python files under ``root``, excluding caches and environments."""
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or ".venv" in path.parts:
            continue
        yield path


def _scan(paths: Iterator[Path]) -> tuple[int, int, int, int, int, int]:
    """Return the class-name, ``value(...)``, suppression, class and file counts."""
    class_name = value_form = suppressions = classes = files = suppressed_files = 0
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        visitor = _Declarations()
        visitor.visit(tree)
        class_name += visitor.class_name
        value_form += visitor.value_form
        classes += visitor.declaring_classes
        if visitor.class_name or visitor.value_form:
            files += 1
        hits = len(_ALIAS_SUPPRESSION.findall(text))
        suppressions += hits
        suppressed_files += 1 if hits else 0
    return class_name, value_form, suppressions, classes, files, suppressed_files


def main() -> None:
    """Print the counts per area and the total."""
    totals = [0, 0, 0, 0, 0, 0]
    header = (
        f"{'area':30} {'class-name':>10} {'value(...)':>10} {'suppressed':>10} "
        f"{'classes':>8} {'files':>6} {'sup files':>10}"
    )
    print(header)
    for area in _AREAS:
        counts = _scan(_python_files(Path(area)))
        totals = [left + right for left, right in zip(totals, counts, strict=True)]
        print(
            f"{area:30} {counts[0]:>10} {counts[1]:>10} {counts[2]:>10} "
            f"{counts[3]:>8} {counts[4]:>6} {counts[5]:>10}"
        )
    print(
        f"{'total':30} {totals[0]:>10} {totals[1]:>10} {totals[2]:>10} "
        f"{totals[3]:>8} {totals[4]:>6} {totals[5]:>10}"
    )


if __name__ == "__main__":
    main()

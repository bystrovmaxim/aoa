"""Migrate lifecycle axes: statuses move from the axis to the state type.

The surface is unchanged — ``DRAFT = OrderStateEntity(...)`` moves verbatim from
the axis body to the state type body. The axis keeps ``_template`` and its bare
status names become ``OrderStateEntity.DRAFT``. ``StateVocabulary`` leaves the
bases and, when unused, the import. Each moved status line gets ``# noqa: F821``
because ruff cannot resolve the class-name alias statically.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
AXIS_BASE = "Lifecycle"
STATE_BASE = "BaseStateEntity"
VOCABULARY = "StateVocabulary"
DOMAIN_MODULE = "aoa.action_machine.domain"


def iter_class_nodes(statements: list[ast.stmt]):
    """Yield module-level and compound-block classes, never function-local ones."""
    for stmt in statements:
        if isinstance(stmt, ast.ClassDef):
            yield stmt
            yield from iter_class_nodes(stmt.body)
        elif isinstance(stmt, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            yield from iter_class_nodes(stmt.body)
            yield from iter_class_nodes(getattr(stmt, "orelse", []))
            yield from iter_class_nodes(getattr(stmt, "finalbody", []))
            for handler in getattr(stmt, "handlers", []):
                yield from iter_class_nodes(handler.body)


def base_names(node: ast.ClassDef) -> set[str]:
    """Return the last names of a class's bases."""
    names: set[str] = set()
    for base in node.bases:
        text = ast.unparse(base)
        names.add(text.split("[")[0].rsplit(".", 1)[-1])
    return names


def is_catalogue_axis(node: ast.ClassDef) -> bool:
    """True for a Lifecycle axis that applies StateVocabulary."""
    names = base_names(node)
    return AXIS_BASE in names and VOCABULARY in names


def status_assignments(axis: ast.ClassDef) -> list[tuple[ast.Assign, str]]:
    """Return status assignments and the state type each one calls."""
    out: list[tuple[ast.Assign, str]] = []
    for stmt in axis.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        value = stmt.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        if target.id.startswith("_"):
            continue
        call_name = ast.unparse(value.func).rsplit(".", 1)[-1]
        if not call_name:
            continue
        out.append((stmt, call_name))
    return out


def template_names(axis: ast.ClassDef) -> list[ast.Name]:
    """Return the bare status names used by ``.state(...)`` and ``.to(...)``."""
    names: list[ast.Name] = []
    for stmt in axis.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        if not isinstance(target, ast.Name) or target.id != "_template":
            continue
        for node in ast.walk(stmt.value):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"state", "to"}:
                names.extend(arg for arg in node.args if isinstance(arg, ast.Name))
    return names


def dedent(indent: str, line: str) -> str:
    """Remove the given leading indent from a line."""
    return line[len(indent) :] if line.startswith(indent) else line.lstrip(" ")


def migrate_file(path: Path) -> dict[str, Any]:
    """Rewrite one module; return a per-file report."""
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    tree = ast.parse(source)
    classes = list(iter_class_nodes(tree.body))
    state_types = {node.name: node for node in classes if STATE_BASE in base_names(node)}
    axes = [node for node in classes if is_catalogue_axis(node)]
    report: dict[str, Any] = {"file": path.resolve().relative_to(ROOT).as_posix(), "migrated": [], "skipped": []}
    if not axes:
        return report

    full_line_edits: dict[int, str] = {}
    delete_lines: set[int] = set()
    insert_after: dict[int, list[str]] = {}
    column_edits: list[tuple[int, int, int, str]] = []

    for axis in axes:
        assignments = status_assignments(axis)
        state_type_names = {call for _, call in assignments}
        if not assignments:
            report["skipped"].append({"axis": axis.name, "reason": "no statuses (negative example)"})
            continue
        if len(state_type_names) != 1:
            report["skipped"].append(
                {"axis": axis.name, "reason": f"mixed status types: {sorted(state_type_names)}"}
            )
            continue
        state_name = state_type_names.pop()
        state_node = state_types.get(state_name)
        if state_node is None:
            report["skipped"].append({"axis": axis.name, "reason": f"state type {state_name} not in module"})
            continue

        axis_indent = " " * axis.body[0].col_offset
        state_indent = " " * state_node.body[0].col_offset
        moved: list[str] = []
        for assignment, _ in assignments:
            start = assignment.lineno
            end = assignment.end_lineno or start
            segment = lines[start - 1 : end]
            for index, line in enumerate(segment):
                text = dedent(axis_indent, line)
                if index == 0 and "noqa" not in text:
                    text = text.rstrip("\n") + "  # noqa: F821\n"
                moved.append(state_indent + text)
            delete_lines.update(range(start, end + 1))

        insert_after.setdefault(state_node.end_lineno or state_node.lineno, []).extend(moved)
        for name in template_names(axis):
            column_edits.append(
                (
                    name.lineno,
                    name.col_offset,
                    name.end_col_offset or (name.col_offset + len(name.id)),
                    f"{state_name}.{name.id}",
                )
            )
        header = lines[axis.lineno - 1]
        new_header = re.sub(r",\s*StateVocabulary", "", header)
        new_header = re.sub(r"StateVocabulary\s*,\s*", "", new_header)
        if new_header != header:
            full_line_edits[axis.lineno] = new_header
        report["migrated"].append({"axis": axis.name, "state_type": state_name, "statuses": len(assignments)})

    if not report["migrated"]:
        return report

    # Apply column edits first, line by line, from right to left.
    by_line: dict[int, list[tuple[int, int, str]]] = {}
    for lineno, start, end, text in column_edits:
        by_line.setdefault(lineno, []).append((start, end, text))
    for lineno, edits in by_line.items():
        line = full_line_edits.get(lineno, lines[lineno - 1])
        for start, end, text in sorted(edits, reverse=True):
            line = line[:start] + text + line[end:]
        full_line_edits[lineno] = line

    result: list[str] = []
    for lineno, line in enumerate(lines, start=1):
        if lineno in delete_lines:
            continue
        result.append(full_line_edits.get(lineno, line))
        if lineno in insert_after:
            result.extend(insert_after[lineno])
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            result.append("\n")
    text = "".join(result)

    # Remove the import only when the mixin is no longer used as a name.
    try:
        edited_tree = ast.parse(text)
    except SyntaxError:
        path.write_text(text)
        return report
    if not any(isinstance(node, ast.Name) and node.id == VOCABULARY for node in ast.walk(edited_tree)):
        text = re.sub(r"^[ \t]*StateVocabulary,\s*\n", "", text, flags=re.MULTILINE)
        text = re.sub(r",\s*StateVocabulary\b", "", text)
        text = re.sub(r"\bStateVocabulary\s*,\s*", "", text)
    path.write_text(text)
    return report


def main() -> int:
    """Run the migration over the requested roots."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--report", type=Path, default=Path(__file__).parent / "migration.report.json")
    args = parser.parse_args()
    roots = [ROOT / root for root in args.root] or [
        ROOT / "packages" / "aoa-demo" / "src",
        ROOT / "examples",
        ROOT / "packages" / "aoa-action-machine" / "tests",
    ]
    reports = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                report = migrate_file(path)
            except SyntaxError as exc:
                reports.append({"file": path.relative_to(ROOT).as_posix(), "error": str(exc)})
                continue
            if report["migrated"] or report["skipped"]:
                reports.append(report)
    args.report.write_text(json.dumps(reports, indent=2) + "\n")
    migrated = sum(len(r.get("migrated", [])) for r in reports)
    skipped = sum(len(r.get("skipped", [])) for r in reports)
    print(f"migrated axes: {migrated}; skipped: {skipped}; files: {len(reports)}")
    for report in reports:
        for item in report.get("skipped", []):
            print(f"  skipped {report['file']}: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

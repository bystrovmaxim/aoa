"""Scan the lifecycle axes and state types before and after the migration.

The declarations are read with ``ast`` so docstring snippets are not counted.
The demo baseline imports the demo model and records what the runtime exposes:
status objects, templates, entity lifecycle fields and the graph state rows.
"""

from __future__ import annotations

import argparse
import ast
import json
import pkgutil
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent

AXIS_BASE = "Lifecycle"
STATE_BASE = "BaseStateEntity"
VOCABULARY = "StateVocabulary"


def iter_py_files(root: Path) -> list[Path]:
    """Return every Python file under ``root``, sorted, without caches."""
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def root_key(path: Path) -> str:
    """Classify a file by the corpus area it belongs to."""
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("packages/aoa-demo/src/"):
        return "demo"
    if rel.startswith("examples/"):
        return "examples"
    if rel.startswith("packages/aoa-action-machine/tests/"):
        return "framework tests"
    return "other"


def base_name(node: ast.expr) -> str:
    """Return the last name of a base expression, including a subscript."""
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def last_name(node: ast.expr) -> str:
    """Return the last component of a name or attribute expression."""
    text = ast.unparse(node)
    return text.rsplit(".", 1)[-1]


def parse_template(node: ast.expr) -> list[dict[str, Any]]:
    """Read a ``Lifecycle().state(...).to(...).initial()`` chain."""
    events: list[tuple[str, list[ast.expr]]] = []
    current: ast.expr = node
    while isinstance(current, ast.Call):
        func = current.func
        if isinstance(func, ast.Attribute):
            events.append((func.attr, list(current.args)))
            current = func.value
        else:
            break
    events.reverse()
    states: list[dict[str, Any]] = []
    state: dict[str, Any] | None = None
    for attr, args in events:
        if attr == "state" and args:
            state = {"state": last_name(args[0]), "classification": None, "targets": []}
            states.append(state)
        elif attr == "to" and state is not None:
            state["targets"].extend(last_name(arg) for arg in args)
        elif attr in {"initial", "intermediate", "final"} and state is not None:
            state["classification"] = attr
    return states


def read_statuses(body: list[ast.stmt]) -> list[dict[str, Any]]:
    """Read ``NAME = TheType(...)`` status declarations from a class body."""
    statuses: list[dict[str, Any]] = []
    for stmt in body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        value = stmt.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        status_type = ast.unparse(value.func)
        if target.id.startswith("_") or status_type.rsplit(".", 1)[-1] == "Lifecycle":
            continue
        fields = {kw.arg: ast.unparse(kw.value) for kw in value.keywords if kw.arg}
        statuses.append(
            {
                "name": target.id,
                "type": status_type,
                "code": fields.get("code"),
                "display_name": fields.get("display_name"),
                "fields": fields,
            }
        )
    return statuses


def read_fields(body: list[ast.stmt]) -> list[dict[str, Any]]:
    """Read annotated fields from a state type body."""
    fields: list[dict[str, Any]] = []
    for stmt in body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fields.append(
                {
                    "name": stmt.target.id,
                    "annotation": ast.unparse(stmt.annotation),
                    "default": ast.unparse(stmt.value) if stmt.value is not None else None,
                }
            )
    return fields


def read_template(body: list[ast.stmt]) -> list[dict[str, Any]]:
    """Read ``_template`` from a class body."""
    for stmt in body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and target.id == "_template":
                return parse_template(stmt.value)
    return []


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


def is_catalogue_axis(node: ast.ClassDef) -> bool:
    """True for an old vocabulary axis or a new generic axis, never a plain Lifecycle."""
    if AXIS_BASE not in {base_name(base) for base in node.bases}:
        return False
    if any(base_name(base) == VOCABULARY for base in node.bases):
        return True
    return any(isinstance(base, ast.Subscript) and base_name(base) == AXIS_BASE for base in node.bases)


def declaration_scan() -> dict[str, Any]:
    """Read every axis and state type with ``ast``."""
    axes: list[dict[str, Any]] = []
    state_types: list[dict[str, Any]] = []
    for path in iter_py_files(ROOT / "packages") + iter_py_files(ROOT / "examples"):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in iter_class_nodes(tree.body):
            bases = {base_name(base) for base in node.bases}
            record = {
                "file": path.relative_to(ROOT).as_posix(),
                "module": path.relative_to(ROOT).with_suffix("").as_posix().replace("/", "."),
                "qualname": node.name,
                "private": node.name.startswith("_"),
                "root": root_key(path),
            }
            if is_catalogue_axis(node):
                statuses = read_statuses(node.body)
                template = read_template(node.body)
                axes.append(
                    {
                        **record,
                        "state_vocabulary": VOCABULARY in bases,
                        "state_type": statuses[0]["type"] if statuses else None,
                        "statuses": statuses,
                        "template": template,
                    }
                )
            if STATE_BASE in bases:
                state_types.append(
                    {**record, "fields": read_fields(node.body), "statuses": read_statuses(node.body)}
                )
    axes.sort(key=lambda a: (a["root"], a["file"], a["qualname"]))
    state_types.sort(key=lambda s: (s["root"], s["file"], s["qualname"]))
    counts = {
        "axes": len(axes),
        "axes_by_root": dict(Counter(a["root"] for a in axes)),
        "state_types": len(state_types),
        "state_types_by_root": dict(Counter(s["root"] for s in state_types)),
    }
    return {"counts": counts, "axes": axes, "state_types": state_types}


def coverage(scan: dict[str, Any]) -> list[dict[str, Any]]:
    """Report axes whose template does not list every declared status."""
    by_type = {s["qualname"]: s for s in scan["state_types"]}
    problems: list[dict[str, Any]] = []
    for axis in scan["axes"]:
        statuses = axis["statuses"]
        if not statuses and axis["state_type"]:
            state_type = by_type.get(axis["state_type"].rsplit(".", 1)[-1])
            statuses = state_type["statuses"] if state_type else []
        declared = {status["name"] for status in statuses}
        used = {state["state"] for state in axis["template"]}
        missing = sorted(declared - used)
        if missing:
            problems.append({"axis": axis["qualname"], "file": axis["file"], "missing": missing})
    return problems


def demo_baseline() -> dict[str, Any]:
    """Import the demo model and record the runtime view of every axis."""
    import aoa.demo.model as demo
    from aoa.action_machine.domain import BaseEntity, BaseStateEntity, Lifecycle
    from aoa.action_machine.graph.nodes.lifecycle_graph_node import LifeCycleGraphNode

    modules = [demo]
    modules.extend(
        pkgutil.walk_packages(demo.__path__, demo.__name__ + ".")
    )
    axes: dict[str, Any] = {}
    state_types: dict[str, Any] = {}
    entities: dict[str, type[BaseEntity]] = {}
    errors: list[str] = []
    for info in modules:
        name = info.name if hasattr(info, "name") else info.__name__
        try:
            module = __import__(name, fromlist=["*"])
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        for value in vars(module).values():
            if not isinstance(value, type):
                continue
            qualname = f"{value.__module__}.{value.__qualname__}"
            try:
                if issubclass(value, Lifecycle) and value.__module__ == module.__name__:
                    axes[qualname] = value
                elif issubclass(value, BaseStateEntity) and value.__module__ == module.__name__:
                    state_types[qualname] = value
                elif issubclass(value, BaseEntity) and value.__module__ == module.__name__:
                    entities[qualname] = value
            except TypeError:
                continue

    axis_rows: list[dict[str, Any]] = []
    for qualname, axis in sorted(axes.items()):
        members = tuple(getattr(axis, "members", ()))
        state_type = getattr(axis, "_state_type", None)
        if not members and state_type is not None:
            members = tuple(getattr(state_type, "members", ()))
        template = axis._get_template()
        states = []
        if template is not None:
            states = [
                {
                    "key": info.key,
                    "display_name": info.display_name,
                    "state_type": info.state_type.value,
                    "transitions": sorted(info.transitions),
                }
                for info in template.get_states().values()
            ]
        axis_rows.append(
            {
                "qualname": qualname,
                "state_type": getattr(state_type, "__qualname__", None),
                "members": [member.model_dump(mode="json") for member in members],
                "template": states,
            }
        )

    type_rows: list[dict[str, Any]] = []
    for qualname, state_type in sorted(state_types.items()):
        type_rows.append(
            {
                "qualname": qualname,
                "fields": {
                    name: str(field.annotation) for name, field in state_type.model_fields.items()
                },
                "members": [m.code for m in getattr(state_type, "members", ())],
            }
        )

    entity_fields: list[dict[str, Any]] = []
    state_rows: list[dict[str, Any]] = []
    for entity_qualname, entity in sorted(entities.items()):
        for field_name, field in entity.model_fields.items():
            annotation = field.annotation
            if not isinstance(annotation, type) or not issubclass(annotation, Lifecycle):
                continue
            entity_fields.append(
                {
                    "entity": entity_qualname,
                    "field": field_name,
                    "axis": f"{annotation.__module__}.{annotation.__qualname__}",
                }
            )
            try:
                node = LifeCycleGraphNode(entity, field_name, annotation)
                state_rows.append(
                    {
                        "entity": entity_qualname,
                        "field": field_name,
                        "axis": annotation.__qualname__,
                        "states": [state.to_dict() for state in node.states],
                    }
                )
            except Exception as exc:  # pragma: no cover - diagnostic path
                errors.append(f"{entity_qualname}.{field_name}: {type(exc).__name__}: {exc}")

    return {
        "axes": axis_rows,
        "state_types": type_rows,
        "entity_lifecycle_fields": entity_fields,
        "state_rows": state_rows,
        "errors": errors,
    }


def main() -> int:
    """Run the scan and write the two JSON artefacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=EVIDENCE / "scan.before.json")
    parser.add_argument("--baseline-out", type=Path, default=EVIDENCE / "baseline.before.json")
    parser.add_argument("--skip-runtime", action="store_true")
    args = parser.parse_args()

    scan = declaration_scan()
    scan["coverage_problems"] = coverage(scan)
    scan["counts"]["uncovered"] = sum(len(p["missing"]) for p in scan["coverage_problems"])
    args.out.write_text(json.dumps(scan, indent=2, sort_keys=True) + "\n")

    counts = scan["counts"]
    print(
        f"axes: {counts['axes']} {counts['axes_by_root']}; "
        f"state types: {counts['state_types']} {counts['state_types_by_root']}; "
        f"uncovered: {counts['uncovered']}"
    )
    if scan["coverage_problems"]:
        for problem in scan["coverage_problems"]:
            print(f"  {problem['axis']}: missing {problem['missing']}")
    if args.skip_runtime:
        return 0

    baseline = demo_baseline()
    args.baseline_out.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n")
    print(
        f"baseline: {len(baseline['axes'])} axes, {len(baseline['state_types'])} state types, "
        f"{len(baseline['entity_lifecycle_fields'])} entity fields, "
        f"{len(baseline['state_rows'])} state rows"
    )
    for error in baseline["errors"]:
        print(f"  baseline error: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

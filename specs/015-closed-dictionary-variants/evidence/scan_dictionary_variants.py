# specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py
"""Count the dictionary and specialization facts this feature is measured against.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Produce the numbers the specification quotes: how many closed dictionaries
exist, how many values they declare, how many currency fields are still plain
strings, and how many specialization axes still restate their codes as a
``Literal``. The script walks Python sources and notebook code cells, so script
and notebook stay in step.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py
    python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py --json out.json
    python specs/015-closed-dictionary-variants/evidence/scan_dictionary_variants.py --graph

With the project environment: ``uv run python …``. When the uv cache is not
writable, the checked-in virtual environment works the same way:
``.venv/bin/python …``.

``--graph`` also builds the demo interchange graph and records its node types,
entity kinds, dictionary nodes and axis edges. Building it imports the demo
model and takes a few seconds.

═══════════════════════════════════════════════════════════════════════════════
WHAT IT COUNTS
═══════════════════════════════════════════════════════════════════════════════

- dictionaries: classes inheriting ``BaseEnumEntity``, decorated or not
- declared values: class-body assignments of the declaring type
- duplicate codes and empty decorated dictionaries
- ``*_iso`` string fields, of which currency codes
- specialization axes: ``Specialization[...]`` annotations
- ``Classifier`` markers: those with ``codes=Literal[...]``, those with a
  positional ``Literal``, those already on the dictionary form
- ``Classifier`` declarations that still carry a ``Literal`` anywhere
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]

AREAS: dict[str, Path] = {
    "demo": ROOT / "packages" / "aoa-demo" / "src",
    "examples": ROOT / "examples",
    "framework_tests": ROOT / "packages" / "aoa-action-machine" / "tests",
    "framework_src": ROOT / "packages" / "aoa-action-machine" / "src",
    "maxitor": ROOT / "packages" / "aoa-maxitor" / "src",
}

_EMPTY_COUNTS: dict[str, int] = {
    "files": 0,
    "notebooks": 0,
    "dictionaries": 0,
    "decorated_dictionaries": 0,
    "empty_decorated_dictionaries": 0,
    "declared_values": 0,
    "duplicate_codes": 0,
    "iso_str_fields": 0,
    "currency_iso_str_fields": 0,
    "axes": 0,
    "classifier_calls": 0,
    "classifier_with_literal": 0,
    "classifier_with_codes": 0,
    "classifier_with_variant": 0,
}


def _new_counts() -> dict[str, int]:
    """Return a fresh counter bundle."""
    return dict(_EMPTY_COUNTS)


def _dotted(node: ast.expr) -> str:
    """Return a dotted name for ``Name``/``Attribute`` nodes, or an empty string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = _dotted(node.value)
        return f"{head}.{node.attr}" if head else node.attr
    return ""


def _is_literal(node: ast.expr | None) -> bool:
    """True when the node is a ``Literal[...]`` subscript."""
    return isinstance(node, ast.Subscript) and _dotted(node.value).split(".")[-1] == "Literal"


def _is_entity_decorator(node: ast.expr) -> bool:
    """True for ``@entity`` and ``@entity(...)``."""
    target = node.func if isinstance(node, ast.Call) else node
    return _dotted(target).split(".")[-1] == "entity"


def _call_is_dictionary_value(node: ast.expr, class_name: str) -> ast.Call | None:
    """Return the call when ``node`` constructs ``class_name``."""
    if isinstance(node, ast.Call) and _dotted(node.func).split(".")[-1] == class_name:
        return node
    return None


def _code_of(call: ast.Call) -> str | None:
    """Return the ``code=`` string of a value declaration, or ``None``."""
    for keyword in call.keywords:
        if keyword.arg == "code" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _literal_codes(node: ast.expr | None) -> list[str]:
    """Return the string members of a ``Literal[...]`` node."""
    if not _is_literal(node) or node is None:
        return []
    slice_node = node.slice
    members = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
    return [member.value for member in members if isinstance(member, ast.Constant) and isinstance(member.value, str)]


def _class_values(tree: ast.Module, class_name: str) -> list[str]:
    """Return the declared ``code`` values of a dictionary class in this module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            codes: list[str] = []
            for statement in node.body:
                if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                    continue
                value = _call_is_dictionary_value(statement.value, class_name)
                if value is not None and (code := _code_of(value)) is not None:
                    codes.append(code)
            return codes
    return []


def _specialization_node(annotation: ast.expr) -> ast.Subscript | None:
    """Return the ``Specialization[...]`` subscript, unwrapping ``Annotated[...]``."""
    node: ast.expr = annotation
    if isinstance(node, ast.Subscript) and _dotted(node.value).split(".")[-1] == "Annotated":
        inner = node.slice
        parts = inner.elts if isinstance(inner, ast.Tuple) else [inner]
        if parts:
            node = parts[0]
    if isinstance(node, ast.Subscript) and _dotted(node.value).split(".")[-1] == "Specialization":
        return node
    return None


def axis_entries(tree: ast.Module, file_label: str, medium: str) -> list[dict[str, Any]]:
    """Return one entry per ``Specialization[…]`` field with the codes it declares."""
    entries: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            annotation = statement.annotation
            specialization = _specialization_node(annotation)
            if specialization is None:
                continue
            field = statement.target.id if isinstance(statement.target, ast.Name) else getattr(statement.target, "attr", "")
            codes: list[str] = []
            source = ""
            classifier_field = ""
            for inner in ast.walk(annotation):
                if not (isinstance(inner, ast.Call) and _dotted(inner.func).split(".")[-1] == "Classifier"):
                    continue
                for keyword in inner.keywords:
                    if keyword.arg == "field" and isinstance(keyword.value, ast.Constant):
                        classifier_field = str(keyword.value.value)
                    if keyword.arg == "codes":
                        codes = _literal_codes(keyword.value)
                        source = "literal"
                if not classifier_field and inner.args and isinstance(inner.args[0], ast.Constant):
                    classifier_field = str(inner.args[0].value)
            if not source:
                slice_node = specialization.slice
                parts = slice_node.elts if isinstance(slice_node, ast.Tuple) else [slice_node]
                if len(parts) >= 2:
                    dictionary = _dotted(parts[1]).split(".")[-1]
                    codes = _class_values(tree, dictionary)
                    source = "dictionary"
            entries.append(
                {
                    "file": file_label,
                    "medium": medium,
                    "class": node.name,
                    "field": field,
                    "classifier_field": classifier_field,
                    "codes": codes,
                    "codes_source": source,
                }
            )
    return entries


def scan_module(tree: ast.Module, counts: dict[str, int]) -> None:
    """Update ``counts`` from one parsed module."""
    class_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(_dotted(base).split(".")[-1] == "BaseEnumEntity" for base in node.bases)
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_dictionary = node.name in class_names
            if is_dictionary:
                counts["dictionaries"] += 1
                decorated = any(_is_entity_decorator(dec) for dec in node.decorator_list)
                if decorated:
                    counts["decorated_dictionaries"] += 1
                codes: list[str] = []
                for statement in node.body:
                    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                        continue
                    value = _call_is_dictionary_value(statement.value, node.name)
                    if value is None:
                        continue
                    counts["declared_values"] += 1
                    code = _code_of(value)
                    if code is not None:
                        codes.append(code)
                if decorated and not codes:
                    counts["empty_decorated_dictionaries"] += 1
                counts["duplicate_codes"] += len(codes) - len(set(codes))

            for statement in node.body:
                if not isinstance(statement, ast.AnnAssign):
                    continue
                target = statement.target
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                annotation = _dotted(statement.annotation).split(".")[-1]
                if annotation == "str" and "iso" in name:
                    counts["iso_str_fields"] += 1
                    if "currency" in name:
                        counts["currency_iso_str_fields"] += 1

        if isinstance(node, ast.Subscript) and _dotted(node.value).split(".")[-1] == "Specialization":
            counts["axes"] += 1

        if isinstance(node, ast.Call) and _dotted(node.func).split(".")[-1] == "Classifier":
            counts["classifier_calls"] += 1
            keywords = {keyword.arg for keyword in node.keywords}
            if "codes" in keywords:
                counts["classifier_with_codes"] += 1
            if "variant" in keywords:
                counts["classifier_with_variant"] += 1
            has_literal = any(_is_literal(arg) for arg in node.args) or any(
                _is_literal(keyword.value) for keyword in node.keywords
            )
            if has_literal:
                counts["classifier_with_literal"] += 1


def _notebook_sources(path: Path) -> list[str]:
    """Return the code cells of a notebook, joined per cell."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    sources: list[str] = []
    for cell in payload.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        sources.append("".join(source) if isinstance(source, list) else str(source))
    return sources


def scan_area(path: Path) -> dict[str, Any]:
    """Walk one area and return separate script and notebook counts."""
    scripts = _new_counts()
    notebooks = _new_counts()
    entries: list[dict[str, Any]] = []
    files = 0
    notebook_files = 0
    for file_path in sorted(path.rglob("*.py")):
        files += 1
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except (OSError, SyntaxError):
            continue
        scan_module(tree, scripts)
        entries.extend(axis_entries(tree, str(file_path.relative_to(ROOT)), "script"))
    for file_path in sorted(path.rglob("*.ipynb")):
        notebook_files += 1
        for source in _notebook_sources(file_path):
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            scan_module(tree, notebooks)
            entries.extend(axis_entries(tree, str(file_path.relative_to(ROOT)), "notebook"))
    return {
        "files": files,
        "notebook_files": notebook_files,
        "scripts": scripts,
        "notebooks": notebooks,
        "axes": sorted(entries, key=lambda entry: (entry["file"], entry["class"], entry["field"])),
    }


def demo_graph_facts() -> dict[str, Any]:
    """Build the demo interchange graph and return the facts this feature moves."""
    from aoa.demo.model.interchange_demo_coordinator import build_registered_interchange_coordinator

    coordinator = build_registered_interchange_coordinator()
    document = json.loads(coordinator.to_json())
    nodes = document.get("nodes", [])
    edges = document.get("edges", [])

    by_type: dict[str, int] = {}
    entity_kinds: dict[str, int] = {}
    dictionary_nodes: list[str] = []
    references = 0
    for node in nodes:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
        properties = node.get("properties") or {}
        if node["type"] == "Entity":
            kind = str(properties.get("entity_kind", ""))
            entity_kinds[kind] = entity_kinds.get(kind, 0) + 1
            if kind == "enum":
                dictionary_nodes.append(node["id"])
        if node["type"] == "EntityField" and properties.get("reference_qualname"):
            references += 1

    axis_edges = [edge for edge in edges if edge.get("type") == "entity_specialization"]
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "node_types": dict(sorted(by_type.items())),
        "entity_kinds": dict(sorted(entity_kinds.items())),
        "dictionary_nodes": sorted(dictionary_nodes),
        "reference_fields": references,
        "specialization_edges": len(axis_edges),
        "axis_edges_with_dictionary": sum(
            1 for edge in axis_edges if (edge.get("properties") or {}).get("dictionary_qualname")
        ),
        "axis_edges_with_classifier_field": sum(
            1 for edge in axis_edges if (edge.get("properties") or {}).get("classifier_field")
        ),
    }


def _tools() -> dict[str, str]:
    """Return the tool versions that make the measurement reproducible."""
    versions: dict[str, str] = {"python": sys.version.split()[0]}
    try:
        versions["uv"] = subprocess.run(
            ["uv", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        versions["uv"] = "unavailable"
    try:
        import pydantic

        versions["pydantic"] = pydantic.VERSION
    except ImportError:
        versions["pydantic"] = "unavailable"
    return versions


def _commit() -> str:
    """Return the current commit hash, or an empty string."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def scan(include_graph: bool) -> dict[str, Any]:
    """Return the whole report."""
    areas: dict[str, Any] = {}
    totals_scripts = _new_counts()
    totals_notebooks = _new_counts()
    for name, path in AREAS.items():
        area = scan_area(path) if path.exists() else {
            "files": 0,
            "notebook_files": 0,
            "scripts": _new_counts(),
            "notebooks": _new_counts(),
            "axes": [],
        }
        areas[name] = area
        for key, value in area["scripts"].items():
            totals_scripts[key] += value
        for key, value in area["notebooks"].items():
            totals_notebooks[key] += value
    totals = {
        "files": sum(area["files"] for area in areas.values()),
        "notebook_files": sum(area["notebook_files"] for area in areas.values()),
        "scripts": totals_scripts,
        "notebooks": totals_notebooks,
    }

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(),
        "tools": _tools(),
        "areas": areas,
        "totals": totals,
    }
    if include_graph:
        report["demo_graph"] = demo_graph_facts()
    return report


def main() -> int:
    """Print the report and optionally write it to a file."""
    parser = argparse.ArgumentParser(description="Count dictionary and specialization facts.")
    parser.add_argument("--json", metavar="PATH", help="write the report to this path")
    parser.add_argument("--graph", action="store_true", help="also build the demo graph and record its facts")
    args = parser.parse_args()

    report = scan(include_graph=args.graph)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

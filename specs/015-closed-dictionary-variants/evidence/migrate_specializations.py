# specs/015-closed-dictionary-variants/evidence/migrate_specializations.py
"""Plan, and then perform, the move of an axis from `Classifier(codes=Literal[…])` to a dictionary.

The codemod recognizes one axis shape: a head class whose field is typed
``Specialization[A | B]`` and carries ``Classifier("field", Literal["a", "b"])``. For
each axis it names the dictionary it would create, the codes it would declare, the
classifier field it would remove, and the classes whose marker names a code. It also
counts the constructions that pass the classifier field as a keyword, because those
are the sites a human has to look at: the field is going away.

Usage::

    python migrate_specializations.py --plan FILE...
    python migrate_specializations.py --write FILE...      # not implemented yet

`--plan` prints one JSON object per axis and changes nothing. The counters are what
the migration task (T036/T037) reads before any file is touched.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


def _dotted(node: ast.AST) -> str:
    """Return the dotted source name of an attribute or name node, or an empty string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _classifier_call(node: ast.AST) -> ast.Call | None:
    """Return the ``Classifier(...)`` call inside ``node``, if there is one."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and _dotted(child.func) == "Classifier":
            return child
    return None


def _subscribed_container(node: ast.AST, container: str) -> ast.Subscript | None:
    """Return the ``container[...]`` subscript inside ``node``, if there is one."""
    for child in ast.walk(node):
        if isinstance(child, ast.Subscript) and _dotted(child.value) == container:
            return child
    return None


def _literal_codes(node: ast.AST) -> list[str]:
    """Return the string members of a ``Literal[...]`` inside ``node``."""
    for child in ast.walk(node):
        if isinstance(child, ast.Subscript) and _dotted(child.value) == "Literal":
            values = child.slice
            elements = values.elts if isinstance(values, ast.Tuple) else [values]
            return [element.value for element in elements if isinstance(element, ast.Constant)]
    return []


def _classifier_arguments(call: ast.Call) -> tuple[str, list[str]]:
    """Return the classifier field name and the declared codes of a ``Classifier(...)`` call."""
    field = ""
    if call.args:
        field = call.args[0].value if isinstance(call.args[0], ast.Constant) else ""
    codes: list[str] = []
    for keyword in call.keywords:
        if keyword.arg == "field" and isinstance(keyword.value, ast.Constant):
            field = str(keyword.value.value)
        elif keyword.arg == "codes":
            codes = _literal_codes(keyword.value)
    if not codes and len(call.args) > 1:
        codes = _literal_codes(call.args[1])
    return field, codes


def _dictionary_name(head: str) -> str:
    """Return the dictionary class name a head's axis would declare."""
    stem = head[: -len("CoreEntity")] if head.endswith("CoreEntity") else head
    return f"{stem}KindEnumEntity"


def plan_class(cls: ast.ClassDef) -> dict[str, Any] | None:
    """Return the migration plan for one class, or ``None`` when it declares no axis."""
    for statement in cls.body:
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
            continue
        container = _subscribed_container(statement.annotation, "Specialization")
        if container is None:
            continue
        call = _classifier_call(statement.annotation)
        if call is None:
            continue
        field, codes = _classifier_arguments(call)
        if not field or not codes:
            continue
        union = container.slice
        alternatives = [element for element in getattr(union, "elts", [union])]
        return {
            "head": cls.name,
            "line": statement.lineno,
            "field_name": statement.target.id,
            "classifier_field": field,
            "codes": codes,
            "dictionary": _dictionary_name(cls.name),
            "alternatives": [_dotted(element).split(".")[-1] for element in alternatives],
        }
    return None


def _constructions(tree: ast.AST, classifier_fields: set[str]) -> int:
    """Count the calls that pass a classifier field as a keyword."""
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and any(
            keyword.arg in classifier_fields for keyword in node.keywords
        ):
            count += 1
    return count


def plan_file(path: Path) -> dict[str, Any]:
    """Return the migration plan of one file."""
    tree = ast.parse(path.read_text())
    axes = [axis for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) if (axis := plan_class(cls))]
    classifier_fields = {str(axis["classifier_field"]) for axis in axes}
    return {
        "file": str(path),
        "axes": axes,
        "constructions_to_review": _constructions(tree, classifier_fields),
    }


def main(argv: list[str]) -> int:
    """Print the plan for every file named on the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", nargs="+", type=Path, metavar="FILE")
    parser.add_argument("--write", nargs="+", type=Path, metavar="FILE")
    arguments = parser.parse_args(argv)
    if arguments.write:
        print("--write is not implemented yet: the migration lands with T036-T038.", file=sys.stderr)
        return 2
    if not arguments.plan:
        parser.error("name at least one file with --plan or --write")
    plans = [plan_file(path) for path in arguments.plan]
    print(json.dumps({"files": plans, "totals": {"axes": sum(len(p["axes"]) for p in plans)}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

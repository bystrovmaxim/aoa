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
    python migrate_specializations.py --write FILE...

`--plan` prints one JSON object per axis and changes nothing. `--write` performs the
four edits: the head's container names the dictionary, the head loses its classifier
field and its `Classifier` marker, each extension's marker names a value, and the
dictionary class is inserted before the head. Constructions that pass the classifier
field as a keyword are counted and left alone: removing the field is a human's call.
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


def _value_name(code: str) -> str:
    """Return the class-body name a code is declared under."""
    cleaned = "".join(character if character.isalnum() else "_" for character in code)
    return cleaned.upper() if cleaned[:1].isdigit() is False else f"VALUE_{cleaned.upper()}"


def _span(text: str, node: ast.AST) -> tuple[int, int]:
    """Return the absolute (start, end) offsets of ``node`` in ``text``."""
    lines = text.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[: node.end_lineno - 1]) + node.end_col_offset
    return start, end


def _dictionary_source(axis: dict[str, Any], domain: str, *, exclude: bool, indent: str = "") -> str:
    """Return the dictionary class the axis migrates to, decorated like its head."""
    lines = [
        *( [f"{indent}@exclude_graph_model"] if exclude else [] ),
        f'{indent}@entity(description="Kind of {axis["head"]}", domain={domain})',
        f'{indent}class {axis["dictionary"]}(BaseEnumEntity):',
        f'{indent}    """Declare the codes the axis borrows."""',
        "",
    ]
    for code in axis["codes"]:
        name = _value_name(code)
        lines.append(
            f'{indent}    {name} = {axis["dictionary"]}('
            f'code="{code}", display_name="{name.replace("_", " ").title()}")  # noqa: F821'
        )
    return "\n".join(lines)


def _annotated_parts(annotation: ast.AST) -> tuple[ast.AST, list[ast.AST]] | None:
    """Split ``Annotated[X, ...]`` into its type and its metadata nodes."""
    if isinstance(annotation, ast.Subscript) and _dotted(annotation.value) == "Annotated":
        elements = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else []
        if elements:
            return elements[0], list(elements[1:])
    return None


def transform(text: str, axes: list[dict[str, Any]] | None = None) -> tuple[str, int]:
    """Return the migrated text and the number of axes it declares."""
    tree = ast.parse(text)
    planned = axes if axes is not None else _plan_tree(text, tree)["axes"]
    if not planned:
        return text, 0
    plan = {"axes": planned}

    edits: list[tuple[int, int, str]] = []
    domain = _domain_of(tree)
    inserted: set[str] = set()

    for axis in plan["axes"]:
        head = next(
            (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == axis["head"]),
            None,
        )
        if head is None:
            # The head lives in another cell of this notebook; this cell only carries the
            # extensions and constructions, which the marker and constructor edits handle.
            edits.extend(_rewrite_markers(text, tree, axis))
            edits.extend(_drop_constructor_arguments(text, tree, axis))
            edits.extend(_rewrite_container_constructions(text, tree, axis))
            continue
        field_name = str(axis["field_name"])
        statement = next(
            node
            for node in head.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == field_name
        )
        parts = _annotated_parts(statement.annotation)
        if parts is None:
            continue
        container, metadata = parts
        assert isinstance(container, ast.Subscript)
        union = ast.get_source_segment(text, container.slice)
        kept = [ast.get_source_segment(text, item) for item in metadata if not isinstance(item, ast.Call) or _dotted(item.func) != "Classifier"]
        arguments = f"Specialization[{union}, {axis['dictionary']}]"
        if kept and statement.annotation.end_lineno != statement.annotation.lineno:
            inner = " " * (statement.col_offset + 4)
            closing = " " * statement.col_offset
            replacement = "Annotated[\n" + f"{inner}{arguments},\n"
            replacement += "".join(f"{inner}{item},\n" for item in kept) + f"{closing}]"
        else:
            replacement = f"Annotated[{arguments}, {', '.join(kept)}]" if kept else arguments
        start, end = _span(text, statement.annotation)
        edits.append((start, end, replacement))

        classifier_field = str(axis["classifier_field"])
        for node in head.body:
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == classifier_field
            ):
                field_start, _ = _span(text, node)
                field_end = sum(len(line) for line in text.splitlines(keepends=True)[: node.end_lineno])
                edits.append((field_start - len(text.splitlines(keepends=True)[node.lineno - 1][: node.col_offset]), field_end, ""))

        anchor = head.decorator_list[0] if head.decorator_list else head
        anchor_start = _span(text, anchor)[0] - anchor.col_offset
        excluded = any(_dotted(decorator) == "exclude_graph_model" for decorator in head.decorator_list)
        if str(axis["dictionary"]) not in inserted:
            inserted.add(str(axis["dictionary"]))
            edits.append(
                (anchor_start, anchor_start, _dictionary_source(axis, domain, exclude=excluded) + "\n\n\n")
            )

        edits.extend(_rewrite_markers(text, tree, axis))
        edits.extend(_drop_constructor_arguments(text, tree, axis))
        edits.extend(_rewrite_container_constructions(text, tree, axis))

    kept_edits: list[tuple[int, int, str]] = []
    for start, end, replacement in sorted(edits, key=lambda edit: (edit[0], edit[1]), reverse=True):
        overlaps = any(
            start < kept_end and kept_start < (end if end > start else start + 1)
            for kept_start, kept_end, _ in kept_edits
            if kept_end > kept_start
        )
        if overlaps:
            continue
        kept_edits.append((start, end, replacement))
    edits = kept_edits

    for start, end, replacement in sorted(edits, key=lambda edit: (edit[0], edit[1]), reverse=True):
        text = text[:start] + replacement + text[end:]

    return _add_import(text), len(plan["axes"])


def _plan_tree(text: str, tree: ast.AST) -> dict[str, Any]:
    """Return the migration plan of one parsed module."""
    axes = [axis for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef) if (axis := plan_class(cls))]
    classifier_fields = {str(axis["classifier_field"]) for axis in axes}
    return {"axes": axes, "constructions_to_review": _constructions(tree, classifier_fields)}


def write_file(path: Path) -> dict[str, Any]:
    """Apply the migration to one file, and return what was done."""
    if path.suffix == ".ipynb":
        return _write_notebook(path)
    text = path.read_text()
    migrated, axes = transform(text)
    if migrated != text:
        path.write_text(migrated)
    return {"file": str(path), "axes": axes, "changed": migrated != text}


def _write_notebook(path: Path) -> dict[str, Any]:
    """Apply the migration to every code cell of a notebook."""
    import json

    notebook = json.loads(path.read_text())
    changed = 0
    cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
    # The plan comes from the whole notebook: a head and its extensions may live in different
    # cells, and a cell on its own would declare neither.
    collected = "\n\n".join("".join(cell.get("source", [])) for cell in cells)
    try:
        axes = _plan_tree(collected, ast.parse(collected))["axes"]
    except SyntaxError:
        axes = []
    for cell in cells:
        source = "".join(cell.get("source", []))
        migrated, _ = transform(source, axes=axes)
        if migrated != source:
            cell["source"] = migrated.splitlines(keepends=True)
            changed += 1
    if changed:
        path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
    return {"file": str(path), "axes": len(axes), "cells_changed": changed, "changed": changed > 0}


def _drop_constructor_arguments(text: str, tree: ast.AST, axis: dict[str, Any]) -> list[tuple[int, int, str]]:
    """Return the edits that stop constructions of the head from passing the removed field."""
    edits: list[tuple[int, int, str]] = []
    head_name = str(axis["head"])
    classifier_field = str(axis["classifier_field"])
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _dotted(node.func) != head_name:
            continue
        for keyword in node.keywords:
            if keyword.arg != classifier_field:
                continue
            start, end = _span(text, keyword)
            comma = text.rfind(",", 0, start)
            if comma != -1 and not text[comma + 1 : start].strip():
                start = comma
            edits.append((start, end, ""))
    return edits


def _rewrite_container_constructions(text: str, tree: ast.AST, axis: dict[str, Any]) -> list[tuple[int, int, str]]:
    """Return the edits that make a directly built container name the dictionary and its value."""
    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Subscript) or _dotted(func.value) != "Specialization":
            continue
        union = ast.get_source_segment(text, func.slice) or ""
        if not all(str(name) in union for name in axis["alternatives"]):
            continue
        start, end = _span(text, func.slice)
        edits.append((start, end, f"{union}, {axis['dictionary']}"))
        for keyword in node.keywords:
            if keyword.arg != "variant" or not isinstance(keyword.value, ast.Constant):
                continue
            value = keyword.value.value
            if not isinstance(value, str) or value not in axis["codes"]:
                continue
            value_start, value_end = _span(text, keyword.value)
            edits.append((value_start, value_end, f"{axis['dictionary']}.{_value_name(value)}"))
    return edits


def _domain_of(tree: ast.AST) -> str:
    """Return the domain class the file's entities are declared in."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _dotted(node.func) == "entity":
            for keyword in node.keywords:
                if keyword.arg == "domain":
                    return _dotted(keyword.value)
    return ""


def _rewrite_markers(text: str, tree: ast.AST, axis: dict[str, Any]) -> list[tuple[int, int, str]]:
    """Return the edits that turn each extension's marker into the value form."""
    edits: list[tuple[int, int, str]] = []
    head_name = str(axis["head"])
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        points_at_head = any(
            f"Generalization[{head_name}]" in (ast.get_source_segment(text, statement.annotation) or "")
            for statement in node.body
            if isinstance(statement, ast.AnnAssign)
        )
        if not points_at_head:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            call = _classifier_call(statement.annotation)
            if call is None:
                continue
            field, codes = _classifier_arguments(call)
            if not field or not codes:
                continue
            if codes[0] not in axis["codes"]:
                # The head does not declare this code: the case is expressing a refusal that
                # the dictionary form cannot write, so leave it for a human.
                continue
            start, end = _span(text, call)
            edits.append(
                (
                    start,
                    end,
                    f'Classifier(field="{field}", variant={axis["dictionary"]}.{_value_name(codes[0])})',
                )
            )
    return edits


def _add_import(text: str) -> str:
    """Add ``BaseEnumEntity`` to the action-machine domain import, once."""
    if "from aoa.action_machine.domain import BaseEnumEntity" in text or "\n    BaseEnumEntity," in text:
        return text
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("from aoa.action_machine.domain import ("):
            lines.insert(index + 1, "    BaseEnumEntity,\n")
            return "".join(lines)
    for index, line in enumerate(lines):
        if line.startswith("from aoa.action_machine.domain import "):
            lines.insert(index, "from aoa.action_machine.domain import BaseEnumEntity\n")
            return "".join(lines)
    return text


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
    if not arguments.plan and not arguments.write:
        parser.error("name at least one file with --plan or --write")
    if arguments.plan:
        plans = [plan_file(path) for path in arguments.plan]
        print(json.dumps({"files": plans, "totals": {"axes": sum(len(p["axes"]) for p in plans)}}, indent=2))
    for path in arguments.write or []:
        print(json.dumps(write_file(path)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

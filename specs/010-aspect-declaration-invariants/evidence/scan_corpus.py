# specs/010-aspect-declaration-invariants/evidence/scan_corpus.py
"""
Scan the repository for aspect declarations and judge them against the contract.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The measurement behind T002 (baseline) and T036/T039 (after the migration): how
many declarations of the four decorators exist, and how many of them the rules of
this feature would refuse. It reads source, notebooks and documentation the way a
reader does — syntax trees, not regular expressions — so a signature split across
several lines is judged the same as one written on one line.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

IN: the four declaration decorators, their parameter names and order, the trailing
``ctx`` and whether ``@context_requires`` can be seen at that moment, annotations on
every parameter but ``self``, the return annotation, and whether the signature can be
called positionally.

OUT: the types those annotations resolve to — that needs the operation's own names,
which exist only when the class is assembled, so it is measured by tests and not by a
static scan.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    .venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py
    .venv/bin/python specs/010-aspect-declaration-invariants/evidence/scan_corpus.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
from collections import Counter, defaultdict

SKIP_PARTS = {".venv", ".uv-cache", ".uvcache", "node_modules", "dist", "htmlcov", "archive", "__pycache__"}

CONTRACTS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "summary_aspect": (
        ("self", "params", "state", "box", "connections"),
        ("self", "params", "state", "box", "connections", "ctx"),
    ),
    "regular_aspect": (
        ("self", "params", "state", "box", "connections"),
        ("self", "params", "state", "box", "connections", "ctx"),
    ),
    "on_error": (
        ("self", "params", "state", "box", "connections", "error"),
        ("self", "params", "state", "box", "connections", "error", "ctx"),
    ),
    "compensate": (
        ("self", "params", "state_before", "state_after", "box", "connections", "error"),
        ("self", "params", "state_before", "state_after", "box", "connections", "error", "ctx"),
    ),
}


def _skipped(path: pathlib.Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def _declaration_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, int] | None:
    """Return the decorator's name and its index in the decorator list, or ``None``."""
    for index, decorator in enumerate(node.decorator_list):
        name = ast.unparse(decorator).split("(", 1)[0]
        if name in CONTRACTS:
            return name, index
    return None


def _ctx_is_visible(node: ast.FunctionDef | ast.AsyncFunctionDef, decl_index: int) -> bool:
    """Whether ``@context_requires`` is applied before the declaration, so it can be seen."""
    for index, decorator in enumerate(node.decorator_list):
        if ast.unparse(decorator).split("(", 1)[0] == "context_requires" and index > decl_index:
            return True
    return False


def _judge(node: ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> dict[str, object]:
    plain, with_ctx = CONTRACTS[kind]
    names = tuple(argument.arg for argument in (*node.args.posonlyargs, *node.args.args))
    expected = with_ctx if _ctx_is_visible(node, _declaration_kind(node)[1]) else plain  # type: ignore[index]
    unannotated = [
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args)
        if argument.arg != "self" and argument.annotation is None
    ]
    return {
        "kind": kind,
        "names": names,
        "names_ok": names == expected,
        "unannotated": unannotated,
        "return_ok": node.returns is not None,
        "positional_ok": not (node.args.vararg or node.args.kwarg or node.args.kwonlyargs),
    }


def _faults(record: dict[str, object]) -> list[str]:
    out = []
    if not record["names_ok"]:
        out.append("names")
    if record["unannotated"]:
        out.append("annotations")
    if not record["return_ok"]:
        out.append("return")
    if not record["positional_ok"]:
        out.append("positional")
    return out


def _asserted_refusal(tree: ast.AST, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether the declaration sits inside a ``pytest.raises`` block, i.e. the refusal is the point."""
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.With, ast.AsyncWith)):
            continue
        for item in candidate.items:
            text = ast.unparse(item.context_expr)
            if "raises" not in text:
                continue
            if any(child is node for statement in candidate.body for child in ast.walk(statement)):
                return True
    return False


def _scan_source(source: str, where: str) -> list[dict[str, object]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        declaration = _declaration_kind(node)
        if declaration is None:
            continue
        record = _judge(node, declaration[0])
        record["where"] = where
        record["line"] = node.lineno
        record["faults"] = _faults(record)
        record["asserted"] = _asserted_refusal(tree, node)
        found.append(record)
    return found


def _python_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(path for path in root.rglob("*.py") if not _skipped(path))


def _notebook_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(path for path in root.rglob("*.ipynb") if not _skipped(path))


def _doc_files(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(path for path in root.rglob("*.md") if not _skipped(path))


def _scan_python(root: pathlib.Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    files = _python_files(root)
    for path in files:
        records.extend(_scan_source(path.read_text(encoding="utf-8", errors="ignore"), str(path)))
    return records, len(files)


def _scan_notebooks(root: pathlib.Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    files = _notebook_files(root)
    for path in files:
        try:
            book = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        for cell in book.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            records.extend(_scan_source(source, str(path)))
    return records, len(files)


def _scan_docs(root: pathlib.Path) -> tuple[list[dict[str, object]], int]:
    records: list[dict[str, object]] = []
    files = _doc_files(root)
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for block in re.findall(r"```python\n(.*?)```", text, re.S):
            records.extend(_scan_source(block, str(path)))
    return records, len(files)


def _report(tree_name: str, records: list[dict[str, object]], files: int, out: list[str]) -> None:
    bad = [record for record in records if record["faults"]]
    asserted = sum(1 for record in bad if record["asserted"])
    out.append(
        f"| {tree_name} | {files} | {len(records)} | {len(records) - len(bad)} | **{len(bad)}** | {asserted} | {len(bad) - asserted} |"
    )


def main() -> None:
    """Print the table of declarations, their faults and the files to migrate."""
    parser = argparse.ArgumentParser(description="Judge aspect declarations against the contract.")
    parser.add_argument("--json", action="store_true", help="print the raw records instead of the report")
    parser.add_argument("--root", default=".", help="repository root")
    arguments = parser.parse_args()
    root = pathlib.Path(arguments.root)

    trees = {
        "packages (**/*.py)": _scan_python(root / "packages"),
        "examples (**/*.py)": _scan_python(root / "examples"),
        "examples (**/*.ipynb)": _scan_notebooks(root / "examples"),
        "docs (**/*.md, ```python blocks)": _scan_docs(root / "docs"),
    }

    if arguments.json:
        print(json.dumps({name: records for name, (records, _) in trees.items()}, indent=2, default=str))
        return

    lines: list[str] = []
    lines.append("| Tree | Files | Declarations | Conforming | Non-conforming | of them asserted refusals | to migrate |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    total_declarations = 0
    total_bad = 0
    total_asserted = 0
    all_records: list[dict[str, object]] = []
    for name, (records, files) in trees.items():
        _report(name, records, files, lines)
        total_declarations += len(records)
        total_bad += sum(1 for record in records if record["faults"])
        total_asserted += sum(1 for record in records if record["faults"] and record["asserted"])
        all_records.extend(records)
    lines.append(
        f"| **total** | | **{total_declarations}** | **{total_declarations - total_bad}** | **{total_bad}** | **{total_asserted}** | **{total_bad - total_asserted}** |"
    )
    print("\n".join(lines))

    print()
    by_kind: Counter[str] = Counter(record["kind"] for record in all_records)
    bad_by_kind: Counter[str] = Counter(record["kind"] for record in all_records if record["faults"])
    print("| Declaration | Total | Non-conforming |")
    print("| --- | --- | --- |")
    for kind in CONTRACTS:
        print(f"| `@{kind}` | {by_kind[kind]} | {bad_by_kind[kind]} |")

    print()
    faults: Counter[str] = Counter()
    combos: Counter[str] = Counter()
    for record in all_records:
        faults.update(record["faults"])
        combos["+".join(record["faults"]) or "none"] += 1
    print("| Fault | Declarations |")
    print("| --- | --- |")
    for key in ("names", "annotations", "return", "positional"):
        print(f"| {key} | {faults[key]} |")
    print()
    print("Fault combinations (a declaration can carry several):")
    print()
    print("| Combination | Declarations |")
    print("| --- | --- |")
    for key, count in sorted(combos.items(), key=lambda item: -item[1]):
        print(f"| {key} | {count} |")

    print()
    notebook_files = sorted({str(record["where"]) for record in trees["examples (**/*.ipynb)"][0]})
    docs_files = sorted({str(record["where"]) for record in trees["docs (**/*.md, ```python blocks)"][0]})
    print(f"Notebooks carrying declarations: {len(notebook_files)}")
    print()
    for path in notebook_files:
        print(f"- `{path}`")
    print()
    print(f"Documentation pages carrying declarations: {len(docs_files)}")
    print()
    for path in docs_files:
        print(f"- `{path}`")

    print()
    print("Files to migrate")
    print()
    for tree_name, (records, _) in trees.items():
        bad_files = defaultdict(int)
        for record in records:
            if record["faults"] and not record["asserted"]:
                bad_files[str(record["where"])] += len(record["faults"])
        if not bad_files:
            continue
        print(f"### {tree_name} ({len(bad_files)} files)")
        print()
        for path, count in sorted(bad_files.items()):
            print(f"- `{path}` — {count} fault(s)")


if __name__ == "__main__":
    main()

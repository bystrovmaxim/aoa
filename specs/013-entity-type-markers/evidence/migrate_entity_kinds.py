# specs/013-entity-type-markers/evidence/migrate_entity_kinds.py
"""
Apply the decision table: rename the entities and move them onto their kind base class.

Reads `entity_kind_map.py`, then for every Python module under `packages/` and
`examples/`:

1. renames the classes the module declares, and the names it imports from a
   module in the table, with whole-word replacements — so annotations,
   `Inverse(...)` arguments, `model_rebuild()` calls and any string that spells
   an old class name move with it;
2. rewrites the base of each migrated class from `BaseEntity` to the kind base
   class the map chose, and adds the import for it.

The codemod refuses a same-module collision and reports what it changed. It
never renames a file: module paths stay, so imports of modules keep working.

Usage:
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py --check
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/migrate_entity_kinds.py
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
EVIDENCE = pathlib.Path(__file__).resolve().parent
MAP_FILE = EVIDENCE / "entity_kind_map.py"
SKIP = {"__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build"}
BASE_BY_KIND = {
    "core": "BaseCoreEntity",
    "assoc": "BaseAssocEntity",
    "detail": "BaseDetailEntity",
    "spec": "BaseSpecEntity",
    "enum": "BaseEnumEntity",
    "state": "BaseStateEntity",
}


def load_map() -> tuple[dict[str, dict[str, tuple[str, str]]], dict[str, dict[str, str]]]:
    """Return {module: {old: (new, base)}} and {dotted module: {old: new}} from the decision table."""
    spec = importlib.util.spec_from_file_location("entity_kind_map", MAP_FILE)
    if spec is None or spec.loader is None:
        raise SystemExit("entity_kind_map.py is not importable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    by_module: dict[str, dict[str, tuple[str, str]]] = {}
    by_dotted: dict[str, dict[str, str]] = {}
    for entry in module.ENTITY_KIND_MAP:
        base = BASE_BY_KIND[entry["kind"]]
        by_module.setdefault(entry["module"], {})[entry["old_name"]] = (entry["new_name"], base)
        dotted = dotted_name(entry["module"])
        if dotted:
            by_dotted.setdefault(dotted, {})[entry["old_name"]] = entry["new_name"]

    collisions = [
        (module, new)
        for module, entries in by_module.items()
        for new in _duplicates([new for new, _ in entries.values()])
    ]
    if collisions:
        raise SystemExit(f"the map renames two classes in one module to the same name: {collisions}")
    return by_module, by_dotted


def _duplicates(names: list[str]) -> list[str]:
    """Return the names that appear more than once, each once."""
    seen, twice = set(), []
    for name in names:
        if name in seen and name not in twice:
            twice.append(name)
        seen.add(name)
    return twice


def dotted_name(path: str) -> str | None:
    """Return the importable dotted name of a module under packages/<pkg>/src, or None."""
    parts = pathlib.PurePosixPath(path).parts
    if len(parts) < 5 or parts[0] != "packages" or parts[2] != "src" or not path.endswith(".py"):
        return None
    return ".".join(parts[3:])[: -len(".py")]


def imported_renames(tree: ast.Module, by_dotted: dict[str, dict[str, str]]) -> dict[str, str]:
    """Return the names this module imports from a mapped module under an old name."""
    renames: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in by_dotted:
            for alias in node.names:
                if alias.name in by_dotted[node.module]:
                    renames[alias.asname or alias.name] = by_dotted[node.module][alias.name]
    return renames


def replace_words(text: str, renames: dict[str, str]) -> str:
    """Replace whole identifiers, longest first, so a prefix never eats a longer name."""
    for old in sorted(renames, key=len, reverse=True):
        text = re.sub(rf"(?<![\w.]){re.escape(old)}(?![\w])", renames[old], text)
    return text


def header_span(lines: list[str], first_line: int) -> tuple[int, int]:
    """Return the first and last line index of a class header, counting parentheses."""
    depth = 0
    opened = False
    for index in range(first_line, len(lines)):
        depth += lines[index].count("(") - lines[index].count(")")
        opened = opened or "(" in lines[index]
        if opened and depth <= 0:
            return first_line, index
    return first_line, first_line


def migrate_file(
    path: pathlib.Path,
    entries: dict[str, tuple[str, str]],
    imported: dict[str, str],
    write: bool,
) -> tuple[int, int]:
    """Rename one module's entities, move them onto their kind base class, and return (renames, bases)."""
    text = path.read_text(encoding="utf-8")
    renames = {old: new for old, (new, _) in entries.items()} | imported
    if not renames:
        return 0, 0
    new_text = replace_words(text, renames)

    tree = ast.parse(new_text)
    lines = new_text.splitlines(keepends=True)
    bases_needed: set[str] = set()
    rewritten = 0
    for new_name, base in (value for value in entries.values()):
        for node in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == new_name):
            if "BaseEntity" not in {ast.unparse(b).split("[")[0].strip() for b in node.bases}:
                continue
            start, end = header_span(lines, node.lineno - 1)
            header = "".join(lines[start : end + 1])
            lines[start : end + 1] = [re.sub(r"(?<![\w.])BaseEntity(?![\w])", base, header)]
            bases_needed.add(base)
            rewritten += 1
    new_text = "".join(lines)

    if bases_needed:
        import_line = "from aoa.action_machine.domain import " + ", ".join(sorted(bases_needed)) + "\n"
        if import_line not in new_text:
            top = new_text.splitlines(keepends=True)
            insert_at = 0
            for index, line in enumerate(top[:80]):
                if line.startswith(("import ", "from ")):
                    insert_at = index + 1
            top.insert(insert_at, import_line)
            new_text = "".join(top)

    if write and new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return len(renames), rewritten


def main() -> int:
    """Walk the tree, apply the map, and report what changed."""
    parser = argparse.ArgumentParser(description="Rename entities and move them onto their kind base class.")
    parser.add_argument("--check", action="store_true", help="report what would change without writing")
    parser.add_argument("--root", default=None, help="limit the run to one subtree")
    args = parser.parse_args()

    by_module, by_dotted = load_map()
    roots = [pathlib.Path(args.root).resolve()] if args.root else [(REPO_ROOT / "packages"), (REPO_ROOT / "examples")]
    totals = [0, 0]
    touched = 0
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if any(part in SKIP for part in path.parts):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"))
            entries = by_module.get(rel, {})
            imported = imported_renames(tree, by_dotted)
            if not entries and not imported:
                continue
            renames, bases = migrate_file(path, entries, imported, write=not args.check)
            if renames or bases:
                touched += 1
                totals[0] += renames
                totals[1] += bases
                if args.check:
                    print(f"{rel}: {renames} name(s), {bases} base(s)")
    print(f"{'would change' if args.check else 'changed'} {touched} file(s); {totals[0]} name reference(s), {totals[1]} base class(es)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

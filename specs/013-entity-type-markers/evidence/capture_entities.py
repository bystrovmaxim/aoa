# specs/013-entity-type-markers/evidence/capture_entities.py
"""
Capture, per entity class, the declaration surface the migration must not change.

Reads the tree with `ast` only: the model field names, the relation fields with
their relation kind, the lifecycle fields, the `@entity` description and the
domain. The same script writes the "before" and the "after" baseline, so the two
are comparable key for key.

Usage:
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/capture_entities.py --out before.json
    UV_CACHE_DIR=./.uvcache uv run python specs/013-entity-type-markers/evidence/capture_entities.py --out after.json
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SKIP = {"__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build"}
SERVICE = {"id", "created_at", "updated_at"}
RELATIONS = ("Association", "Composite", "Aggregate")


def display_path(path: pathlib.Path) -> str:
    """Return the path relative to the repository root."""
    return str(path.resolve().relative_to(REPO_ROOT))


def relation_kind(annotation: str) -> str | None:
    """Return the relation kind an annotation names, or None when it is not a relation."""
    for kind in RELATIONS:
        if f"{kind}One[" in annotation or f"{kind}Many[" in annotation:
            return kind.lower()
    return None


def capture_class(path: str, node: ast.ClassDef) -> dict[str, object]:
    """Return the declaration surface of one class."""
    scalar, relations, lifecycles = [], {}, []
    for statement in node.body:
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
            continue
        name, annotation = statement.target.id, ast.unparse(statement.annotation)
        kind = relation_kind(annotation)
        if kind is not None:
            relations[name] = kind
        elif "Lifecycle" in annotation:
            lifecycles.append(name)
        elif name not in SERVICE:
            scalar.append(name)
    description, domain = "", ""
    for decorator in node.decorator_list:
        text = ast.unparse(decorator)
        match = re.search(r'description="([^"]*)"', text)
        if match:
            description = match.group(1)
        match = re.search(r"domain=(\w+)", text)
        if match:
            domain = match.group(1)
    return {
        "module": path,
        "scalars": sorted(scalar),
        "relations": dict(sorted(relations.items())),
        "lifecycles": sorted(lifecycles),
        "description": description,
        "domain": domain,
    }


def capture() -> dict[str, dict[str, object]]:
    """Walk the tree and return every class on the entity base, keyed by module and name."""
    entities: dict[str, dict[str, object]] = {}
    for root in ("packages", "examples"):
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            if any(part in SKIP for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = {ast.unparse(base).split("[")[0].strip() for base in node.bases}
                if "BaseEntity" not in bases and not any(b.startswith("Base") and b.endswith("Entity") for b in bases):
                    continue
                if node.name.startswith("Base"):
                    continue
                entities[f"{display_path(path)}::{node.name}"] = capture_class(display_path(path), node)
    return entities


def main() -> int:
    """Write the baseline to ``--out``."""
    parser = argparse.ArgumentParser(description="Capture the entity declaration surface.")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    data = capture()
    args.out.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(data)} classes captured -> {display_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

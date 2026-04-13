#!/usr/bin/env python3
"""Enforce test-directory ↔ action_machine import boundaries (plan 008 / PR-T5).

Walks ``tests/<layer>/**/*.py`` and flags ``import`` / ``from`` of ``action_machine.*``
whose first subpackage after ``action_machine`` is forbidden for that layer.

Exemptions: ``scripts/test_layer_import_allowlist.toml`` — ``[[allow_prefix]]`` rows
with ``path`` (repo-relative) and ``prefix`` (e.g. ``action_machine.runtime``).
"""

from __future__ import annotations

import ast
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS = REPO_ROOT / "tests"
ALLOWLIST_PATH = REPO_ROOT / "scripts" / "test_layer_import_allowlist.toml"

# Layer name (first path segment under tests/) → forbidden first subpackages under action_machine.*
LAYER_FORBIDDEN: dict[str, frozenset[str]] = {
    "model": frozenset({"graph", "runtime", "integrations", "testing"}),
    "resources": frozenset({"graph", "runtime", "intents"}),
    "intents": frozenset({"graph", "runtime", "adapters", "integrations"}),
    "graph": frozenset({"runtime", "adapters", "integrations"}),
    "runtime": frozenset({"integrations"}),
    "dependencies": frozenset({"graph", "runtime", "integrations"}),
    # Domain package sits on model-ish layer; keep tests from reaching upper tiers.
    "domain": frozenset({"graph", "runtime", "integrations", "testing", "adapters"}),
}

# Top-level dirs under tests/ that are not subject to layered rules.
SKIP_TOP_LEVEL = frozenset(
    {
        "scenarios",
        "smoke",
        "bench",
        "architecture",
        "adapters",
        "integrations",
        "testing",
        "__pycache__",
    }
)


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    module: str
    forbidden: str

    def format(self) -> str:
        rel = self.path.relative_to(REPO_ROOT)
        return f"{rel}:{self.lineno}: forbidden {self.forbidden!r} import {self.module!r}"


def _layer_for_file(path: Path) -> str | None:
    try:
        rel = path.relative_to(TESTS)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    top = parts[0]
    if top in SKIP_TOP_LEVEL:
        return None
    return top if top in LAYER_FORBIDDEN else None


def _action_machine_modules(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, full_module_string) for action_machine imports."""
    found: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == "action_machine" or name.startswith("action_machine."):
                    found.append((node.lineno, name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if mod == "action_machine" or mod.startswith("action_machine."):
                found.append((node.lineno, mod))
    return found


def _first_subpackage(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2 or parts[0] != "action_machine":
        return None
    return parts[1]


def _load_allow_prefixes() -> list[tuple[str, str]]:
    if not ALLOWLIST_PATH.is_file():
        return []
    data = tomllib.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    rows = data.get("allow_prefix", [])
    out: list[tuple[str, str]] = []
    for row in rows:
        path = row["path"].replace("\\", "/")
        prefix = row["prefix"]
        if not prefix.startswith("action_machine"):
            raise ValueError(f"allow_prefix.prefix must start with action_machine: {prefix!r}")
        out.append((path, prefix))
    return out


def _allowed_by_prefix(rel_posix: str, module: str, allow: list[tuple[str, str]]) -> bool:
    for apath, prefix in allow:
        if rel_posix != apath.replace("\\", "/"):
            continue
        if module == prefix or module.startswith(prefix + "."):
            return True
    return False


def collect_violations() -> list[Violation]:
    allow = _load_allow_prefixes()
    violations: list[Violation] = []

    for path in sorted(TESTS.rglob("*.py")):
        if path.name == "conftest.py" and path.parent == TESTS:
            continue
        layer = _layer_for_file(path)
        if layer is None:
            continue
        forbidden = LAYER_FORBIDDEN[layer]
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as e:
            raise SystemExit(f"Cannot parse {path}: {e}") from e

        rel_posix = path.relative_to(REPO_ROOT).as_posix()

        for lineno, module in _action_machine_modules(tree):
            sub = _first_subpackage(module)
            if sub is None:
                continue
            if sub not in forbidden:
                continue
            if _allowed_by_prefix(rel_posix, module, allow):
                continue
            violations.append(Violation(path, lineno, module, sub))

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("Test layer import violations:", file=sys.stderr)
        for v in violations:
            print(v.format(), file=sys.stderr)
        print(
            f"\nAllow exemptions in {ALLOWLIST_PATH.relative_to(REPO_ROOT)} "
            "via [[allow_prefix]] path + prefix.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

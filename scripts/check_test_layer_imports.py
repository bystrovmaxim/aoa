#!/usr/bin/env python3
"""Enforce internal layer imports for ``tests/action_machine/<layer>/``.

Walks ``tests/action_machine/<layer>/**/*.py`` and flags ``import`` / ``from`` of ``aoa.action_machine.*``
whose first subpackage after ``action_machine`` is forbidden for that layer.

This is **orthogonal** to ``check_package_boundaries.py`` (cross-package ``aoa.graph`` / ``aoa.maxitor`` rules).

Exemptions: ``scripts/test_layer_import_allowlist.toml`` - ``[[allow_prefix]]`` rows
with ``path`` (repo-relative) and ``prefix`` (e.g. ``aoa.action_machine.runtime``).
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

# Second path segment under ``tests/action_machine/`` maps to forbidden first subpackages under aoa.action_machine.*
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

# Second-level dirs under ``tests/action_machine/`` not subject to layered rules.
SKIP_SECOND_LEVEL = frozenset(
    {
        "scenarios",
        "smoke",
        "bench",
        "adapters",
        "graph_host",
        "application",
        "introspection",
        "system_core",
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
    if len(parts) < 2 or parts[0] != "action_machine":
        return None
    second = parts[1]
    if second in SKIP_SECOND_LEVEL:
        return None
    return second if second in LAYER_FORBIDDEN else None


def _action_machine_modules(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, full_module_string) for ``aoa.action_machine`` imports."""
    found: list[tuple[int, str]] = []
    prefix = "aoa.action_machine"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name == prefix or name.startswith(prefix + "."):
                    found.append((node.lineno, name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module
            if mod == prefix or mod.startswith(prefix + "."):
                found.append((node.lineno, mod))
    return found


def _first_subpackage(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 3 or parts[0] != "aoa" or parts[1] != "action_machine":
        return None
    return parts[2]


def _load_allow_prefixes() -> list[tuple[str, str]]:
    if not ALLOWLIST_PATH.is_file():
        return []
    data = tomllib.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    rows = data.get("allow_prefix", [])
    out: list[tuple[str, str]] = []
    for row in rows:
        path = row["path"].replace("\\", "/")
        prefix = row["prefix"]
        if not prefix.startswith("aoa.action_machine"):
            raise ValueError(f"allow_prefix.prefix must start with aoa.action_machine: {prefix!r}")
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
        if path.name == "conftest.py" and path.parent in (TESTS, TESTS / "action_machine"):
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

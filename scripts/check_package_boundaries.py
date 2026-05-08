#!/usr/bin/env python3
# scripts/check_package_boundaries.py
"""
Enforce production import boundaries between top-level packages (graph, action_machine, maxitor, examples).

Reads rules from ``scripts/package_boundaries.toml`` and scans Python files under each package's
``current_roots``. ``--tests`` is reserved for later phases (PR-07); it is not implemented yet.
"""

from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "scripts" / "package_boundaries.toml"

CANONICAL = ("graph", "action_machine", "maxitor", "examples")


@dataclass(frozen=True)
class Violation:
    path: Path
    lineno: int
    owner: str
    target: str
    module: str

    def format(self) -> str:
        rel = self.path.relative_to(REPO_ROOT)
        return (
            f"{rel.as_posix()}:{self.lineno}: package {self.owner!r} must not import "
            f"package {self.target!r} via {self.module!r}"
        )


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"Missing config: {CONFIG_PATH}")
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _packages_table(cfg: dict) -> dict:
    try:
        return cfg["packages"]
    except KeyError as exc:
        raise SystemExit("Config section [packages] is required") from exc


def _package_roots(cfg: dict) -> dict[str, list[str]]:
    packages = _packages_table(cfg)
    out: dict[str, list[str]] = {}
    for name in CANONICAL:
        if name not in packages:
            raise SystemExit(f"Config section [packages.{name}] is required")
        roots = packages[name].get("current_roots") or []
        if not roots:
            raise SystemExit(f"[packages.{name}].current_roots must be non-empty")
        out[name] = [str(r).rstrip("/") for r in roots]
    return out


def _may_import(cfg: dict, pkg: str) -> frozenset[str]:
    packages = _packages_table(cfg)
    allowed = packages[pkg].get("may_import") or []
    return frozenset(str(x) for x in allowed)


def _owner_for_file(rel_posix: str, roots: dict[str, list[str]]) -> str | None:
    best: str | None = None
    best_len = -1
    for pkg, rlist in roots.items():
        for root in rlist:
            if rel_posix == root or rel_posix.startswith(root + "/"):
                ln = len(root)
                if ln > best_len:
                    best_len = ln
                    best = pkg
    return best


def _target_from_module(module: str) -> str | None:
    parts = module.split(".")
    if not parts:
        return None
    if parts[0] == "aoa" and len(parts) >= 2 and parts[1] in CANONICAL:
        return parts[1]
    if parts[0] in CANONICAL:
        return parts[0]
    return None


def _load_allows(cfg: dict) -> list[tuple[str, frozenset[str]]]:
    rows = cfg.get("allow", [])
    if not isinstance(rows, list):
        raise SystemExit("'allow' must be a list of tables")
    out: list[tuple[str, frozenset[str]]] = []
    for row in rows:
        path = str(row["path"]).replace("\\", "/")
        imports_raw = row.get("imports") or []
        if not row.get("reason"):
            raise SystemExit(f"allow entry for {path!r} missing 'reason'")
        if not row.get("expires"):
            raise SystemExit(f"allow entry for {path!r} missing 'expires'")
        ims = frozenset(str(x) for x in imports_raw)
        out.append((path, ims))
    return out


def _allowed_by_allowlist(
    rel_posix: str, target: str, allows: list[tuple[str, frozenset[str]]]
) -> bool:
    for apath, ims in allows:
        if rel_posix != apath.replace("\\", "/"):
            continue
        if target in ims:
            return True
    return False


def _iter_import_violations(path: Path, owner: str, may: frozenset[str]) -> list[Violation]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        raise SystemExit(f"{path}: syntax error: {exc}") from exc

    bad: list[Violation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name
                tgt = _target_from_module(mod)
                if tgt is None or tgt == owner:
                    continue
                if tgt in may:
                    continue
                bad.append(Violation(path, node.lineno, owner, tgt, mod))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            mod = node.module
            tgt = _target_from_module(mod)
            if tgt is None or tgt == owner:
                continue
            if tgt in may:
                continue
            bad.append(Violation(path, node.lineno, owner, tgt, mod))
    return bad


def _collect_py_files(roots: dict[str, list[str]]) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []
    for rlist in roots.values():
        for root in rlist:
            base = REPO_ROOT / root
            if not base.is_dir():
                raise SystemExit(f"Root is not a directory: {base}")
            for p in sorted(base.rglob("*.py")):
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    files.append(p)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tests",
        action="store_true",
        help="Reserved; test-directory boundaries are planned for PR-07.",
    )
    args = parser.parse_args()
    if args.tests:
        print("check_package_boundaries: --tests is not implemented yet (see PR-07).", file=sys.stderr)
        return 2

    cfg = _load_config()
    roots = _package_roots(cfg)
    may_by_pkg = {p: _may_import(cfg, p) for p in CANONICAL}
    allows = _load_allows(cfg)

    violations: list[Violation] = []
    for path in _collect_py_files(roots):
        rel = path.relative_to(REPO_ROOT).as_posix()
        owner = _owner_for_file(rel, roots)
        if owner is None:
            continue
        for v in _iter_import_violations(path, owner, may_by_pkg[owner]):
            if _allowed_by_allowlist(rel, v.target, allows):
                continue
            violations.append(v)

    if violations:
        for v in sorted(violations, key=lambda x: (str(x.path), x.lineno)):
            print(v.format(), file=sys.stderr)
        print(f"\n{len(violations)} package boundary violation(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

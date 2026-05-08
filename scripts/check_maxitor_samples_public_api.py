#!/usr/bin/env python3
# scripts/check_maxitor_samples_public_api.py
"""
Enforce façade-only imports of ``action_machine`` under ``src/maxitor/samples``.

Only ``ImportFrom`` / ``Import`` targets listed in ``ALLOWED_ACTION_MACHINE_MODULES`` are
accepted. Extend that set when new public surfaces are intentionally exposed to samples.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ALLOWED_ACTION_MACHINE_MODULES: frozenset[str] = frozenset(
    {
        "action_machine",
        # Facade packages documented via package ``__init__`` / ``__all__``
        "action_machine.auth",
        "action_machine.context",
        "action_machine.domain",
        "action_machine.integrations.fastapi",
        "action_machine.integrations.mcp",
        "action_machine.logging",
        "action_machine.model",
        "action_machine.plugin",
        "action_machine.resources",
        "action_machine.resources.external_service",
        "action_machine.resources.sql",
        "action_machine.testing",
        "action_machine.intents.aspects",
        "action_machine.intents.check_roles",
        "action_machine.intents.checkers",
        "action_machine.intents.compensate",
        "action_machine.intents.connection",
        "action_machine.intents.context_requires",
        "action_machine.intents.depends",
        "action_machine.intents.entity",
        "action_machine.intents.meta",
        "action_machine.intents.on",
        "action_machine.intents.on_error",
    },
)


def _git_ls_python_samples(repo_root: Path) -> list[Path]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "-z", "--", "src/maxitor/samples"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        decoded = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"git ls-files failed: {decoded}")

    paths: list[Path] = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        decoded_path = raw.decode("utf-8")
        path = repo_root / decoded_path
        if path.suffix == ".py":
            paths.append(path)
    return sorted(paths)


def _check_import_from(
    *,
    repo_root: Path,
    abs_path: Path,
    node: ast.ImportFrom,
    violations: list[str],
) -> None:
    if node.level != 0:
        return

    module = node.module
    dotted = module if module else "action_machine"

    if not dotted.startswith("action_machine"):
        return

    if dotted not in ALLOWED_ACTION_MACHINE_MODULES:
        lineno = getattr(node, "lineno", 0)
        rel = abs_path.relative_to(repo_root)
        violations.append(f"{rel}:{lineno}: disallowed façade import 'from {dotted} import …'")


def _check_import(repo_root: Path, abs_path: Path, node: ast.Import, violations: list[str]) -> None:
    for alias in node.names:
        name = alias.name
        if not name.startswith("action_machine"):
            continue
        if name == "action_machine":
            if "action_machine" not in ALLOWED_ACTION_MACHINE_MODULES:
                lineno = getattr(node, "lineno", 0)
                rel = abs_path.relative_to(repo_root)
                violations.append(f"{rel}:{lineno}: disallowed bare 'import action_machine'")
            continue
        mod = name
        if mod not in ALLOWED_ACTION_MACHINE_MODULES:
            lineno = getattr(node, "lineno", 0)
            rel = abs_path.relative_to(repo_root)
            violations.append(
                f"{rel}:{lineno}: disallowed ''import {name}'' "
                "(import only through façade subpackages, e.g. model / domain)."
            )


def _scan_file(repo_root: Path, abs_path: Path) -> list[str]:
    violations: list[str] = []
    source = abs_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(abs_path))
    except SyntaxError as exc:
        rel = abs_path.relative_to(repo_root)
        return [f"{rel}:{exc.lineno or 0}: syntax error: {exc.msg}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            _check_import_from(repo_root=repo_root, abs_path=abs_path, node=node, violations=violations)
        elif isinstance(node, ast.Import):
            _check_import(repo_root, abs_path, node, violations)
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument(
        "--samples-root",
        type=Path,
        default=None,
        help="Override root (default: git-tracked paths under src/maxitor/samples)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if args.samples_root is not None:
        samples_root = args.samples_root.resolve()
        py_files = sorted(p for p in samples_root.rglob("*.py") if p.is_file())
        if not py_files:
            print("No Python files found under samples root.", file=sys.stderr)
            return 1
    else:
        py_files = _git_ls_python_samples(repo_root)

    all_violations: list[str] = []
    for path in py_files:
        all_violations.extend(_scan_file(repo_root, path))

    if all_violations:
        sys.stderr.write(
            "maxitor.samples must import action_machine only through façade modules.\n"
            "Violation(s):\n  "
            + "\n  ".join(all_violations)
            + "\nExtend scripts/check_maxitor_samples_public_api.py "
            "ALLOWED_ACTION_MACHINE_MODULES if a new public surface is intentional.\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

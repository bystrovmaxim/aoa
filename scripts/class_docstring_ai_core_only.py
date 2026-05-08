#!/usr/bin/env python3
"""
For each class docstring that contains both leading prose and an AI-CORE-BEGIN … AI-CORE-END
block, replace the docstring with **only** that block (trimmed, normalized indentation).

Skips classes whose docstring is already AI-CORE-only (no leading prose).

Usage:
  uv run python scripts/class_docstring_ai_core_only.py --dry-run src
  uv run python scripts/class_docstring_ai_core_only.py src
"""

from __future__ import annotations

import argparse
import ast
import sys
import textwrap
from pathlib import Path


def format_docstring_literal(value: str) -> str:
    inner = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return '"""' + inner + '"""'


def _line_start_offsets(source: str) -> list[int]:
    offsets: list[int] = [0]
    pos = 0
    for line in source.splitlines(keepends=True):
        pos += len(line)
        offsets.append(pos)
    return offsets


def _span_for_constant(source: str, node: ast.Constant) -> tuple[int, int] | None:
    if node.lineno is None or node.col_offset is None:
        return None
    if node.end_lineno is None or node.end_col_offset is None:
        return None
    starts = _line_start_offsets(source)
    if node.lineno > len(starts) or node.end_lineno > len(starts):
        return None
    start = starts[node.lineno - 1] + node.col_offset
    end = starts[node.end_lineno - 1] + node.end_col_offset
    return start, end


def get_class_docstring_constant(node: ast.ClassDef) -> ast.Constant | None:
    if not node.body:
        return None
    first = node.body[0]
    if not isinstance(first, ast.Expr):
        return None
    v = first.value
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return v
    return None


def collect_class_docstrings(tree: ast.AST) -> list[tuple[ast.ClassDef, ast.Constant]]:
    out: list[tuple[ast.ClassDef, ast.Constant]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            c = get_class_docstring_constant(node)
            if c is not None:
                out.append((node, c))
    return out


def ai_core_only_inner(old: str) -> str | None:
    """Return new docstring inner text, or None if no change."""
    if "AI-CORE-BEGIN" not in old or "AI-CORE-END" not in old:
        return None
    start = old.index("AI-CORE-BEGIN")
    end = old.index("AI-CORE-END", start) + len("AI-CORE-END")
    block = old[start:end].strip()
    if not block:
        return None
    # Already only the block (allow surrounding whitespace)
    if old.strip() == block:
        return None
    # One leading newline + indented block + trailing newline reads well in editors
    body = textwrap.dedent(block)
    inner = "\n" + body + "\n"
    return inner


def process_source(source: str) -> tuple[str, int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0

    repls: list[tuple[int, int, str]] = []
    for _cls, const in collect_class_docstrings(tree):
        new_inner = ai_core_only_inner(const.value)
        if new_inner is None:
            continue
        span = _span_for_constant(source, const)
        if span is None:
            continue
        a, b = span
        repls.append((a, b, format_docstring_literal(new_inner)))

    repls.sort(key=lambda t: t[0], reverse=True)
    out = source
    for a, b, text in repls:
        out = out[:a] + text + out[b:]
    return out, len(repls)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roots = [Path(p) for p in args.paths]
    py_files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            py_files.append(root)
        elif root.is_dir():
            py_files.extend(sorted(root.rglob("*.py")))

    n_files = 0
    n_repl = 0
    for path in py_files:
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"skip {path}: {e}", file=sys.stderr)
            continue
        new_src, n = process_source(src)
        if new_src == src:
            continue
        n_files += 1
        n_repl += n
        rel = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        print(f"{rel}: {n} class docstring(s)")
        if not args.dry_run:
            path.write_text(new_src, encoding="utf-8")

    print(f"{'dry-run: ' if args.dry_run else ''}{n_files} file(s), {n_repl} class(es)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

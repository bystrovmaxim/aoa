#!/usr/bin/env python3
"""
Remove only docstring blocks whose **title line** (between two U+2550 separator lines)
matches one of the strings passed with ``--remove-title`` (exact match after ``strip()``).

Does nothing unless you pass at least one ``--remove-title`` and explicit paths.

Example::

    uv run python scripts/strip_docstring_separator_blocks.py \\
      --remove-title EXCEPTIONS \\
      --remove-title INVARIANTS \\
      --remove-title \"ERRORS / LIMITATIONS\" \\
      --dry-run \\
      src/graph/exceptions.py
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# U+2550 BOX DRAWINGS DOUBLE HORIZONTAL
SEP_CHAR = "═"


def is_separator_line(line: str) -> bool:
    s = line.strip()
    return len(s) >= 10 and all(c == SEP_CHAR for c in s)


def format_docstring_literal(value: str) -> str:
    """Return Python source for a string literal (prefer triple double quotes)."""
    if '"""' in value and "'''" not in value:
        inner = value.replace("\\", "\\\\").replace("'''", "\\'\\'\\'")
        return "'''" + inner + "'''"
    inner = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return '"""' + inner + '"""'


def strip_matching_blocks(text: str, remove_titles: frozenset[str]) -> str:
    """Remove sep/title/sep/body blocks only when title.strip() is in remove_titles."""
    lines = text.splitlines(keepends=True)
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(lines):
            if not (
                i + 2 < len(lines)
                and is_separator_line(lines[i])
                and is_separator_line(lines[i + 2])
            ):
                i += 1
                continue
            title_line = lines[i + 1]
            if not title_line.strip():
                i += 1
                continue
            if title_line.strip() not in remove_titles:
                i += 1
                continue
            end = i + 3
            while end < len(lines) and not is_separator_line(lines[end]):
                end += 1
            del lines[i:end]
            changed = True
            break
    out = "".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.rstrip() + ("\n" if text.endswith("\n") and out else "")


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


def _collect_docstring_constants(tree: ast.AST) -> list[ast.Constant]:
    out: list[ast.Constant] = []

    def first_expr_doc(n: ast.AST) -> ast.Constant | None:
        if not isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        body = getattr(n, "body", None)
        if not body:
            return None
        first = body[0]
        if not isinstance(first, ast.Expr):
            return None
        v = first.value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            return v
        return None

    m = first_expr_doc(tree)
    if m is not None:
        out.append(m)
    for n in ast.walk(tree):
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            c = first_expr_doc(n)
            if c is not None:
                out.append(c)
    return out


def process_source(source: str, remove_titles: frozenset[str]) -> tuple[str, int]:
    """Return new source and number of docstrings changed."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0

    constants = [c for c in _collect_docstring_constants(tree) if SEP_CHAR in c.value]
    replacements: list[tuple[int, int, str]] = []
    for const in constants:
        old_inner = const.value
        new_inner = strip_matching_blocks(old_inner, remove_titles)
        if new_inner == old_inner:
            continue
        span = _span_for_constant(source, const)
        if span is None:
            continue
        start, end = span
        new_text = format_docstring_literal(new_inner)
        replacements.append((start, end, new_text))

    replacements.sort(key=lambda t: t[0], reverse=True)
    out = source
    for start, end, new_text in replacements:
        out = out[:start] + new_text + out[end:]
    return out, len(replacements)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strip only ═-framed docstring sections with given title lines.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Python files or directories to process",
    )
    parser.add_argument(
        "--remove-title",
        action="append",
        dest="remove_titles",
        default=[],
        metavar="TITLE",
        help="Exact title line (after strip) for a block to remove; repeat flag",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change, do not write files",
    )
    args = parser.parse_args()

    if not args.remove_titles:
        print("error: pass at least one --remove-title", file=sys.stderr)
        return 2

    titles = frozenset(t.strip() for t in args.remove_titles if t.strip())
    if not titles:
        print("error: --remove-title values are empty", file=sys.stderr)
        return 2

    roots = [Path(p) for p in args.paths]
    py_files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            py_files.append(root)
        elif root.is_dir():
            py_files.extend(sorted(root.rglob("*.py")))

    total_files = 0
    total_docs = 0
    for path in py_files:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"skip {path}: {e}", file=sys.stderr)
            continue
        if SEP_CHAR not in source:
            continue
        new_src, n = process_source(source, titles)
        if new_src == source:
            continue
        total_files += 1
        total_docs += n
        rel = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        print(f"{rel}: {n} docstring(s) updated")
        if not args.dry_run:
            path.write_text(new_src, encoding="utf-8")

    if args.dry_run:
        print(f"dry-run: would touch {total_files} file(s), {total_docs} docstring(s)")
    else:
        print(f"done: {total_files} file(s), {total_docs} docstring(s) modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

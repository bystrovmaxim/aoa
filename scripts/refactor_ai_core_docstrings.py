#!/usr/bin/env python3
"""
Move AI-CORE out of module docstrings; keep on classes and top-level functions;
replace method docstrings that contain AI-CORE with a single short line.

Dry-run:
  uv run python scripts/refactor_ai_core_docstrings.py --dry-run src

Apply:
  uv run python scripts/refactor_ai_core_docstrings.py src
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

SEP_LINE = "═══════════════════════════════════════════════════════════════════════════════"

# Framed module-style AI-CORE block (may include trailing separator line).
_MODULE_AI_CORE_FRAMED = re.compile(
    rf"\n{re.escape(SEP_LINE)}\nAI-CORE-BEGIN\n{re.escape(SEP_LINE)}\n.*?\nAI-CORE-END\n(?:{re.escape(SEP_LINE)}\n)?",
    re.DOTALL,
)
# Minimal AI-CORE ... AI-CORE-END (no outer frame) inside a docstring.
_AI_CORE_PLAIN = re.compile(r"\nAI-CORE-BEGIN\n.*?\nAI-CORE-END\n", re.DOTALL)


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


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST | None]:
    parents: dict[ast.AST, ast.AST | None] = {tree: None}

    def walk(node: ast.AST, parent: ast.AST | None) -> None:
        for child in ast.iter_child_nodes(node):
            parents[child] = node
            walk(child, node)

    walk(tree, None)
    return parents


def get_docstring_constant(node: ast.AST) -> ast.Constant | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if not isinstance(first, ast.Expr):
        return None
    v = first.value
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return v
    return None


def collect_docstring_nodes(tree: ast.AST) -> list[tuple[ast.AST, ast.Constant]]:
    out: list[tuple[ast.AST, ast.Constant]] = []
    if isinstance(tree, ast.Module):
        mod = get_docstring_constant(tree)
        if mod is not None:
            out.append((tree, mod))
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            c = get_docstring_constant(node)
            if c is not None:
                out.append((node, c))
    return out


def strip_module_ai_core(text: str) -> str:
    """Remove AI-CORE blocks from module docstring."""
    s = text
    s = _MODULE_AI_CORE_FRAMED.sub("\n", s)
    s = _AI_CORE_PLAIN.sub("\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.rstrip() + ("\n" if text.endswith("\n") else "")


def _extract_role(ai_core_blob: str) -> str | None:
    m = re.search(r"^ROLE:\s*(.+)$", ai_core_blob, re.MULTILINE)
    return m.group(1).strip() if m else None


def shorten_method_docstring(text: str) -> str:
    """Drop AI-CORE; keep one short English line (prefer ROLE, else first line)."""
    role_source = text
    without = _MODULE_AI_CORE_FRAMED.sub("\n", text)
    without = _AI_CORE_PLAIN.sub("\n", without)
    role = _extract_role(role_source)
    body = without.strip()
    if body:
        first = body.splitlines()[0].strip()
        if len(first) > 160:
            first = first[:157] + "..."
        return first
    if role:
        if len(role) > 160:
            role = role[:157] + "..."
        return role
    return "Implementation detail."


def is_method_like(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: dict[ast.AST, ast.AST | None],
) -> bool:
    p = parents.get(node)
    return isinstance(p, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))


def process_source(source: str) -> tuple[str, int]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0

    parents = build_parent_map(tree)
    items = collect_docstring_nodes(tree)
    replacements: list[tuple[int, int, str]] = []

    for node, const in items:
        old = const.value
        if isinstance(node, ast.Module):
            if "AI-CORE-BEGIN" not in old:
                continue
            new_inner = strip_module_ai_core(old)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_method_like(
            node,
            parents,
        ):
            if "AI-CORE-BEGIN" not in old:
                continue
            new_inner = shorten_method_docstring(old)
        else:
            continue

        if new_inner == old:
            continue
        span = _span_for_constant(source, const)
        if span is None:
            continue
        start, end = span
        replacements.append((start, end, format_docstring_literal(new_inner)))

    replacements.sort(key=lambda t: t[0], reverse=True)
    out = source
    for start, end, new_text in replacements:
        out = out[:start] + new_text + out[end:]
    return out, len(replacements)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="Files or directories")
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
    n_repls = 0
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
        n_repls += n
        rel = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        print(f"{rel}: {n} replacement(s)")
        if not args.dry_run:
            path.write_text(new_src, encoding="utf-8")

    print(
        f"{'dry-run: ' if args.dry_run else ''}"
        f"{n_files} file(s), {n_repls} docstring(s)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

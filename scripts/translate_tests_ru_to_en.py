#!/usr/bin/env python3
"""Translate Russian in test .py files: comments and string literals only (tokenize)."""
from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from pathlib import Path

from deep_translator import GoogleTranslator

RU = re.compile(r"[а-яА-ЯёЁ]")
SKIP_FILES = {
    "tests/conftest.py",
    "tests/dependencies/__init__.py",
    "tests/dependencies/test_depends_decorator_validation.py",
    "tests/dependencies/test_dependency_intent.py",
}

_tr = GoogleTranslator(source="ru", target="en")


def translate_text(text: str) -> str:
    if not RU.search(text):
        return text
    text = text.strip()
    if not text:
        return text
    # Chunk long text for API limits
    max_chunk = 4500
    if len(text) <= max_chunk:
        return _tr.translate(text)
    parts: list[str] = []
    buf: list[str] = []
    n = 0
    for line in text.split("\n"):
        if n + len(line) + 1 > max_chunk and buf:
            parts.append(_tr.translate("\n".join(buf)))
            buf = []
            n = 0
        buf.append(line)
        n += len(line) + 1
    if buf:
        parts.append(_tr.translate("\n".join(buf)))
    return "\n".join(parts)


def requote_string(original_token: str, new_inner: str) -> str:
    """Rebuild string token with same quote style; new_inner is raw string content."""
    raw = original_token
    prefix = ""
    body = raw
    for p in ("rf", "fr", "rb", "br", "r", "f", "b", "u", "R", "F", "B", "U"):
        if raw.startswith(p) and len(raw) > len(p) and raw[len(p)] in "\"'":
            prefix = p
            body = raw[len(p) :]
            break
    if body.startswith('"""'):
        q = '"""'
        esc = new_inner.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return f"{prefix}{q}{esc}{q}"
    if body.startswith("'''"):
        q = "'''"
        esc = new_inner.replace("\\", "\\\\").replace("'''", "\\'\\'\\'")
        return f"{prefix}{q}{esc}{q}"
    q = body[0]
    esc = new_inner.replace("\\", "\\\\").replace(q, "\\" + q)
    return f"{prefix}{q}{esc}{q}"


def translate_string_token(tok_str: str) -> str:
    try:
        inner = ast.literal_eval(tok_str)
    except (SyntaxError, ValueError):
        return tok_str
    if not isinstance(inner, str) or not RU.search(inner):
        return tok_str
    translated = translate_text(inner)
    return requote_string(tok_str, translated)


def line_starts(src: str) -> list[int]:
    lines = src.splitlines(keepends=True)
    starts = []
    off = 0
    for line in lines:
        starts.append(off)
        off += len(line)
    return starts


def to_offset(starts: list[int], line: int, col: int, src_len: int) -> int:
    if not starts:
        return min(col, src_len)
    idx = line - 1
    if idx < 0:
        idx = 0
    if idx >= len(starts):
        idx = len(starts) - 1
    return min(starts[idx] + col, src_len)


def process_file(path: Path) -> bool:
    rel = path.as_posix()
    if rel in SKIP_FILES:
        return False
    src = path.read_text(encoding="utf-8")
    if not RU.search(src):
        return False

    starts = line_starts(src)
    src_len = len(src)
    readline = io.StringIO(src).readline
    try:
        tokens = list(tokenize.generate_tokens(readline))
    except tokenize.TokenError:
        print(f"SKIP tokenize error: {path}", file=sys.stderr)
        return False

    out: list[str] = []
    prev_end = 0
    for tok in tokens:
        s = to_offset(starts, tok.start[0], tok.start[1], src_len)
        e = to_offset(starts, tok.end[0], tok.end[1], src_len)
        out.append(src[prev_end:s])
        piece = src[s:e]
        if tok.type == tokenize.COMMENT and RU.search(piece):
            if piece.startswith("#"):
                body = piece[1:]
                # preserve trailing newline
                nl = ""
                if body.endswith("\n"):
                    nl = "\n"
                    body = body[:-1]
                tr = translate_text(body)
                out.append("#" + tr + nl)
            else:
                out.append(piece)
        elif tok.type == tokenize.STRING and RU.search(piece):
            out.append(translate_string_token(piece))
        else:
            out.append(piece)
        prev_end = e
    out.append(src[prev_end:])
    new_src = "".join(out)
    if new_src != src:
        path.write_text(new_src, encoding="utf-8")
        return True
    return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    tests = root / "tests"
    changed = 0
    for path in sorted(tests.rglob("*.py")):
        if process_file(path):
            print(path.relative_to(root))
            changed += 1
    print(f"Done. Modified {changed} files.", file=sys.stderr)


if __name__ == "__main__":
    main()

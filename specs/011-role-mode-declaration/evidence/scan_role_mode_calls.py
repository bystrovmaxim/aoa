# specs/011-role-mode-declaration/evidence/scan_role_mode_calls.py
"""
Count every ``@role_mode(...)`` occurrence in the tree and classify its argument.

The feature's corpus claim is measured, not quoted from the issue: how many
declarations exist, which member each passes, and which occurrences are prose
placeholders rather than calls. Run from the repository root:

    python3 specs/011-role-mode-declaration/evidence/scan_role_mode_calls.py

Exit status is 0 when every real call passes a ``RoleMode`` member.
"""

from __future__ import annotations

import collections
import pathlib
import re

CALL = re.compile(r"@role_mode\(\s*([^)]*?)\s*\)")
MEMBER = re.compile(r"RoleMode\.[A-Z_]+")
SCANNED_ROOTS = ("packages", "examples", "tests", "docs")
SUFFIXES = (".py", ".md", ".ipynb")
SKIPPED_PARTS = {
    ".git",
    ".venv",
    ".uvcache",
    ".uv-cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "archive",
    "node_modules",
    "htmlcov",
    "dist",
    "build",
}


def scanned_files() -> list[pathlib.Path]:
    """Return every file the scan reads, in a stable order."""
    files: list[pathlib.Path] = []
    for root in SCANNED_ROOTS:
        for path in sorted(pathlib.Path(root).rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if any(part in SKIPPED_PARTS for part in path.parts):
                continue
            files.append(path)
    return files


def main() -> int:
    """Print the counts and report whether any real call is not a member."""
    members: collections.Counter[str] = collections.Counter()
    exceptions: list[tuple[str, str]] = []
    placeholders: list[tuple[str, str]] = []
    carriers: collections.Counter[str] = collections.Counter()

    for path in scanned_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in CALL.finditer(text):
            argument = match.group(1)
            if MEMBER.fullmatch(argument):
                members[argument] += 1
                carriers[path.suffix] += 1
                continue
            if argument in {"...", "RoleMode.…", "RoleMode..."}:
                placeholders.append((str(path), argument))
                continue
            exceptions.append((str(path), argument))

    total = sum(members.values())
    print(f"real calls: {total} {dict(members)}")
    print(f"by carrier: {dict(carriers)}")
    print(f"placeholders in prose: {len(placeholders)}")
    for path, argument in placeholders:
        print(f"  {path}: @role_mode({argument})")
    print(f"arguments that are neither a member nor a known placeholder: {len(exceptions)}")
    for path, argument in exceptions:
        print(f"  {path}: @role_mode({argument})")
    return 1 if exceptions else 0


if __name__ == "__main__":
    raise SystemExit(main())

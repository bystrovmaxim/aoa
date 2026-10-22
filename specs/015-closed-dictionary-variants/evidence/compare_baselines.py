# specs/015-closed-dictionary-variants/evidence/compare_baselines.py
"""Compare two scan dumps and report identity or a named difference.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The feature's success criteria are counts and graph facts. ``baseline.before.json``
records them before the migration and ``baseline.after.json`` after it; this script
says whether they are identical or names every path that moved, so a difference is
reviewed rather than discovered.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    python compare_baselines.py BEFORE.json AFTER.json
    python compare_baselines.py BEFORE.json AFTER.json --strict

``generated_at``, ``commit`` and ``tools`` always differ and are ignored unless
``--strict`` is given. Exit code: 0 identical, 1 differences, 2 unreadable input.

═══════════════════════════════════════════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════════════════════════════════════════

    identical
    ~ totals.scripts.axes: 107 -> 110
    + demo_graph.node_types.Lifecycle: 201 -> 201
    - ...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IGNORED_KEYS = frozenset({"generated_at", "commit", "tools"})
MAX_LINES = 60


def _walk(left: Any, right: Any, path: str, differences: list[str]) -> None:
    """Append one line per difference between ``left`` and ``right``."""
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            child = f"{path}.{key}" if path else key
            if key not in left:
                differences.append(f"+ {child}: (absent) -> {right[key]!r}")
            elif key not in right:
                differences.append(f"- {child}: {left[key]!r} -> (absent)")
            else:
                _walk(left[key], right[key], child, differences)
        return
    if isinstance(left, list) and isinstance(right, list):
        if left != right:
            differences.append(f"~ {path}: {left!r} -> {right!r}")
        return
    if left != right:
        differences.append(f"~ {path}: {left!r} -> {right!r}")


def _load(path: Path) -> dict[str, Any]:
    """Read one dump, refusing anything that is not an object."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def main() -> int:
    """Compare two dumps and print the result."""
    parser = argparse.ArgumentParser(description="Compare two scan dumps.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--strict", action="store_true", help="also compare generated_at, commit and tools")
    args = parser.parse_args()

    try:
        before = _load(args.before)
        after = _load(args.after)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"cannot read a baseline: {error}")
        return 2

    if not args.strict:
        for payload in (before, after):
            for key in IGNORED_KEYS:
                payload.pop(key, None)

    differences: list[str] = []
    _walk(before, after, "", differences)

    if not differences:
        print("identical")
        return 0

    print(f"{len(differences)} difference(s):")
    for line in differences[:MAX_LINES]:
        print(line)
    if len(differences) > MAX_LINES:
        print(f"... and {len(differences) - MAX_LINES} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

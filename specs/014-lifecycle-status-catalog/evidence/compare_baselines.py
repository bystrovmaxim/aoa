"""Compare the demo baseline before and after the lifecycle-catalogue migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    """Load one baseline artefact."""
    return json.loads(path.read_text())


def axes(baseline: dict[str, Any]) -> dict[str, Any]:
    """Index axes by qualified name."""
    return {axis["qualname"]: axis for axis in baseline["axes"]}


def state_types(baseline: dict[str, Any]) -> dict[str, Any]:
    """Index state types by qualified name."""
    return {state_type["qualname"]: state_type for state_type in baseline["state_types"]}


def state_rows(baseline: dict[str, Any]) -> dict[tuple[str, str], Any]:
    """Index graph state rows by entity and field."""
    return {(row["entity"], row["field"]): row["states"] for row in baseline["state_rows"]}


def entity_fields(baseline: dict[str, Any]) -> set[tuple[str, str, str]]:
    """Return the entity lifecycle fields as a set."""
    return {(row["entity"], row["field"], row["axis"]) for row in baseline["entity_lifecycle_fields"]}


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Return every difference that changes a status, label, transition, row or field."""
    problems: list[str] = []
    for name in ("errors",):
        if before.get(name) or after.get(name):
            problems.append(f"{name}: before={before.get(name)!r} after={after.get(name)!r}")
    before_axes, after_axes = axes(before), axes(after)
    if set(before_axes) != set(after_axes):
        problems.append(f"axis set changed: {sorted(set(before_axes) ^ set(after_axes))}")
    for qualname in sorted(set(before_axes) & set(after_axes)):
        old, new = before_axes[qualname], after_axes[qualname]
        if old["members"] != new["members"]:
            problems.append(f"{qualname}: members changed")
        if old["template"] != new["template"]:
            problems.append(f"{qualname}: template changed")
    before_types, after_types = state_types(before), state_types(after)
    if set(before_types) != set(after_types):
        problems.append(f"state type set changed: {sorted(set(before_types) ^ set(after_types))}")
    for qualname in sorted(set(before_types) & set(after_types)):
        if before_types[qualname]["fields"] != after_types[qualname]["fields"]:
            problems.append(f"{qualname}: fields changed")
    if entity_fields(before) != entity_fields(after):
        problems.append("entity lifecycle fields changed")
    before_rows, after_rows = state_rows(before), state_rows(after)
    if set(before_rows) != set(after_rows):
        problems.append(f"state row set changed: {sorted(set(before_rows) ^ set(after_rows))}")
    for key in sorted(set(before_rows) & set(after_rows)):
        if before_rows[key] != after_rows[key]:
            problems.append(f"{key}: state rows changed")
    return problems


def main() -> int:
    """Run the comparison and report the counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    before, after = load(args.before), load(args.after)
    problems = compare(before, after)
    if problems:
        for problem in problems:
            print("CHANGED:", problem)
        return 1
    print(
        f"{len(before['axes'])} axes and {len(before['state_types'])} types compared, "
        "0 with a changed status, label, transition, state row or entity field"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

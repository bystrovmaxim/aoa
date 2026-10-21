# specs/012-lifecycle-state-vocabularies/evidence/compare_baselines.py
"""Compare two corpus baselines by declaration: state codes and transition pairs must be identical."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fingerprint(payload: dict) -> dict[str, tuple[frozenset[str], frozenset[tuple[str, str]]]]:
    """Return ``declaration -> (codes, pairs)`` for a baseline payload."""
    result: dict[str, tuple[frozenset[str], frozenset[tuple[str, str]]]] = {}
    for chain in payload["chains"]:
        if "error" in chain:
            continue
        states = chain.get("states", [])
        codes = frozenset(state["key"] for state in states)
        pairs = frozenset((state["key"], target) for state in states for target in state["transitions"])
        result[chain["declaration"]] = (codes, pairs)
    return result


def main(argv: list[str]) -> int:
    """Compare the two baseline files and print every difference."""
    if len(argv) != 3:
        print("usage: compare_baselines.py BEFORE.json AFTER.json")
        return 2
    before = fingerprint(json.loads(Path(argv[1]).read_text()))
    after = fingerprint(json.loads(Path(argv[2]).read_text()))

    problems = 0
    for name in sorted(set(before) | set(after)):
        if name not in before or name not in after:
            print(f"MISSING  {name}: before={name in before} after={name in after}")
            problems += 1
            continue
        before_codes, before_pairs = before[name]
        after_codes, after_pairs = after[name]
        if before_codes != after_codes:
            print(f"CODES    {name}: -{sorted(before_codes - after_codes)} +{sorted(after_codes - before_codes)}")
            problems += 1
        if before_pairs != after_pairs:
            print(f"PAIRS    {name}: -{sorted(before_pairs - after_pairs)} +{sorted(after_pairs - before_pairs)}")
            problems += 1

    print(f"declarations compared: {len(before)}; differences: {problems}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

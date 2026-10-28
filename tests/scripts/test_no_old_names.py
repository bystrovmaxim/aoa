# tests/scripts/test_no_old_names.py
"""No tracked file names Maxitor's old package, folder or import — except old specs and past changelog entries."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The viewer was ``aoa-maxitor`` in ``packages/aoa-maxitor``, imported as ``aoa.maxitor``.
OLD_NAMES = re.compile(r"aoa\.maxitor|aoa/maxitor|aoa-maxitor")


def _kept_as_history(path: str) -> bool:
    """Old specs and changelogs are history: they keep the names they were written with; this test names them to find them."""
    return path.startswith("specs/") or Path(path).name.startswith("CHANGELOG") or path == "tests/scripts/test_no_old_names.py"


def test_no_tracked_file_names_the_old_viewer() -> None:
    """Every file outside history speaks of ``maxitor`` and ``maxitor.viewer`` only."""
    listed = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True, cwd=REPO_ROOT).stdout
    found: list[str] = []
    for path in filter(None, listed.decode().split("\0")):
        if _kept_as_history(path) or not (REPO_ROOT / path).is_file():
            continue
        text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")
        found += [f"{path}:{text.count(chr(10), 0, m.start()) + 1}: {m.group()}" for m in OLD_NAMES.finditer(text)]
    assert found == [], "old names left:\n" + "\n".join(found[:20])

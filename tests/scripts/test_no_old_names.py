# tests/scripts/test_no_old_names.py
"""No tracked file names Maxitor's old packages, folders or imports — except old specs and past changelog entries."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The front was ``aoa-maxitor`` in ``packages/aoa-maxitor``, imported as ``aoa.maxitor``, then ``maxitor.viewer`` in
# ``packages/maxitor/app``, installed as ``maxitor[viewer]`` and run as ``maxitor-api``; the command was
# ``maxitor-gnomon`` in ``packages/maxitor-gnomon``, imported as ``maxitor_gnomon``.
OLD_NAMES = re.compile(
    r"aoa\.maxitor|aoa/maxitor(?![-\w])|aoa-maxitor|maxitor_gnomon|packages/maxitor-gnomon"
    r"|maxitor\.viewer|maxitor/viewer|maxitor\[viewer\]|packages/maxitor/app|maxitor-api"
)
# A link pinned to the released ``maxitor-gnomon`` 0.1.0 points at that snapshot, where the old paths are right.
RELEASED = "maxitor-gnomon-v0.1.0"


def _kept_as_history(path: str) -> bool:
    """Old specs and changelogs are history: they keep the names they were written with; this test names them to find them."""
    return path.startswith("specs/") or Path(path).name.startswith("CHANGELOG") or path == "tests/scripts/test_no_old_names.py"


def test_no_tracked_file_names_the_old_packages() -> None:
    """Every file outside history speaks of ``maxitor``, ``maxitor.front`` and ``maxitor.graph_builder`` only."""
    listed = subprocess.run(["git", "ls-files", "-z"], check=True, capture_output=True, cwd=REPO_ROOT).stdout
    found: list[str] = []
    for path in filter(None, listed.decode().split("\0")):
        if _kept_as_history(path) or not (REPO_ROOT / path).is_file():
            continue
        text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for match in OLD_NAMES.finditer(text):
            line = text[text.rfind("\n", 0, match.start()) + 1 : text.find("\n", match.end())]
            if RELEASED not in line:
                found.append(f"{path}:{text.count(chr(10), 0, match.start()) + 1}: {match.group()}")
    assert found == [], "old names left:\n" + "\n".join(found[:20])

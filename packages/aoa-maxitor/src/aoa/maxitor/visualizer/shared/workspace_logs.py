# packages/aoa-maxitor/src/aoa/maxitor/visualizer/shared/workspace_logs.py
"""
workspace_logs — resolve ``archive/logs`` under the AOA workspace root.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demo CLIs write HTML under ``<repo>/archive/logs``. Package sources live deep
under ``packages/aoa-maxitor/src/...``; a fixed ``Path.parents[n]`` breaks when
layout depth changes. This module walks upward to the monorepo root.
"""

from __future__ import annotations

from pathlib import Path


def archive_logs_dir() -> Path:
    """Return ``<workspace>/archive/logs`` (monorepo root with ``packages/aoa-maxitor``)."""
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").is_file() and (parent / "packages" / "aoa-maxitor").is_dir():
            return parent / "archive" / "logs"
    return Path.cwd() / "archive" / "logs"

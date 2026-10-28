# packages/maxitor-gnomon/src/maxitor_gnomon/__init__.py
"""
maxitor-gnomon — the graph format of Maxitor.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Give a service's graph a home that depends on no framework: the graph schema by
version, the config that lists a repository's graphs, and the ``gnomon`` command
that keeps each graph in one file. A gnomon is the rod of a sundial whose shadow
marks the hour; this package marks where a service's graph stood at each commit.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The package imports nothing from ``aoa``; ``scripts/check_package_boundaries.py``
enforces it. AOA reads its graph schema from here, never the other way round.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]

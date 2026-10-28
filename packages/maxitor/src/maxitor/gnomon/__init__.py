# packages/maxitor/src/maxitor/gnomon/__init__.py
"""
maxitor.gnomon — the ``gnomon`` command: a repository's graphs, kept in files.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Keep each service's graph in one file, checked against the Open Gnomon Protocol
by version: the config that lists a repository's graphs, the writer and the
check, and the differences between a file and what its build prints. A gnomon is
the rod of a sundial whose shadow marks the hour; this part marks where a
service's graph stood at each commit.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The part imports nothing from ``aoa`` and nothing of ``maxitor.viewer``;
``scripts/check_package_boundaries.py`` enforces both, so ``pip install maxitor``
with no extra is enough to run it.
"""

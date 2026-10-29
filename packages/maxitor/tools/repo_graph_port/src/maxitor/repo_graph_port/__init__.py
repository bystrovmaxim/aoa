# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/__init__.py
"""
maxitor.repo_graph_port — a graph's history, read from the repository that keeps its file.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A service keeps its graph in one file beside its code, so the file's history in
git is the graph's history. This part reads it: which commits changed the file
on a branch (the versions), the repository's tags placed on those versions, and
each version's graph, checked against the Open Gnomon Protocol and counted.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

The part is a service of its own, ``repo-graph-port``: the only part of Maxitor that
talks to a repository's host. It never imports the front, and the front reads it over
HTTP, never imports it; it checks graphs with ``maxitor.graph_builder.schemas``.
``scripts/check_package_boundaries.py`` enforces this. ``pip install "maxitor[repo-graph-port]"``
brings its dependencies.
"""

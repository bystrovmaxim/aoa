# packages/maxitor/core/repo_graph_port/src/maxitor/repo_graph_port/actions/__init__.py
"""
The actions of ``maxitor.repo_graph_port`` — what a reader of a history can ask.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``DescribeHistoryAction`` (what a history is), ``HistoryAction`` (its versions) and
``VersionAction`` (one version's graph file). The front mounts them as routes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

route ──► action ──connections──► HistoriesConfig, GitMirror, VersionCache.
"""

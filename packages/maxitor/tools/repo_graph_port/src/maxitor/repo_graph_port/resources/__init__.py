# packages/maxitor/tools/repo_graph_port/src/maxitor/repo_graph_port/resources/__init__.py
"""
The resources of ``maxitor.repo_graph_port`` — the stores and hosts its actions read through.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Each resource works with one store directly and offers only methods that mean
something to a history: the git mirror today, the host and the histories
config next to it.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

action aspect ──connections[...]──► resource ──► git / the host / the config file.
"""

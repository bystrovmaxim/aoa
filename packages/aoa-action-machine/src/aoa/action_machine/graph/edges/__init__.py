# packages/aoa-action-machine/src/aoa/action_machine/graph/edges/__init__.py
"""
Typed interchange edges package.

Import concrete edge types from their leaf modules.
"""

from __future__ import annotations

from aoa.action_machine.graph.edges.entity_schema_graph_edge import EntitySchemaGraphEdge

__all__: list[str] = ["EntitySchemaGraphEdge"]
